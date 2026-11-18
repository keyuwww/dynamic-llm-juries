"""Residual stream at the LAST token, every 2nd layer (+ the last), for any items file in dir_build.py's format
(rows: bench, qid, aid, gold, src, mode, messages, suffix; optional "think": true and "prefix" = text the model already
wrote in its own turn). Forward hooks keep only the last position, so long transcripts (thinking-on traces) fit.
Also records the verdict log-odds CORRECT vs INCORRECT at that position for J / S / JX / JT rows.

Output (dir_analyze.load format): <out>/hidden_<tag>.npy [rows, kept layers, d] float16, meta_<tag>.jsonl,
layers_<tag>.json. Resumes from meta_<tag>.jsonl.

  python capture_last.py --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 --items dir_items_roles4.jsonl.gz \
      --out out_dirs/nemotron3-nano-30b --tag roles4 [--limit 3] [--max-tokens 131072]
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--items", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--tag", required=True)
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--max-tokens", type=int, default=131072)
ap.add_argument("--shard", default="0/1")
a = ap.parse_args()

# native transformers classes (Nemotron-H included); the hub's remote code would require the mamba-ssm kernels
tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="auto")
model.eval()
inner = model.model if hasattr(model, "model") else model.backbone
if hasattr(inner, "language_model"):
    inner = inner.language_model
layers = inner.layers
n = len(layers)
keep = sorted(set(range(0, n + 1, 2)) | {n})  # index 0 = embeddings output, k = output of block k-1
d = model.config.get_text_config().hidden_size if hasattr(model.config, "get_text_config") else model.config.hidden_size
print(f"{type(model).__name__}: {n} blocks, d={d}, keep {keep}", flush=True)

cap = {}


def mk(k):
    def hook(mod, inp, out):
        h = out[0] if isinstance(out, tuple) else out
        cap[k] = h[0, -1].detach().float().cpu()
    return hook


emb = inner.embed_tokens if hasattr(inner, "embed_tokens") else inner.embeddings
emb.register_forward_hook(mk(0))
for k in keep:
    if k > 0:
        layers[k - 1].register_forward_hook(mk(k))

t1 = tok.encode(" CORRECT", add_special_tokens=False)[0]
t2 = tok.encode(" INCORRECT", add_special_tokens=False)[0]
assert t1 != t2


def build_ids(r):
    think = bool(r.get("think"))
    try:
        text = tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=think)
    except TypeError:
        text = tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True)
    ids = tok(text, add_special_tokens=False).input_ids
    tail = (r.get("prefix") or "") + (r.get("suffix") or "")
    if tail:
        ids += tok.encode(tail, add_special_tokens=False)
    return ids


with gzip.open(a.items, "rt") as f:
    rows = [json.loads(l) for l in f]
si, sn = map(int, a.shard.split("/"))
rows = [r for k, r in enumerate(rows) if k % sn == si]
if a.limit:
    seen, kept = {}, []
    for r in rows:
        kk = (r["bench"], r["mode"])
        if seen.get(kk, 0) < a.limit:
            seen[kk] = seen.get(kk, 0) + 1
            kept.append(r)
    rows = kept
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
tag = a.tag + (f"_s{si}" if sn > 1 else "")
hp = out / f"hidden_{tag}.npy"
mp = out / f"meta_{tag}.jsonl"
H = np.lib.format.open_memmap(hp, mode="r+" if hp.exists() else "w+", dtype=np.float16, shape=(len(rows), len(keep), d))
done = sum(1 for _ in open(mp)) if mp.exists() else 0
print(f"{len(rows)} rows, {done} done", flush=True)
with open(mp, "a") as meta:
    for i in range(done, len(rows)):
        r = rows[i]
        ids = build_ids(r)
        skipped = len(ids) > a.max_tokens
        m = None
        if not skipped:
            cap.clear()
            with torch.no_grad():
                o = model(input_ids=torch.tensor([ids], device=model.device), logits_to_keep=1, use_cache=False)
            H[i] = torch.stack([cap[k] for k in keep]).numpy().astype(np.float16)
            lg = o.logits[0, -1].float()
            if r["mode"] in ("J", "S", "JX", "JT"):
                m = float(lg[t1] - lg[t2])
            del o
        meta.write(json.dumps({k: r.get(k) for k in ("bench", "qid", "aid", "gold", "src", "mode")}
                              | dict(margin=m, n_tok=len(ids), row=i, skipped=skipped)) + "\n")
        if (i + 1) % 100 == 0:
            meta.flush()
            H.flush()
            print(f"  {i + 1}/{len(rows)}", flush=True)
H.flush()
json.dump(dict(layers=keep, n_layers=n, d=d), open(out / f"layers_{tag}.json", "w"))
print("CAPTURE_DONE", flush=True)
