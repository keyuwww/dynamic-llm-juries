#!/usr/bin/env python3
"""
Step 8 of Trust / Read / Think: staged thinking and longer thinking, compared at equal thinking-token cost.

All policies start from the same free forward pass (gut + probe, probe trained on 100 labels as in Step 7).
Cost = thinking tokens actually used per test item (a think at budget B costs min(B, the model's own thinking length);
a long think continues the short one, so it costs min(2,048, length) in total, not 512 + 2,048).
  gut->think@1024     gut verdict, think 1,024 on the least confident gut items          (standard escalation)
  gut->think@2048     the same with 2,048 tokens
  v2@1024             cascade v2: more confident of gut/probe; think 1,024 on the least confident
  v2@2048             cascade v2 with 2,048 tokens ("more tokens for the items that think")
  v2+staged           cascade v2; short think (512) on the least confident; continue to 2,048 only where the short
                      think disagrees with the free verdict or is unsure (confidence < 0.8, fixed in advance)
Each policy is swept over the share of items it thinks on (0-100%), giving an accuracy-vs-tokens curve; accuracy is
read off each curve at the same average token costs (linear interpolation). 10 random draws of the 100 labels.

  .venv/bin/python experiments/trust_read_think/step8.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
import step2
from step2 import probe
from step5 import pick_layer
from step6 import draw_labels

HERE = Path(__file__).resolve().parent
from paths import RAW, RES, ITEMS  # noqa: E402
BENCHES = ("safety", "focus", "math", "bff", "factuality")
N_LAB, DRAWS = 100, 10
SHARES = np.linspace(0, 1, 21)
COSTS = (100, 200, 300, 500)        # average thinking tokens per item
TAU = 0.8


def load():
    items = [json.loads(l) for f in ("items.jsonl", "items_factuality.jsonl") for l in open(ITEMS / f)]
    D = {}
    for b in BENCHES:
        sub = [it for it in items if it["bench"] == b]
        th = {json.loads(l)["id"]: json.loads(l) for l in open(RAW / f"{b}_think.jsonl")}
        f = np.load(RAW / f"{b}_fast.npz")
        T = [th[it["id"]] for it in sub]
        D[b] = dict(y=np.array([it["gold"] for it in sub]), g=np.array([it["group"] for it in sub]),
                    hs=f["hs"].astype(np.float32), gut=f["p"],
                    p={B: np.array([t["p_budget"][str(B)] for t in T]) for B in (512, 1024, 2048)},
                    tlen=np.array([t["think_tokens"] for t in T]))
    return D


conf = lambda p: np.abs(2 * p - 1)


def probe_scores(d, lab, te):
    y, g, hs = d["y"], d["g"], d["hs"]
    L = pick_layer(hs[lab], y[lab], g[lab], 20)
    oof = np.zeros(len(lab))
    for a, c in GroupKFold(5).split(lab, y[lab], g[lab]):
        oof[c] = probe().fit(hs[lab[a], L], y[lab[a]]).decision_function(hs[lab[c], L])
    platt = LogisticRegression(C=1e4).fit(oof[:, None], y[lab])
    return platt.predict_proba(probe().fit(hs[lab, L], y[lab]).decision_function(hs[te, L])[:, None])[:, 1]


def curves(d, te, pr):
    y, gut, P, tl = d["y"][te], d["gut"][te], {B: v[te] for B, v in d["p"].items()}, d["tlen"][te]
    n = len(te)
    cost = {B: np.minimum(tl, B) for B in (512, 1024, 2048)}
    base_v2 = np.where(conf(gut) >= conf(pr), gut, pr)
    order_gut = np.argsort(conf(gut), kind="stable")
    order_v2 = np.argsort(np.maximum(conf(gut), conf(pr)), kind="stable")
    acc = lambda s: float(((s > 0.5) == y).mean())
    out = {k: [] for k in ("gut->think@1024", "gut->think@2048", "v2@1024", "v2@2048", "v2+staged")}
    for sh in SHARES:
        k = int(round(sh * n))
        for name, base, order, B in (("gut->think@1024", gut, order_gut, 1024), ("gut->think@2048", gut, order_gut, 2048),
                                     ("v2@1024", base_v2, order_v2, 1024), ("v2@2048", base_v2, order_v2, 2048)):
            s = base.copy()
            idx = order[:k]
            s[idx] = P[B][idx]
            out[name].append((float(cost[B][idx].sum() / n), acc(s)))
        # staged: short think on the k least confident; continue where it disagrees or is unsure
        s = base_v2.copy()
        idx = order_v2[:k]
        short = P[512][idx]
        go = ((short > 0.5) != (base_v2[idx] > 0.5)) | (conf(short) < TAU)
        s[idx] = np.where(go, P[2048][idx], short)
        c = np.where(go, cost[2048][idx], cost[512][idx]).sum() / n
        out["v2+staged"].append((float(c), acc(s)))
    return out


def at_cost(curve, c):
    xs, ys = zip(*sorted(curve))
    if c > xs[-1]:
        return float("nan")            # this policy cannot spend that much (it thinks on every item below it)
    return float(np.interp(c, xs, ys))


def main():
    D = load()
    res = {}
    for b in BENCHES:
        d = D[b]
        per = []
        for seed in range(DRAWS):
            lab = draw_labels(d["g"], np.random.default_rng(seed), N_LAB)
            te = np.setdiff1d(np.arange(len(d["y"])), lab)
            cv = curves(d, te, probe_scores(d, lab, te))
            per.append({name: [at_cost(c, x) for x in COSTS] for name, c in cv.items()})
        res[b] = {name: [round(float(np.nanmean([p[name][i] for p in per])), 3) for i in range(len(COSTS))]
                  for name in per[0]}
        res[b]["mean_think_tokens_if_all_1024"] = int(np.minimum(d["tlen"], 1024).mean())
        print(f"== {b}  (tokens/item: {COSTS})", flush=True)
        for name, v in res[b].items():
            print(f"   {name:18s} {v}", flush=True)
    avg = {name: [round(float(np.nanmean([res[b][name][i] for b in BENCHES])), 3) for i in range(len(COSTS))]
           for name in res[BENCHES[0]] if name.startswith(("gut", "v2"))}
    res["average"] = avg
    print("== average", json.dumps(avg), flush=True)
    (RES / "step8.json").write_text(json.dumps(dict(costs=COSTS, tau=TAU, results=res), indent=1))


if __name__ == "__main__":
    main()
