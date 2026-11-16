"""Layer sweep for stretching: same edit as dir_capture.py --phase steer, but at many layers, with the long prompt
run once per answer and only the last token ("VERDICT:") re-run for each edit (the edit only touches that token, so
this gives the same verdict as a full re-run; the KV cache of the prompt is reused).

  capture  one pass per answer: hidden state at the last token for every 2nd layer + the unedited verdict margin
           -> <out>/hidden_<tag>.npy, meta_<tag>.jsonl, layers_<tag>.json
  dirs     for each requested layer, the question-centred "right minus wrong" direction learned on one half of the
           questions (same split and recipe as stretch_pipeline.py), applied to the other half; plus a random direction
           -> <out>/sweep_dirs_<tag>.json
  steer    for the requested layers: add -8/+8 sd and amplify x11/x21 (beta 10/20), judge and random direction
           -> <out>/sweep_<tag>_L<layers>.jsonl   one row per (answer, layer, direction): margins per edit

  python layer_sweep.py --phase capture --model meta-llama/Llama-3.1-8B-Instruct --items math_full_items.jsonl.gz --out o --tag math
  python layer_sweep.py --phase dirs --out o --tag math --layers 8,10,12
  python layer_sweep.py --phase steer --model ... --items ... --out o --tag math --layers 8,10
"""
import argparse
import collections
import json
from pathlib import Path

import numpy as np

from dir_capture import build_ids, load_rows, setup, verdict_ids


