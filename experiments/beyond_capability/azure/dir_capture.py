"""GPU side of the solve-vs-judge direction study (runs on Modal, see dir_modal.py).

capture  For every row of an items file (dir_build.py): chat template (thinking off) + suffix, one forward pass,
         residual stream at the last token for every 2nd layer (+ the last), and for J/S rows the verdict
         log-odds CORRECT vs INCORRECT at that position.
           -> <out>/hidden_<tag>.npy  float16 [n_rows, n_kept_layers, d]   + meta_<tag>.jsonl (same order)
steer    For judge-mode rows (J): at one layer, at the last token, change the hidden state along a unit direction v
         and read the verdict again. Two kinds of edit:
           add      h + alpha * v                              (shifts every item the same way)
           amplify  h + beta * ((h.v) - mu) * v                (stretches items apart along v; mu = mean projection)
         Directions file: {name: {"layer": L, "vec": [...], "mu": float}}.
           -> <out>/steer_<tag>.jsonl
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np


def setup(model_name):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.bfloat16, device_map="cuda")
    model.eval()
    layers = model.model.layers if hasattr(model.model, "layers") else model.model.language_model.layers
    return tok, model, layers


def build_ids(tok, row, think=False):
    """thinking off: template + suffix (e.g. "VERDICT:"). thinking on: the template opens the thinking block and the
    state is taken there, before the model has reasoned (no suffix)."""
    text = tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=think)
    ids = tok(text, add_special_tokens=False).input_ids
    if row["suffix"] and not think:
        ids += tok.encode(row["suffix"], add_special_tokens=False)
    return ids


def verdict_ids(tok):
    t1 = tok.encode(" CORRECT", add_special_tokens=False)[0]
    t2 = tok.encode(" INCORRECT", add_special_tokens=False)[0]
    assert t1 != t2
    return t1, t2


def load_rows(path, limit):
    with gzip.open(path, "rt") as f:
        rows = [json.loads(l) for l in f]
    if limit:  # pilot: a few rows of every (bench, mode)
        seen, keep = {}, []
        for r in rows:
            k = (r["bench"], r["mode"])
            if seen.get(k, 0) < limit:
                seen[k] = seen.get(k, 0) + 1
                keep.append(r)
        rows = keep
    return rows


def capture(a):
    import torch
    tok, model, layers = setup(a.model)
    rows = load_rows(a.items, a.limit)
    if a.think:  # thinking-on capture: judge rows only
        rows = [r for r in rows if r["mode"] == "J"]
    n = len(layers)
    keep = sorted(set(range(0, n + 1, 2)) | {n})
    d = model.config.get_text_config().hidden_size
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    H = np.lib.format.open_memmap(out / f"hidden_{a.tag}.npy", mode="w+", dtype=np.float16, shape=(len(rows), len(keep), d))
    t1, t2 = verdict_ids(tok)
    with open(out / f"meta_{a.tag}.jsonl", "w") as meta:
        for i, r in enumerate(rows):
            ids = build_ids(tok, r, a.think)
            with torch.no_grad():
                o = model(input_ids=torch.tensor([ids], device="cuda"), output_hidden_states=True, logits_to_keep=1)
            H[i] = torch.stack([o.hidden_states[l][0, -1] for l in keep]).float().cpu().numpy().astype(np.float16)
            lg = o.logits[0, -1].float()
            m = float(lg[t1] - lg[t2]) if r["mode"] in ("J", "S") and not a.think else None
            meta.write(json.dumps({k: r[k] for k in ("bench", "qid", "aid", "gold", "src", "mode")}
                                  | dict(margin=m, n_tok=len(ids), row=i)) + "\n")
            del o
            if (i + 1) % 200 == 0:
                print(f"  {a.tag}: {i + 1}/{len(rows)}", flush=True)
                meta.flush()
    H.flush()
    json.dump(dict(layers=keep, n_layers=n, d=d), open(out / f"layers_{a.tag}.json", "w"))
    print(f"done: capture {a.tag} {len(rows)} rows, layers {keep}", flush=True)


def steer(a):
    import torch
    tok, model, layers = setup(a.model)
    rows = [r for r in load_rows(a.items, 0) if r["mode"] == "J"]
    want = set(json.loads(Path(a.steer_ids).read_text())) if a.steer_ids else None
    if want is not None:
        rows = [r for r in rows if r["aid"] in want]
    dirs = json.loads(Path(a.directions).read_text())
    t1, t2 = verdict_ids(tok)
    scales = {"add": [float(x) for x in a.alphas.split(",")], "amplify": [float(x) for x in a.betas.split(",")]}
    out = Path(a.out)
    fh = open(out / f"steer_{a.tag}.jsonl", "w")
    for name, spec in dirs.items():
        L = spec["layer"]
        v = torch.tensor(spec["vec"], dtype=torch.float32, device="cuda")
        mu = float(spec.get("mu", 0.0))
        sd = float(spec.get("sd", 1.0))  # "add" strengths are in standard deviations of the projection
        state = {"kind": "add", "s": 0.0}

        def hook(module, inp, o):
            h = o[0] if isinstance(o, tuple) else o
            h = h.clone()
            x = h[0, -1].float()
            if state["kind"] == "add":
                x = x + state["s"] * sd * v
            else:
                x = x + state["s"] * ((x @ v) - mu) * v
            h[0, -1] = x.to(h.dtype)
            return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
        handle = layers[L - 1].register_forward_hook(hook)  # hidden_states[L] = output of decoder layer L-1
        for i, r in enumerate(rows):
            ids = build_ids(tok, r)
            res = {}
            for kind, ss in scales.items():
                for s in ss:
                    if s == 0 and kind == "amplify":
                        continue
                    state.update(kind=kind, s=s)
                    with torch.no_grad():
                        lg = model(input_ids=torch.tensor([ids], device="cuda"), logits_to_keep=1).logits[0, -1].float()
                    res[f"{kind}:{s}"] = float(lg[t1] - lg[t2])
            fh.write(json.dumps(dict(dir=name, layer=L, aid=r["aid"], qid=r["qid"], bench=r["bench"], gold=r["gold"],
                                     margins=res)) + "\n")
            if (i + 1) % 100 == 0:
                print(f"  steer {name}: {i + 1}/{len(rows)}", flush=True)
                fh.flush()
        handle.remove()
    fh.close()
    print("done: steer", flush=True)


VERDICT_RE = None


def parse_verdict(text):
    import re
    m = re.findall(r"VERDICT:\s*\**\s*(CORRECT|INCORRECT)", text or "", re.I)
    return None if not m else int(m[-1].upper() == "CORRECT")


def steergen(a):
    """Thinking-on judging with an edit while the model reasons. Edits (one per run, set by --edit):
         none                       no edit (baseline on the same stack)
         shift:<name>:<alpha>       add alpha * sd * v at the start of thinking AND at every generated token
         stretch:<name>:<beta>      at the start of thinking only: x + beta * ((x.v) - mu) * v
       Sampling T = 0.7; budget = whole context; outputs that hit the limit are redrawn from scratch (up to 3 times)."""
    import torch
    tok, model, layers = setup(a.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    rows = [r for r in load_rows(a.items, 0) if r["mode"] == "J"]
    want = json.loads(Path(a.steer_ids).read_text()) if a.steer_ids else None
    if want is not None:
        order = {x: i for i, x in enumerate(want)}
        rows = sorted([r for r in rows if r["aid"] in order], key=lambda r: order[r["aid"]])
    if a.limit:
        rows = rows[: a.limit]
    kind, name, s = (a.edit.split(":") + ["", ""])[:3] if a.edit != "none" else ("none", "", "0")
    s = float(s or 0)
    state = {"on": False, "first": True}
    handle = None
    if kind != "none":
        spec = json.loads(Path(a.directions).read_text())[name]
        L = spec["layer"]
        v = torch.tensor(spec["vec"], dtype=torch.float32, device="cuda")
        mu, sd = float(spec["mu"]), float(spec["sd"])

        def hook(module, inp, o):
            if not state["on"]:
                return o
            h = o[0] if isinstance(o, tuple) else o
            prefill = h.shape[1] > 1
            if kind == "stretch" and not prefill:
                return o  # stretch: start of thinking only
            h = h.clone()
            x = h[:, -1].float()
            if kind == "shift":
                x = x + s * sd * v
            else:
                x = x + s * ((x @ v) - mu)[:, None] * v
            h[:, -1] = x.to(h.dtype)
            return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
        handle = layers[L - 1].register_forward_hook(hook)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fpath = out / f"gen_{a.tag}.jsonl"
    done = {json.loads(l)["aid"] for l in open(fpath)} if fpath.exists() else set()
    fh = open(fpath, "a")
    todo = [r for r in rows if r["aid"] not in done]
    todo.sort(key=lambda r: len(build_ids(tok, r, think=True)))  # similar lengths per batch: less padding
    ctx = 65536
    print(f"steergen {a.edit}: {len(todo)} to do ({len(done)} done)", flush=True)

    def gen(batch):
        enc = [build_ids(tok, r, think=True) for r in batch]
        n = max(map(len, enc))
        ids = torch.full((len(enc), n), tok.pad_token_id, dtype=torch.long)
        att = torch.zeros((len(enc), n), dtype=torch.long)
        for i, e in enumerate(enc):
            ids[i, n - len(e):] = torch.tensor(e)
            att[i, n - len(e):] = 1
        state["on"] = True
        with torch.no_grad():
            g = model.generate(input_ids=ids.cuda(), attention_mask=att.cuda(), do_sample=True, temperature=0.7,
                               max_new_tokens=ctx - n - 16, pad_token_id=tok.pad_token_id)
        state["on"] = False
        res = []
        for i in range(len(batch)):
            new = g[i, n:].tolist()
            stops = {tok.eos_token_id, tok.convert_tokens_to_ids("<|im_end|>")}
            end = next((k for k, t in enumerate(new) if t in stops), None)
            clean = end is not None
            new = new[: end + 1] if clean else new  # drop the padding after the end of this sequence
            text = tok.decode(new, skip_special_tokens=False)
            res.append((text, len(new), clean))
        return res

    def gen_safe(batch):
        """Split the batch in half (recursively) if it does not fit in GPU memory."""
        try:
            return gen(batch)
        except torch.OutOfMemoryError:
            state["on"] = False
            torch.cuda.empty_cache()
            if len(batch) == 1:
                raise
            h = len(batch) // 2
            print(f"  out of memory with {len(batch)} sequences: splitting", flush=True)
            return gen_safe(batch[:h]) + gen_safe(batch[h:])

    for b0 in range(0, len(todo), a.batch):
        batch = todo[b0:b0 + a.batch]
        res = gen_safe(batch)
        for r, (text, n_out, clean) in zip(batch, res):
            tries = 1
            while not clean and tries <= 3:  # hit the context limit: redraw from scratch
                text, n_out, clean = gen_safe([r])[0]
                tries += 1
            vis = text.split("</think>")[-1] if "</think>" in text else ""
            fh.write(json.dumps(dict(aid=r["aid"], qid=r["qid"], bench=r["bench"], gold=r["gold"], edit=a.edit,
                                     verdict=parse_verdict(vis), n_out=n_out, clean=clean, tries=tries,
                                     text=text[-3000:], n_think=len(text.split("</think>")[0]))) + "\n")
        fh.flush()
        print(f"  {a.edit}: {min(b0 + a.batch, len(todo))}/{len(todo)}", flush=True)
    if handle:
        handle.remove()
    print(f"done: steergen {a.edit}", flush=True)


def solvegen(a):
    """Plain answers (thinking off) to every prompt in --qfile; one sample; whole context as budget. -> <out>/esolves_<tag>.jsonl"""
    import torch
    tok, model, layers = setup(a.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    qs = [json.loads(l) for l in open(a.qfile)]
    fpath = Path(a.out) / f"esolves_{a.tag}.jsonl"
    Path(a.out).mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["qid"] for l in open(fpath)} if fpath.exists() else set()
    todo = [q for q in qs if q["id"] not in done]
    fh = open(fpath, "a")
    stops = {tok.eos_token_id, tok.convert_tokens_to_ids("<|eot_id|>"), tok.convert_tokens_to_ids("<|im_end|>")}
    stops.discard(None)
    ctx = model.config.get_text_config().max_position_embeddings
    for b0 in range(0, len(todo), a.batch):
        batch = todo[b0:b0 + a.batch]
        enc = [build_ids(tok, dict(messages=[{"role": "user", "content": q["prompt"]}], suffix=""), think=False) for q in batch]
        n = max(map(len, enc))
        ids = torch.full((len(enc), n), tok.pad_token_id, dtype=torch.long)
        att = torch.zeros((len(enc), n), dtype=torch.long)
        for i, e in enumerate(enc):
            ids[i, n - len(e):] = torch.tensor(e)
            att[i, n - len(e):] = 1
        with torch.no_grad():
            g = model.generate(input_ids=ids.cuda(), attention_mask=att.cuda(), do_sample=True, temperature=0.7,
                               max_new_tokens=min(ctx, 131072) - n - 16, pad_token_id=tok.pad_token_id,
                               eos_token_id=list(stops))
        for i, q in enumerate(batch):
            new = g[i, n:].tolist()
            end = next((k for k, t in enumerate(new) if t in stops), None)
            new = new[: end] if end is not None else new
            fh.write(json.dumps(dict(qid=q["id"], text=tok.decode(new, skip_special_tokens=True), n_out=len(new),
                                     clean=end is not None)) + "\n")
        fh.flush()
        print(f"  solvegen: {min(b0 + a.batch, len(todo))}/{len(todo)}", flush=True)
    print("done: solvegen", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["capture", "steer", "steergen", "solvegen"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--items", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--directions", default="")
    ap.add_argument("--steer-ids", default="")
    ap.add_argument("--alphas", default="-8,-4,0,4,8")
    ap.add_argument("--betas", default="1,3,10")
    ap.add_argument("--think", action="store_true", help="capture: thinking-on template, state at the start of thinking")
    ap.add_argument("--edit", default="none", help="steergen: none | shift:<dir>:<alpha> | stretch:<dir>:<beta>")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--qfile", default="")
    a = ap.parse_args()
    {"capture": capture, "steer": steer, "steergen": steergen, "solvegen": solvegen}[a.phase](a)


if __name__ == "__main__":
    main()
