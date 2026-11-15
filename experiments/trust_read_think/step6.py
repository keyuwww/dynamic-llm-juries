#!/usr/bin/env python3
"""
Step 6 of Trust / Read / Think: does the 50-label "read or think" recipe pick the right read, including on a benchmark
that was never used to design it (RewardBench 2 Factuality)?

The recipe, fixed before looking at Factuality:
  1. Label ~50 items (variants: 100 items; leave-one-question-out CV in step 2) of the benchmark (25 questions' worth of items, drawn at random).
  2. On those 50 only, cross-validate a probe (standardize + L2 logistic, C = 0.3; layer by inner CV of a
     difference-of-means probe, as in Step 5) against the gut, same-source AUROC.
  3. Probe wins  -> READ: the probe trained on the 50 labels gives every verdict (no thinking).
     Gut wins    -> ROUTE: keep the gut, think (1,024 tokens) on the 30% least confident items.
Evaluated on the remaining items (never the 50 labelled ones), 20 random draws of the 50, against fixed policies:
  trust (gut only), read (always), route (always), think (thinking on every item).
Reported: how often the recipe picks READ, same-source AUROC and accuracy of each policy, thinking share (cost).

  .venv/bin/python experiments/trust_read_think/step6.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
import step2
from step2 import strata_auc, probe
from step5 import pick_layer

HERE = Path(__file__).resolve().parent
from paths import RAW, RES, ITEMS  # noqa: E402
BENCHES = ("safety", "focus", "math", "bff", "factuality")
DRAWS, TB, Q = 20, 1024, 0.3
# decision variants: (labels, cross-validation in the decision step). "5fold" is the original recipe; "loqo" leaves one
# question out per fold, so the probe in the decision step trains on almost all labelled items.
VARIANTS = [(50, "5fold"), (50, "loqo"), (100, "5fold"), (100, "loqo")]


def load():
    items = [json.loads(l) for f in ("items.jsonl", "items_factuality.jsonl") for l in open(ITEMS / f)]
    D = {}
    for b in BENCHES:
        sub = [it for it in items if it["bench"] == b]
        th = {json.loads(l)["id"]: json.loads(l) for l in open(RAW / f"{b}_think.jsonl")}
        f = np.load(RAW / f"{b}_fast.npz")
        D[b] = dict(y=np.array([it["gold"] for it in sub]), g=np.array([it["group"] for it in sub]),
                    st=np.array([it["strata"] for it in sub]), hs=f["hs"].astype(np.float32), gut=f["p"],
                    think=np.array([th[it["id"]]["p_budget"][str(TB)] for it in sub]))
    return D


def draw_labels(g, rng, n_lab):
    pick, n = [], 0
    for q in rng.permutation(np.unique(g)):
        ii = np.where(g == q)[0]
        pick.append(ii)
        n += len(ii)
        if n >= n_lab:
            break
    return np.concatenate(pick)


def main():
    D = load()
    res = {}
    for n_lab, cv in VARIANTS:
        res[f"{n_lab}_{cv}"] = run(D, n_lab, cv)
    (RES / "step6.json").write_text(json.dumps(res, indent=1))


def run(D, n_lab, cv):
    res = {}
    print(f"== {n_lab} labels, {cv}", flush=True)
    for b in BENCHES:
        d = D[b]
        y, g, st, hs, gut, think = d["y"], d["g"], d["st"], d["hs"], d["gut"], d["think"]
        unc = 1 - np.abs(2 * gut - 1)
        rows = []
        for seed in range(DRAWS):
            rng = np.random.default_rng(seed)
            lab = draw_labels(g, rng, n_lab)
            test = np.setdiff1d(np.arange(len(y)), lab)
            # decision on the labelled items only
            L = pick_layer(hs[lab], y[lab], g[lab], 20)
            oof = np.zeros(len(lab))
            nf = len(np.unique(g[lab])) if cv == "loqo" else 5
            for a, c in GroupKFold(nf).split(lab, y[lab], g[lab]):
                oof[c] = probe().fit(hs[lab[a], L], y[lab[a]]).predict_proba(hs[lab[c], L])[:, 1]
            p_auc, g_auc = strata_auc(oof, y[lab], st[lab]), strata_auc(gut[lab], y[lab], st[lab])
            choose_read = p_auc > g_auc
            # policies on the held-out items
            read = probe().fit(hs[lab, L], y[lab]).predict_proba(hs[test, L])[:, 1]
            yt, stt = y[test], st[test]
            k = int(round(Q * len(test)))
            routed = gut[test].copy()
            top = np.argsort(-unc[test], kind="stable")[:k]
            routed[top] = think[test][top]
            pol = dict(trust=gut[test], read=read, route=routed, think=think[test])
            pol["recipe"] = pol["read"] if choose_read else pol["route"]
            rows.append(dict(read=bool(choose_read),
                             auc={n: strata_auc(s, yt, stt) for n, s in pol.items()},
                             acc={n: float(((s > 0.5) == yt).mean()) for n, s in pol.items()}))
        cost = dict(trust=0, read=0, route=Q, think=1)
        fr = float(np.mean([r["read"] for r in rows]))
        res[b] = dict(picks_read=round(fr, 2),
                      auc={n: round(float(np.mean([r["auc"][n] for r in rows])), 3) for n in rows[0]["auc"]},
                      acc={n: round(float(np.mean([r["acc"][n] for r in rows])), 3) for n in rows[0]["acc"]},
                      think_share={**cost, "recipe": round(fr * 0 + (1 - fr) * Q, 2)})
        print(b, json.dumps(res[b]), flush=True)
    return res


if __name__ == "__main__":
    main()