def within_auc(y, s, q):
    by = collections.defaultdict(lambda: ([], []))
    for yi, si, g in zip(y, s, q):
        by[g][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        for a in pos:
            for b in neg:
                num += 1.0 if a > b else 0.5 if a == b else 0.0
                den += 1
    return num / den if den else float("nan")


def prefix_cache(model, ids):
    import torch
    with torch.no_grad():
        o = model(input_ids=torch.tensor([ids[:-1]], device="cuda"), use_cache=True, logits_to_keep=1)
    return o.past_key_values


def last_token(model, cache, ids, n_prefix, **kw):
    import torch
    with torch.no_grad():
        o = model(input_ids=torch.tensor([ids[-1:]], device="cuda"), past_key_values=cache, use_cache=True,
                  logits_to_keep=1, **kw)
    cache.crop(n_prefix)
    return o


def capture(a):
    import torch
    tok, model, layers = setup(a.model)
    rows = load_rows(a.items, 0)
    n = len(layers)
    keep = sorted(set(range(0, n + 1, 2)) | {n})
    d = model.config.get_text_config().hidden_size
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    H = np.lib.format.open_memmap(out / f"hidden_{a.tag}.npy", mode="w+", dtype=np.float16, shape=(len(rows), len(keep), d))
    t1, t2 = verdict_ids(tok)
    with open(out / f"meta_{a.tag}.jsonl", "w") as meta:
        for i, r in enumerate(rows):
            ids = build_ids(tok, r)
            cache = prefix_cache(model, ids)
            o = last_token(model, cache, ids, len(ids) - 1, output_hidden_states=True)
            H[i] = torch.stack([o.hidden_states[l][0, -1] for l in keep]).float().cpu().numpy().astype(np.float16)
            lg = o.logits[0, -1].float()
            meta.write(json.dumps({k: r[k] for k in ("bench", "qid", "aid", "gold", "src")}
                                  | dict(margin=float(lg[t1] - lg[t2]), n_tok=len(ids), row=i)) + "\n")
            del o, cache
            if (i + 1) % 200 == 0:
                print(f"  capture: {i + 1}/{len(rows)}", flush=True)
                meta.flush()
    H.flush()
    json.dump(dict(layers=keep, n_layers=n, d=d), open(out / f"layers_{a.tag}.json", "w"))
    print(f"done: capture {len(rows)} rows", flush=True)


def make_dirs(a):
    out = Path(a.out)
    H = np.load(out / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(out / f"meta_{a.tag}.jsonl")]
    kept = json.load(open(out / f"layers_{a.tag}.json"))["layers"]
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    rng = np.random.default_rng(0)  # same split as stretch_pipeline.py
    h1q = set(rng.permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    res = {"h1_qids": sorted(h1q), "layers": {}}
    for L in [int(x) for x in a.layers.split(",")]:
        X = np.asarray(H[:, kept.index(L)], np.float32)
        Xc = X.copy()
        for g in uq:
            k = q == g
            Xc[k] -= X[k].mean(0)
        s = np.zeros(len(y))
        per = {}
        for learn, apply_, mask in (("h1", "h2", h1), ("h2", "h1", ~h1)):
            v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
            v /= np.linalg.norm(v) + 1e-9
            r = np.random.default_rng(1000 + L + (0 if learn == "h1" else 1)).normal(size=v.shape[0])
            r /= np.linalg.norm(r)
            s[~mask] = X[~mask] @ v
            for name, dv in (("Jc", v), ("Rc", r)):
                p = X[mask] @ dv
                per[f"{name}_{apply_}"] = dict(vec=dv.tolist(), mu=float(p.mean()), sd=float(p.std()))
        knows = within_auc(y, s, q)
        res["layers"][str(L)] = dict(knows=knows, dirs=per)
        print(f"  layer {L}: held-out within-question AUROC of the direction {knows:.3f}", flush=True)
    json.dump(res, open(out / f"sweep_dirs_{a.tag}.json", "w"))


def steer(a):
    import torch
    tok, model, layers = setup(a.model)
    rows = load_rows(a.items, 0)
    out = Path(a.out)
    D = json.load(open(out / f"sweep_dirs_{a.tag}.json"))
    h1q = set(D["h1_qids"])
    Ls = [int(x) for x in a.layers.split(",")]
    edits = [("add", -8.0), ("add", 8.0), ("amplify", 10.0), ("amplify", 20.0)]
    if a.limit:
        rows = rows[: a.limit]
    t1, t2 = verdict_ids(tok)
    state = {"L": None}

    def make_hook(L):
        def hook(module, inp, o):
            if state["L"] != L:
                return o
            h = o[0] if isinstance(o, tuple) else o
            h = h.clone()
            x = h[0, -1].float()
            if state["kind"] == "add":
                x = x + state["s"] * state["sd"] * state["v"]
            else:
                x = x + state["s"] * ((x @ state["v"]) - state["mu"]) * state["v"]
            h[0, -1] = x.to(h.dtype)
            return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
        return hook

    handles = [layers[L - 1].register_forward_hook(make_hook(L)) for L in Ls]  # hidden_states[L] = output of layer L-1
    vecs = {(L, nm): (torch.tensor(spec["vec"], dtype=torch.float32, device="cuda"), spec["mu"], spec["sd"])
            for L in Ls for nm, spec in D["layers"][str(L)]["dirs"].items()}
    fh = open(out / f"sweep_{a.tag}_L{'-'.join(map(str, Ls))}.jsonl", "w")
    for i, r in enumerate(rows):
        half = "h1" if r["qid"] in h1q else "h2"
        ids = build_ids(tok, r)
        cache = prefix_cache(model, ids)
        state["L"] = None
        lg = last_token(model, cache, ids, len(ids) - 1).logits[0, -1].float()
        base = float(lg[t1] - lg[t2])
        for L in Ls:
            for name in ("Jc", "Rc"):
                v, mu, sd = vecs[(L, f"{name}_{half}")]
                res = {"none": base}
                for kind, s in edits:
                    state.update(L=L, kind=kind, s=s, v=v, mu=mu, sd=sd)
                    lg = last_token(model, cache, ids, len(ids) - 1).logits[0, -1].float()
                    res[f"{kind}:{s}"] = float(lg[t1] - lg[t2])
                state["L"] = None
                fh.write(json.dumps(dict(dir=name, layer=L, aid=r["aid"], qid=r["qid"], gold=r["gold"], src=r["src"],
                                         margins=res)) + "\n")
        del cache
        if (i + 1) % 100 == 0:
            print(f"  steer L{Ls}: {i + 1}/{len(rows)}", flush=True)
            fh.flush()
    for h in handles:
        h.remove()
    fh.close()
    print("done: steer", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["capture", "dirs", "steer"], required=True)
    ap.add_argument("--model")
    ap.add_argument("--items")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--layers", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    {"capture": capture, "dirs": make_dirs, "steer": steer}[a.phase](a)


if __name__ == "__main__":
    main()
