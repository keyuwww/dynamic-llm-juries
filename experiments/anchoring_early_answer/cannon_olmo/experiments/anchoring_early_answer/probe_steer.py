"""Probe and steer a Qwen judge at position A (before it reasons). Runs on a Modal GPU (probe_modal.py).

capture  For every pool judgment by the judge: the exact judge prompt (chat template, thinking off) plus
         "VERDICT:" -- the same position-A readout as the Tinker experiment. Saves, at the last token, the
         residual stream after every decoder layer, plus the verdict log-odds.
           -> <out>/hidden.npy  float16 [n_judgments, n_layers + 1, d]   (index 0 = embeddings)
              <out>/meta.jsonl   one row per judgment, same order (judge, item_id, bench, gold, margin, n_tok)
steer    Adds alpha * direction to the residual stream at one layer, at position A, and reads the verdict
         again. Directions come from a file written by probes.py (unit vectors, one per name).
           -> <out>/steer_<name>.jsonl
readout  (open models with their own generations, e.g. OLMo-3) Early answering on the GPU: the judge's own transcript
         (--gen, from gen_vllm.py) is cut at every checkpoint (ckpts.py; --think for thinking models) and the verdict is
         read as the first-token log-odds of CORRECT vs INCORRECT (A vs B). Also writes the position-A capture
         (hidden.npy + meta.jsonl, same as `capture`) and the hidden state at E (end of thinking) and C (verdict).
           -> <out>/readouts.jsonl, hidden.npy, hidden_E.npy, hidden_C.npy, meta.jsonl
         --plain (base models, no chat template, no generations): the prompt is the raw text; position A only.

  python probe_steer.py --phase capture --model Qwen/Qwen3.5-4B --judge qwen3.5-4b --out /vol/anchoring_probe/qwen3.5-4b
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load_jobs(judge, prompts_from=None):
    """Judge prompts do not depend on the judge, so a model outside the Tinker pool (Llama) reuses the
    prompts of a pool judge (prompts_from) and is labelled with its own name."""
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = [j for j in map(json.loads, f) if j["judge"] == (prompts_from or judge)]
    return [dict(j, judge=judge) for j in jobs]


def setup(model_name):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.bfloat16, device_map="cuda")
    model.eval()
    layers = model.model.layers if hasattr(model.model, "layers") else model.model.language_model.layers
    return tok, model, layers


def prompt_ids(tok, job):
    text = tok.apply_chat_template(job["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    ids = tok(text, add_special_tokens=False).input_ids
    return ids, ids + tok.encode("VERDICT:", add_special_tokens=False)


def option_ids(tok, pairwise):
    o1, o2 = (" A", " B") if pairwise else (" CORRECT", " INCORRECT")
    return tok.encode(o1, add_special_tokens=False)[0], tok.encode(o2, add_special_tokens=False)[0]


def plain_ids(tok, job):
    """Base model (no chat template): the prompt text itself."""
    text = "\n\n".join(m["content"] for m in job["messages"]) + "\n\n"
    return tok(text, add_special_tokens=True).input_ids


def readout(a):
    import sys
    import torch
    sys.path.insert(0, str(HERE))
    from ckpts import checkpoints, checkpoints_think
    tok, model, layers = setup(a.model)
    jobs = load_jobs(a.judge, a.prompts_from)
    gen = {}
    if a.gen:
        for r in map(json.loads, open(a.gen)):
            if r["key"].startswith("judge|"):
                gen[r["key"].split("|", 2)[2]] = r["text"]
        jobs = [j for j in jobs if j["item_id"] in gen]
    if a.limit:
        jobs = jobs[: a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n_layers, d = len(layers), model.config.get_text_config().hidden_size
    caps = {c: np.lib.format.open_memmap(out / f"hidden{'' if c == 'A' else '_' + c}.npy", mode="w+",
                                         dtype=np.float16, shape=(len(jobs), n_layers + 1, d))
            for c in (["A"] if a.plain else ["A", "E", "C"] if a.think else ["A", "C"])}
    meta, reads = open(out / "meta.jsonl", "w"), open(out / "readouts.jsonl", "w")

    def first_ids(opts):
        t1, t2 = (tok.encode(o, add_special_tokens=False)[0] for o in opts)
        assert t1 != t2, opts
        return t1, t2

    for i, j in enumerate(jobs):
        if a.plain:
            base = plain_ids(tok, j)
            cks = [("A", "VERDICT:", (" A", " B") if j["pairwise"] else (" CORRECT", " INCORRECT"))]
        else:
            base = tok.apply_chat_template(j["messages"], tokenize=True, add_generation_prompt=True)
            base = list(base["input_ids"] if isinstance(base, dict) else base)
            t = gen.get(j["item_id"], "")
            cks = (checkpoints_think if a.think else checkpoints)(t, j["pairwise"])
        for name, prefix, opts in cks:
            ids = base + tok.encode(prefix, add_special_tokens=False)
            want_h = name in caps
            with torch.no_grad():
                o = model(input_ids=torch.tensor([ids], device="cuda"), output_hidden_states=want_h, logits_to_keep=1)
            lp = torch.log_softmax(o.logits[0, -1].float(), -1)
            t1, t2 = first_ids(opts)
            m = float(lp[t1] - lp[t2])
            if want_h:
                caps[name][i] = torch.stack([h[0, -1] for h in o.hidden_states]).float().cpu().numpy().astype(np.float16)
            if name == "A":
                meta.write(json.dumps(dict(judge=j["judge"], item_id=j["item_id"], bench=j["bench"], gold=j["gold"],
                                           pairwise=j["pairwise"], margin=m, n_tok=len(base),
                                           pool_n_in=j["pool_n_in"])) + "\n")
            reads.write(json.dumps(dict(judge=j["judge"], item_id=j["item_id"], bench=j["bench"], ckpt=name,
                                        margin=m, n_tok=len(ids), row=i)) + "\n")
            del o
        if (i + 1) % 100 == 0:
            print(f"  readout {i + 1}/{len(jobs)}", flush=True)
            reads.flush()
            meta.flush()
    for H in caps.values():
        H.flush()
    meta.close()
    reads.close()
    print(f"done: readout {len(jobs)} judgments", flush=True)


def capture(a):
    import torch
    tok, model, layers = setup(a.model)
    jobs = load_jobs(a.judge, a.prompts_from)
    if a.limit:
        jobs = jobs[: a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n_layers, d = len(layers), model.config.get_text_config().hidden_size
    H = np.lib.format.open_memmap(out / "hidden.npy", mode="w+", dtype=np.float16, shape=(len(jobs), n_layers + 1, d))
    meta = open(out / "meta.jsonl", "w")
    for i, j in enumerate(jobs):
        base, ids = prompt_ids(tok, j)
        with torch.no_grad():
            o = model(input_ids=torch.tensor([ids], device="cuda"), output_hidden_states=True, logits_to_keep=1)
        H[i] = torch.stack([h[0, -1] for h in o.hidden_states]).float().cpu().numpy().astype(np.float16)
        t1, t2 = option_ids(tok, j["pairwise"])
        lg = o.logits[0, -1].float()
        meta.write(json.dumps(dict(judge=j["judge"], item_id=j["item_id"], bench=j["bench"], gold=j["gold"],
                                   pairwise=j["pairwise"], margin=float(lg[t1] - lg[t2]),
                                   n_tok=len(base), pool_n_in=j["pool_n_in"])) + "\n")
        if (i + 1) % 100 == 0:
            print(f"  captured {i + 1}/{len(jobs)}", flush=True)
    H.flush()
    meta.close()
    print(f"done: {len(jobs)} judgments, {n_layers} layers, d={d}", flush=True)


def steer(a):
    """Directions file: {name: {"layer": L, "vec": [...unit vector...], "items": [item_ids to steer]}}."""
    import torch
    tok, model, layers = setup(a.model)
    jobs = {j["item_id"]: j for j in load_jobs(a.judge, a.prompts_from)}
    dirs = json.loads(Path(a.directions).read_text())
    alphas = [float(x) for x in a.alphas.split(",")]
    out = Path(a.out)
    for name, spec in dirs.items():
        L, v = spec["layer"], torch.tensor(spec["vec"], dtype=torch.bfloat16, device="cuda")
        state = {"alpha": 0.0}

        def hook(module, inp, o):  # add alpha * v at the last token only (position A)
            h = o[0] if isinstance(o, tuple) else o
            h = h.clone()
            h[0, -1] += state["alpha"] * v
            return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
        # hidden_states index L = output of decoder layer L-1
        handle = layers[L - 1].register_forward_hook(hook)
        fh = open(out / f"steer_{name}.jsonl", "w")
        for n, iid in enumerate(spec["items"]):
            j = jobs[iid]
            _, ids = prompt_ids(tok, j)
            t1, t2 = option_ids(tok, j["pairwise"])
            margins = {}
            for al in alphas:
                state["alpha"] = al
                with torch.no_grad():
                    lg = model(input_ids=torch.tensor([ids], device="cuda"), logits_to_keep=1).logits[0, -1].float()
                margins[str(al)] = float(lg[t1] - lg[t2])
            fh.write(json.dumps(dict(item_id=iid, layer=L, margins=margins)) + "\n")
            if (n + 1) % 50 == 0:
                print(f"  {name}: {n + 1}/{len(spec['items'])}", flush=True)
        fh.close()
        handle.remove()
    print("done: steer", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["capture", "steer", "readout"], required=True)
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--judge", default="qwen3.5-4b")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--directions", default="")
    ap.add_argument("--alphas", default="-8,-4,0,4,8")
    ap.add_argument("--prompts-from", default=None, help="reuse another judge's prompts (e.g. qwen3.5-4b for Llama)")
    ap.add_argument("--gen", default="", help="readout: the judge's generations.jsonl (gen_vllm.py)")
    ap.add_argument("--think", action="store_true", help="readout: thinking model (transcripts start inside <think>)")
    ap.add_argument("--plain", action="store_true", help="readout: base model, raw prompt text, position A only")
    a = ap.parse_args()
    {"capture": capture, "steer": steer, "readout": readout}[a.phase](a)


if __name__ == "__main__":
    main()
