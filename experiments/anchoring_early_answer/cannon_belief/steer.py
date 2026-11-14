"""Steer Qwen3.5-9B along a direction while it writes its judging reasoning (thinking off), then read its spoken verdict.

Edit at layer L (hidden_states[L] = output of decoder layer L-1): x <- x + alpha * sd * v at the last position of the
prompt and at every generated token, i.e. throughout the reasoning. v / sd from steer_dirs.json; each item uses the
direction fitted on the OTHER half of its benchmark's questions. Greedy decoding, so every condition judges exactly the
same items the same way except for the edit (paired). Budget: the whole 64K context.

  python steer.py --cond none
  python steer.py --cond belief:-8          # ADD: <direction>:<alpha in SDs of the belief projection>
  python steer.py --cond belief*-5          # SCALE: x <- x + (lam-1) * ((x.v) - mu) * v, i.e. each item's own position
                                            # along v (around the fitting half's mean mu) is multiplied by lam:
                                            # 0 = remove it, -5 = reverse and stretch it, 5 = stretch it
Writes out_steer/<cond>.jsonl (resumes).
"""
import argparse
import gzip
import json
import re
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--cond", required=True)
ap.add_argument("--model", default="Qwen/Qwen3.5-9B")
ap.add_argument("--batch", type=int, default=8)
ap.add_argument("--limit", type=int, default=0, help="pilot: first N items per (bench, group)")
ap.add_argument("--layers", default="20", help="layers to push at, e.g. 20 or 14-26 (each with its own direction)")
ap.add_argument("--max-new", type=int, default=0, help="pilot only: cap on generated tokens (0 = whole context)")
ap.add_argument("--items", default="steer_items.jsonl.gz")
ap.add_argument("--dirs", default="steer_dirs.json")
ap.add_argument("--outdir", default="out_steer")
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
tok.padding_side = "left"
if tok.pad_token is None:  # Llama
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="cuda").eval()
layers = model.model.layers if hasattr(model.model, "layers") else model.model.language_model.layers
items = [json.loads(l) for l in gzip.open(a.items, "rt")]
if a.limit:
    seen, keep = {}, []
    for x in items:
        k = (x["bench"], x["group"])
        if seen.get(k, 0) < a.limit:
            seen[k] = seen.get(k, 0) + 1
            keep.append(x)
    items = keep
dirs = json.load(open(a.dirs))
SCALE = "*" in a.cond
name, alpha = (a.cond.split("*" if SCALE else ":") + ["0"])[:2] if a.cond != "none" else ("none", "0")
alpha = float(alpha)
lo, _, hi = a.layers.partition("-")
LAYERS = list(range(int(lo), int(hi or lo) + 1))
state = {"push": {}}  # layer -> push vector for the current batch


def make_hook(lay):
    def hook(module, inp, o):
        v = state["push"].get(lay)
        if v is None:
            return o
        h = o[0] if isinstance(o, tuple) else o
        h = h.clone()
        x = h[:, -1].float()
        if SCALE:
            u, mu = v
            x = x + (alpha - 1) * ((x @ u) - mu)[:, None] * u[None, :]
        else:
            x = x + v
        h[:, -1] = x.to(h.dtype)
        return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
    return hook


handles = [layers[l - 1].register_forward_hook(make_hook(l)) for l in LAYERS]  # hidden_states[l] = output of layer l-1
out = Path(a.outdir)
out.mkdir(exist_ok=True)
tag = a.cond.replace(':', '_').replace('*', '_x') + (f"_L{a.layers}" if a.layers != "20" else "")
path = out / f"{tag}{'_pilot' if a.limit else ''}.jsonl"
done = {json.loads(l)["aid"] for l in open(path)} if path.exists() else set()
todo = [x for x in items if x["aid"] not in done]


def ids_of(x):
    t = tok.apply_chat_template(x["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return tok(t, add_special_tokens=False).input_ids


# group by (bench, direction half): one push vector per batch
todo.sort(key=lambda x: (x["bench"], x["dir_half"], len(ids_of(x))))
print(f"{a.cond}: {len(todo)} to do ({len(done)} done), layers {LAYERS}", flush=True)
stops = {tok.eos_token_id} | {tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|eot_id|>") if t in tok.get_vocab()}
fh = open(path, "a")
i = 0
while i < len(todo):
    key = (todo[i]["bench"], todo[i]["dir_half"])
    batch = [todo[i]]
    while i + len(batch) < len(todo) and len(batch) < a.batch and \
            (todo[i + len(batch)]["bench"], todo[i + len(batch)]["dir_half"]) == key:
        batch.append(todo[i + len(batch)])
    i += len(batch)
    state["push"] = {}
    if name != "none":
        for l in LAYERS:
            d = dirs[f"{key[0]}|{name}|h{key[1]}|L{l}"]
            vec = torch.tensor(d["vec"], dtype=torch.float32, device="cuda")
            if SCALE:
                state["push"][l] = (vec, d["mu"])
            else:
                # same push length for every direction: SD of the BELIEF projection at that layer
                sd = dirs[f"{key[0]}|belief|h{key[1]}|L{l}"]["sd"]
                state["push"][l] = alpha * sd * vec
    enc = [ids_of(x) for x in batch]
    n = max(map(len, enc))
    ids = torch.full((len(enc), n), tok.pad_token_id, dtype=torch.long)
    att = torch.zeros((len(enc), n), dtype=torch.long)
    for k, e in enumerate(enc):
        ids[k, n - len(e):] = torch.tensor(e)
        att[k, n - len(e):] = 1
    with torch.no_grad():
        g = model.generate(input_ids=ids.cuda(), attention_mask=att.cuda(), do_sample=False,
                           max_new_tokens=a.max_new or 65536 - n - 16, pad_token_id=tok.pad_token_id)
    for k, x in enumerate(batch):
        new = g[k, n:].tolist()
        end = next((j for j, t in enumerate(new) if t in stops), None)
        new = new[: end + 1] if end is not None else new
        text = tok.decode(new, skip_special_tokens=True)
        m = re.findall(r"VERDICT:\s*\**\s*(CORRECT|INCORRECT)", text, re.I)
        fh.write(json.dumps(dict(aid=x["aid"], bench=x["bench"], q=x["q"], group=x["group"], belief=x["belief"],
                                 gold=x["gold"], cond=a.cond, verdict=None if not m else int(m[-1].upper() == "CORRECT"),
                                 n_out=len(new), clean=end is not None, layers=a.layers, text=text[-2500:])) + "\n")
    fh.flush()
    print(f"  {a.cond}: {i}/{len(todo)}", flush=True)
for hd in handles:
    hd.remove()
print(f"STEER_DONE {a.cond}", flush=True)
