"""Minimal pairs, second pass: let the judge write its brief reasoning and verdict for every pair item (greedy, thinking
off), then capture the hidden state + verdict margin at the verdict word (checkpoint C = transcript up to and
including "VERDICT:", or transcript + "\n\nVERDICT:" when it never wrote one).

  python pairs_gen.py --judge qwen3.5-9b --model Qwen/Qwen3.5-9B --outdir out_pairs_C
Writes <outdir>/gen_<judge>.jsonl (resumes), pair_jobs_C_<judge>.jsonl.gz, then runs capture.py on it.
"""
import argparse
import gzip
import json
import subprocess
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--judge", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--jobs", default="pair_jobs.jsonl.gz")
ap.add_argument("--outdir", default="out_pairs_C")
ap.add_argument("--batch", type=int, default=32)
ap.add_argument("--max-new", type=int, default=2048)
ap.add_argument("--limit", type=int, default=0)
a = ap.parse_args()

jobs = [j for j in map(json.loads, gzip.open(a.jobs, "rt")) if j["judge"] == a.judge]
if a.limit:
    jobs = jobs[: a.limit]
out = Path(a.outdir)
out.mkdir(parents=True, exist_ok=True)
gpath = out / f"gen_{a.judge}.jsonl"
done = {json.loads(l)["item_id"] for l in open(gpath)} if gpath.exists() else set()
todo = [j for j in jobs if j["item_id"] not in done]
print(f"{a.judge}: {len(todo)} to generate ({len(done)} done)", flush=True)

if todo:
    tok = AutoTokenizer.from_pretrained(a.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="cuda").eval()
    stops = {tok.eos_token_id} | {tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|eot_id|>")
                                  if t in tok.get_vocab()}
    enc = {j["item_id"]: tok(tok.apply_chat_template(j["messages"], tokenize=False, add_generation_prompt=True,
                                                     enable_thinking=False), add_special_tokens=False).input_ids
           for j in todo}
    todo.sort(key=lambda j: len(enc[j["item_id"]]))
    fh = open(gpath, "a")
    for b in range(0, len(todo), a.batch):
        batch = todo[b: b + a.batch]
        E = [enc[j["item_id"]] for j in batch]
        n = max(map(len, E))
        ids = torch.full((len(E), n), tok.pad_token_id, dtype=torch.long)
        att = torch.zeros((len(E), n), dtype=torch.long)
        for i, e in enumerate(E):
            ids[i, n - len(e):] = torch.tensor(e)
            att[i, n - len(e):] = 1
        with torch.no_grad():
            g = model.generate(input_ids=ids.cuda(), attention_mask=att.cuda(), do_sample=False,
                               max_new_tokens=a.max_new, pad_token_id=tok.pad_token_id)
        for i, j in enumerate(batch):
            new = g[i, n:].tolist()
            end = next((t for t, x in enumerate(new) if x in stops), None)
            new = new[:end] if end is not None else new
            fh.write(json.dumps(dict(item_id=j["item_id"], text=tok.decode(new, skip_special_tokens=True),
                                     n_out=len(new), clean=end is not None)) + "\n")
        fh.flush()
        print(f"  {min(b + a.batch, len(todo))}/{len(todo)}", flush=True)
    del model
    torch.cuda.empty_cache()

gen = {r["item_id"]: r for r in map(json.loads, open(gpath))}
cj = []
for j in jobs:
    t = gen[j["item_id"]]["text"]
    i = t.rfind("VERDICT:")
    pre = t[: i + len("VERDICT:")] if i >= 0 else t.rstrip() + "\n\nVERDICT:"
    cj.append(dict(judge=j["judge"], item_id=j["item_id"], bench=j["bench"], messages=j["messages"],
                   ckpts=[["C", pre, [" CORRECT", " INCORRECT"]]]))
cpath = f"pair_jobs_C_{a.judge}.jsonl.gz"
with gzip.open(cpath, "wt") as f:
    f.write("".join(json.dumps(r) + "\n" for r in cj))
subprocess.run([sys.executable, "capture.py", "--judge", a.judge, "--model", a.model, "--jobs", cpath, "--margins",
                "--outdir", a.outdir], check=True)
print("PAIRS_GEN_DONE", flush=True)
