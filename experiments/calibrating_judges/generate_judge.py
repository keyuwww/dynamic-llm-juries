#!/usr/bin/env python
"""Run a judge model locally as a reasoning judge (paper prompts, see prompts.py) and save its outputs; optionally save the judge's own
residual-stream activations at the LAST token of its generated output (the probe's input in arXiv 2512.22245).

  --prompt uncertainty   reasoning + verbal uncertainty + verdict            (probe training runs; consistency / majority samples)
  --prompt confidence    the same plus a 0-100 confidence score             (verbalized-confidence baseline)
  --n-samples N --temperature T                                              (N=10, T=0.7 for the consistency / majority baselines)
  --save-acts (needs n-samples 1): after generation, one forward pass over prompt + generated text; keep the hidden state of the last generated
  token (the first EOS if the model stopped, else the last token if it was cut at max-new-tokens) at every --layer-step-th layer.

Outputs in --out: <tag>_gen.jsonl (one line per item and sample), and with --save-acts <tag>_acts.npy / <tag>_layers.json / <tag>_items.csv."""
import argparse, json, os, re, time
import numpy as np, pandas as pd, torch
from judge_data import load_items
from prompts import build_prompt, PAIRWISE


def parse(text, bench):
    pat = r"<answer>\s*\[\[([AB])\]\]\s*</answer>" if bench in PAIRWISE else r"<answer>\s*(INCORRECT|CORRECT)\s*</answer>"
    m = re.findall(pat, text, flags=re.I); v = m[-1].upper() if m else None
    if v is not None and bench not in PAIRWISE:
        v = int(v == "CORRECT")
    c = re.findall(r"<confidence>\s*([0-9]*\.?[0-9]+)\s*</confidence>", text); conf = min(max(float(c[-1]) / 100.0, 0.0), 1.0) if c else None
    return v, conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--bench", required=True, choices=["bff", "rb2safety", "judgebench", "ppe_correct", "ppe_pref"])
    ap.add_argument("--data", help="judgments jsonl (bff / rb2safety: gives the item set and the human labels)"); ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--jb-dir")
    ap.add_argument("--prompt", default="uncertainty", choices=["uncertainty", "confidence"]); ap.add_argument("--n-samples", type=int, default=1); ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-new-tokens", type=int, default=1024); ap.add_argument("--batch-size", type=int, default=16); ap.add_argument("--max-batch-tokens", type=int, default=8000, help="cap on (prompts x samples x longest prompt) per batch; long prompts get small batches"); ap.add_argument("--max-len", type=int, default=8192)
    ap.add_argument("--save-acts", action="store_true"); ap.add_argument("--layer-step", type=int, default=2); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="gen"); ap.add_argument("--dtype", default="bfloat16"); ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu"); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(); assert not (a.save_acts and a.n_samples != 1)
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.manual_seed(a.seed)
    items = load_items(a.bench, a.data, a.verdicts_path, a.rb2_path, a.jb_dir)
    if a.limit:
        items = items[:a.limit]
    tag = f"{a.model.split('/')[-1]}__{a.bench}__{a.prompt}__n{a.n_samples}_t{a.temperature}"; os.makedirs(a.out, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True); tok.padding_side, tok.truncation_side = "left", "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def templ(text):
        msgs = [dict(role="user", content=text)]
        if getattr(tok, "chat_template", None) is None:
            return text
        try:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    prompts = [templ(build_prompt(a.bench, a.prompt, it)) for it in items]; lens = [len(tok(p, add_special_tokens=False)["input_ids"]) for p in prompts]
    print(f"[{tag}] {len(items)} items; prompt tokens mean {np.mean(lens):.0f} max {max(lens)} (truncated to {a.max_len})\nexample prompt tail:\n{prompts[0][-250:]}\n", flush=True)

    dt = getattr(torch, a.dtype)
    def load(cls):
        for kw in ("dtype", "torch_dtype"):
            try:
                return cls.from_pretrained(a.model, trust_remote_code=True, **{kw: dt})
            except (TypeError, ValueError) as e:
                err = e
        raise err
    try:
        model = load(AutoModelForCausalLM)
    except Exception as e:
        from transformers import AutoModel
        print("AutoModelForCausalLM failed:", repr(e)[:120], "-> AutoModel", flush=True); model = load(AutoModel)
    model = model.to(a.device).eval(); eos = tok.eos_token_id
    eos_ids = set([eos] if isinstance(eos, int) else (eos or [])) | ({tok.convert_tokens_to_ids("<|im_end|>")} if "<|im_end|>" in tok.get_vocab() else set())
    order = np.argsort(lens)[::-1]; batches, cur = [], []
    for i in order:
        if cur and (len(cur) >= a.batch_size or (len(cur) + 1) * a.n_samples * min(lens[cur[0]], a.max_len) > a.max_batch_tokens):
            batches.append(cur); cur = []
        cur.append(int(i))
    batches.append(cur)
    print(f"{len(batches)} batches (sizes {min(map(len, batches))} to {max(map(len, batches))})", flush=True)
    gen_kw = dict(max_new_tokens=a.max_new_tokens, pad_token_id=tok.pad_token_id, num_return_sequences=a.n_samples)
    gen_kw.update(dict(do_sample=True, temperature=a.temperature, top_p=1.0, top_k=0) if a.temperature > 0 else dict(do_sample=False))
    acts, layers, rows, t0, n_tok = None, None, [], time.time(), 0
    for b, idx in enumerate(batches):
        enc = tok([prompts[i] for i in idx], return_tensors="pt", padding=True, truncation=True, max_length=a.max_len, add_special_tokens=False).to(a.device)
        with torch.no_grad():
            seq = model.generate(**enc, **gen_kw)
        P = enc["input_ids"].shape[1]; gen = seq[:, P:].cpu(); print(f"  batch {b + 1}/{len(batches)}: {len(idx)} prompts x {a.n_samples}, generation done at {time.time() - t0:.0f}s", flush=True)
        lengths = []
        for r in range(gen.shape[0]):
            g = gen[r].tolist(); k = next((j for j, t in enumerate(g) if t in eos_ids), None); lengths.append(k + 1 if k is not None else len(g))
        for r in range(gen.shape[0]):
            i = idx[r // a.n_samples]; it = items[i]; L = lengths[r]; text = tok.decode(gen[r, :L], skip_special_tokens=True); v, conf = parse(text, a.bench); n_tok += L
            rows.append(dict(item_id=it["item_id"], group=it["group"], sample=r % a.n_samples, gold=it["gold"], verdict=v, correct=int(v == it["gold"]) if v is not None else 0,
                             confidence=conf, n_tokens=L, truncated=bool(L == a.max_new_tokens and gen[r, L - 1].item() not in eos_ids), text=text))
        if a.save_acts:
            for lo in range(0, gen.shape[0], 4):                                   # forward over prompt + generation, in chunks of 4 sequences
                sl = slice(lo, min(lo + 4, gen.shape[0])); ids = seq[sl]
                mask = torch.cat([enc["attention_mask"][sl].cpu(), torch.zeros_like(gen[sl])], 1).to(a.device)
                for r in range(ids.shape[0]):
                    mask[r, P:P + lengths[lo + r]] = 1
                pos = (mask.cumsum(-1) - 1).clamp(min=0)
                with torch.no_grad():
                    for extra in (dict(position_ids=pos), dict()):
                        try:
                            out = model(input_ids=ids, attention_mask=mask, output_hidden_states=True, use_cache=False, **extra); break
                        except TypeError:
                            continue
                hs = out.hidden_states; Lm = len(hs) - 1
                if layers is None:
                    layers = sorted(set(range(0, Lm + 1, a.layer_step)) | {Lm}); acts = np.zeros((len(items), len(layers), hs[0].shape[-1]), dtype=np.float16)
                    print(f"{Lm} transformer layers; capturing hidden_states at {layers}", flush=True)
                for r in range(ids.shape[0]):
                    acts[idx[(lo + r) // a.n_samples]] = torch.stack([hs[l][r, P + lengths[lo + r] - 1, :] for l in layers]).float().cpu().numpy().astype(np.float16)
                del out, hs
        print(f"batch {b + 1}/{len(batches)}  {time.time() - t0:.0f}s  generated tokens so far {n_tok}", flush=True)
    df = pd.DataFrame(rows); df.to_json(os.path.join(a.out, f"{tag}_gen.jsonl"), orient="records", lines=True)
    print(f"parsed {df.verdict.notna().mean():.3f}  truncated {df.truncated.mean():.3f}  verdict accuracy {df.correct.mean():.3f}  mean tokens {df.n_tokens.mean():.0f}", flush=True)
    if a.save_acts:
        assert np.isfinite(acts.astype(np.float32)).all(), "non-finite activations"
        np.save(os.path.join(a.out, f"{tag}_acts.npy"), acts); json.dump(layers, open(os.path.join(a.out, f"{tag}_layers.json"), "w"))
        pd.DataFrame({"item_id": [it["item_id"] for it in items], "group": [it["group"] for it in items]}).to_csv(os.path.join(a.out, f"{tag}_items.csv"), index=False)
    print(f"saved {tag}", flush=True)


if __name__ == "__main__":
    main()
