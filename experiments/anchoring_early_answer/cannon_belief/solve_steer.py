"""Does the belief direction change what the judge actually believes? Push it while Qwen3.5-9B SOLVES the question
(no candidate in the prompt), then measure belief the usual way: the share of its own answers that reach each
candidate's answer.

Same edit as steer.py (additive push alpha * sd * v at layers 14-26, last position, prompt and every generated token),
same held-out rule: an RB2 Math question in half h is pushed with the direction fitted on half 1-h
(rb2_question_half.json). Sampling as in the belief run: 7 answers per question, T = 0.7, top_p = 1, thinking off.

  python solve_steer.py --cond none
  python solve_steer.py --cond belief:-6
  python solve_steer.py --cond belief:-6 --redo-cut 32768    # answers that hit the 8192 cap, from scratch
Writes out_solve_steer/<cond>.jsonl (qid, sample, boxed answer, ...); resumes.
"""
import argparse
import json
import re
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--cond", required=True)
ap.add_argument("--model", default="Qwen/Qwen3.5-9B")
ap.add_argument("--samples", type=int, default=7)
ap.add_argument("--qbatch", type=int, default=4, help="questions per generate call (x samples sequences)")
ap.add_argument("--layers", default="14-26")
ap.add_argument("--max-new", type=int, default=8192)
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--redo-cut", type=int, default=0,
                help="regenerate, from scratch with this many new tokens, the answers in <cond>.jsonl that hit the cap; "
                     "writes <cond>_redo.jsonl (the analysis prefers it)")
ap.add_argument("--redo-batch", type=int, default=8)
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
tok.padding_side = "left"
model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="cuda").eval()
layers = model.model.layers if hasattr(model.model, "layers") else model.model.language_model.layers
qs = [json.loads(l) for l in open("rb2_solve_jobs.jsonl")]
if a.limit:
    qs = qs[: a.limit]
half = json.load(open("rb2_question_half.json"))
dirs = json.load(open("steer_dirs.json"))
name, alpha = (a.cond.split(":") + ["0"])[:2] if a.cond != "none" else ("none", "0")
alpha = float(alpha)
lo, _, hi = a.layers.partition("-")
LAYERS = list(range(int(lo), int(hi or lo) + 1))
state = {"push": {}}


def make_hook(lay):
    def hook(module, inp, o):
        v = state["push"].get(lay)
        if v is None:
            return o
        h = o[0] if isinstance(o, tuple) else o
        h = h.clone()
        h[:, -1] = (h[:, -1].float() + v).to(h.dtype)
        return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
    return hook


handles = [layers[l - 1].register_forward_hook(make_hook(l)) for l in LAYERS]
out = Path("out_solve_steer")
out.mkdir(exist_ok=True)
path = out / f"{a.cond.replace(':', '_')}.jsonl"
if a.redo_cut:
    cut = {(r["qid"], r["sample"]) for r in map(json.loads, open(path)) if not r["clean"]}
    path = out / f"{a.cond.replace(':', '_')}_redo.jsonl"
    done = {(r["qid"], r["sample"]) for r in map(json.loads, open(path))} if path.exists() else set()
    units = [(q, s) for q in qs for s in range(1, a.samples + 1) if (q["qid"], s) in cut - done]
    a.max_new, per_batch = a.redo_cut, a.redo_batch
else:
    done = {json.loads(l)["qid"] for l in open(path)} if path.exists() else set()
    units = [(q, s) for q in qs if q["qid"] in half and q["qid"] not in done for s in range(1, a.samples + 1)]
    per_batch = a.qbatch * a.samples
units.sort(key=lambda u: half[u[0]["qid"]])  # one direction half per batch
print(f"{a.cond}: {len(units)} answers to do ({len(done)} done), max {a.max_new} new tokens", flush=True)


def boxed(t):
    i = t.rfind("\\boxed{")
    if i < 0:
        return None
    j, d, s = i + 7, 1, i + 7
    while j < len(t) and d:
        d += t[j] == "{"
        d -= t[j] == "}"
        j += 1
    return t[s:j - 1]


stops = {tok.eos_token_id} | {tok.convert_tokens_to_ids(t) for t in ("<|im_end|>",) if t in tok.get_vocab()}
fh = open(path, "a")
i = 0
torch.manual_seed(a.redo_cut)
while i < len(units):
    dh = 1 - half[units[i][0]["qid"]]
    batch = [units[i]]
    while i + len(batch) < len(units) and len(batch) < per_batch and 1 - half[units[i + len(batch)][0]["qid"]] == dh:
        batch.append(units[i + len(batch)])
    i += len(batch)
    state["push"] = {}
    if name != "none":
        for l in LAYERS:
            d = dirs[f"rb2math|{name}|h{dh}|L{l}"]
            sd = dirs[f"rb2math|belief|h{dh}|L{l}"]["sd"]
            state["push"][l] = alpha * sd * torch.tensor(d["vec"], dtype=torch.float32, device="cuda")
    enc = [tok(tok.apply_chat_template(q["messages"], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False), add_special_tokens=False).input_ids for q, _ in batch]
    n = max(map(len, enc))
    ids = torch.full((len(enc), n), tok.pad_token_id, dtype=torch.long)
    att = torch.zeros((len(enc), n), dtype=torch.long)
    for k, e in enumerate(enc):
        ids[k, n - len(e):] = torch.tensor(e)
        att[k, n - len(e):] = 1
    with torch.no_grad():
        g = model.generate(input_ids=ids.cuda(), attention_mask=att.cuda(), do_sample=True, temperature=0.7,
                           top_p=1.0, top_k=0, max_new_tokens=a.max_new, pad_token_id=tok.pad_token_id)
    for k, (q, smp) in enumerate(batch):
        new = g[k, n:].tolist()
        end = next((j for j, t in enumerate(new) if t in stops), None)
        new = new[: end + 1] if end is not None else new
        text = tok.decode(new, skip_special_tokens=True)
        fh.write(json.dumps(dict(qid=q["qid"], sample=smp, cond=a.cond, boxed=boxed(text),
                                 n_out=len(new), clean=end is not None, text=text[-3000:])) + "\n")
    fh.flush()
    print(f"  {a.cond}: {i}/{len(units)}", flush=True)
print(f"SOLVE_STEER_DONE {a.cond}", flush=True)
