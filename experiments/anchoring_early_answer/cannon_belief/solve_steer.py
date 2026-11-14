"""Does the belief direction change what the judge actually believes? Push it while Qwen3.5-9B SOLVES the question
(no candidate in the prompt), then measure belief the usual way: the share of its own answers that reach each
candidate's answer.

Same edit as steer.py (additive push alpha * sd * v at layers 14-26, last position, prompt and every generated token),
same held-out rule: an RB2 Math question in half h is pushed with the direction fitted on half 1-h
(rb2_question_half.json). Sampling as in the belief run: 7 answers per question, T = 0.7, top_p = 1, thinking off.

  python solve_steer.py --cond none
  python solve_steer.py --cond belief:-6
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
done = {json.loads(l)["qid"] for l in open(path)} if path.exists() else set()
todo = [q for q in qs if q["qid"] in half and q["qid"] not in done]
todo.sort(key=lambda q: half[q["qid"]])  # one direction half per batch
print(f"{a.cond}: {len(todo)} questions to do ({len(done)} done)", flush=True)


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
torch.manual_seed(0)
while i < len(todo):
    dh = 1 - half[todo[i]["qid"]]
    batch = [todo[i]]
    while i + len(batch) < len(todo) and len(batch) < a.qbatch and 1 - half[todo[i + len(batch)]["qid"]] == dh:
        batch.append(todo[i + len(batch)])
    i += len(batch)
    state["push"] = {}
    if name != "none":
        for l in LAYERS:
            d = dirs[f"rb2math|{name}|h{dh}|L{l}"]
            sd = dirs[f"rb2math|belief|h{dh}|L{l}"]["sd"]
            state["push"][l] = alpha * sd * torch.tensor(d["vec"], dtype=torch.float32, device="cuda")
    enc = []
    for q in batch:
        t = tok.apply_chat_template(q["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        enc += [tok(t, add_special_tokens=False).input_ids] * a.samples
    n = max(map(len, enc))
    ids = torch.full((len(enc), n), tok.pad_token_id, dtype=torch.long)
    att = torch.zeros((len(enc), n), dtype=torch.long)
    for k, e in enumerate(enc):
        ids[k, n - len(e):] = torch.tensor(e)
        att[k, n - len(e):] = 1
    with torch.no_grad():
        g = model.generate(input_ids=ids.cuda(), attention_mask=att.cuda(), do_sample=True, temperature=0.7,
                           top_p=1.0, top_k=0, max_new_tokens=a.max_new, pad_token_id=tok.pad_token_id)
    for k in range(len(enc)):
        q = batch[k // a.samples]
        new = g[k, n:].tolist()
        end = next((j for j, t in enumerate(new) if t in stops), None)
        new = new[: end + 1] if end is not None else new
        text = tok.decode(new, skip_special_tokens=True)
        fh.write(json.dumps(dict(qid=q["qid"], sample=k % a.samples + 1, cond=a.cond, boxed=boxed(text),
                                 n_out=len(new), clean=end is not None, text=text[-3000:])) + "\n")
    fh.flush()
    print(f"  {a.cond}: {i}/{len(todo)}", flush=True)
print(f"SOLVE_STEER_DONE {a.cond}", flush=True)
