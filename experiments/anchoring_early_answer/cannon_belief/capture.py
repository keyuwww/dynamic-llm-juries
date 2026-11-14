"""Hidden states (every layer, last token) at each checkpoint of each judging transcript. One forward pass per
checkpoint: chat template (thinking off) + the transcript up to the checkpoint (ckpts.checkpoints prefix).
Writes out/<judge>/hidden_ckpt.npy float16 [n, 33, d] + meta_ckpt.jsonl (judge, item_id, bench, ckpt, n_tok); resumes.

  python capture.py --judge qwen3.5-9b --model Qwen/Qwen3.5-9B
  python capture.py --judge llama3.1-8b --model meta-llama/Llama-3.1-8B-Instruct --jobs ckpt_jobs_llama.jsonl.gz --margins

--margins also scores the two verdict options after each checkpoint (job "opts"): margin = log p(option 1) - log p(option
2) summed over the option's tokens (option 1 = CORRECT / A), saved in meta as "margin". Two passes per checkpoint.
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--judge", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--jobs", default="ckpt_jobs.jsonl.gz")
ap.add_argument("--margins", action="store_true")
ap.add_argument("--outdir", default="out")
a = ap.parse_args()
tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="cuda").eval()
jobs = [j for j in map(json.loads, gzip.open(a.jobs, "rt")) if j["judge"] == a.judge]
if a.limit:
    jobs = jobs[: a.limit]
out = Path(a.outdir) / a.judge
out.mkdir(parents=True, exist_ok=True)
parts = sorted(out.glob("part_*.npy"))
done = set()
for p in sorted(out.glob("meta_part_*.jsonl")):
    done |= {(r["item_id"], r["ckpt"]) for r in map(json.loads, open(p))}
todo = [(j, c[0], c[1], c[2] if len(c) > 2 else None) for j in jobs for c in j["ckpts"] if (j["item_id"], c[0]) not in done]
print(f"{a.judge}: {len(todo)} checkpoints to capture ({len(done)} done)", flush=True)
buf, meta, k = [], [], len(parts)


def flush():
    global buf, meta, k
    if buf:
        np.save(out / f"part_{k:04d}.npy", np.stack(buf))
        with open(out / f"meta_part_{k:04d}.jsonl", "w") as f:
            f.write("".join(json.dumps(m) + "\n" for m in meta))
        k += 1
    buf, meta = [], []


with torch.no_grad():
    for i, (j, name, pre, opts) in enumerate(todo):
        base = tok.apply_chat_template(j["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = tok(base, add_special_tokens=False).input_ids + tok.encode(pre, add_special_tokens=False)
        P = len(ids)
        m = dict(judge=a.judge, item_id=j["item_id"], bench=j["bench"], ckpt=name, n_tok=P)
        if a.margins and opts:
            lps = []
            for oi, opt in enumerate(opts):
                ot = tok.encode(opt, add_special_tokens=False)
                # logits only for the last len(ot)+1 positions: P-1 .. P+len(ot)-1 (the first len(ot) predict ot)
                o = model(input_ids=torch.tensor([ids + ot], device="cuda"), output_hidden_states=(oi == 0),
                          logits_to_keep=len(ot) + 1)
                lp = torch.log_softmax(o.logits[0, :len(ot)].float(), -1)
                lps.append(float(sum(lp[t, x] for t, x in enumerate(ot))))
                if oi == 0:  # hidden state at the last token of the prefix (the checkpoint)
                    hs = torch.stack([h[0, P - 1] for h in o.hidden_states])
            m["margin"] = lps[0] - lps[1]
        else:
            o = model(input_ids=torch.tensor([ids], device="cuda"), output_hidden_states=True, logits_to_keep=1)
            hs = torch.stack([h[0, -1] for h in o.hidden_states])
        buf.append(hs.float().cpu().numpy().astype(np.float16))
        meta.append(m)
        if len(buf) >= 500:
            flush()
            print(f"  {i + 1}/{len(todo)}", flush=True)
flush()
P = sorted(out.glob("part_*.npy"))
np.save(out / "hidden_ckpt.npy", np.concatenate([np.load(p) for p in P]))
with open(out / "meta_ckpt.jsonl", "w") as f:
    for p in sorted(out.glob("meta_part_*.jsonl")):
        f.write(open(p).read())
print("CAPTURE_DONE", flush=True)
