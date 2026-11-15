#!/usr/bin/env python3
"""
Step 10 of Trust / Read / Think: a jury of judges from different families, each with three reads.

Judges (default): Qwen3.5-4B, gpt-oss-20b, Nemotron Nano 9B v2. For every judge and item we have the gut P(CORRECT),
the hidden state (probe, 100 labelled items per benchmark, Platt-calibrated, as in Step 7) and the thinking verdict at
1,024 tokens. Per draw, the same 100 labelled items are used for every judge; everything else is the test set.

Juries, compared at the same thinking cost (share of judge-item calls that think):
  gut majority             majority of the judges' gut verdicts                                  cost 0
  free majority            each judge's free verdict (more confident of gut / probe), majority    cost 0
  gut->think jury          each judge: gut, thinks on its 20% least confident items; majority    cost 20%
  cascade jury             each judge: cascade v2 at 20%; majority                               cost 20%
  dynamic jury             free verdicts first; the 20% of items where the jury is least sure
                           (smallest summed log-odds margin) get every judge thinking; majority  cost 20%
  think majority           every judge thinks on every item; majority                            cost 100%
  agreement jury (Isaac)   every judge thinks; only judges whose gut and thinking agree vote
                           (none agree: majority of thinking verdicts)                           cost 100%
  best single judge        the judge with the best cascade accuracy on the labelled items          cost 20%
Accuracy on test items; 95% CIs from paired bootstrap over questions (per-item correctness averaged over draws).

  .venv/bin/python experiments/trust_read_think/step10_jury.py [--judges a,b,c]
"""
import argparse
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
from step2 import probe, strata_auc
from step6 import draw_labels

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "results" / "raw" / "step1"
BENCHES = ("safety", "focus", "math", "bff", "factuality")
N_LAB, DRAWS, Q, TB, B_BOOT = 100, 10, 0.2, 1024, 2000
DEPTHS = (0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)     # candidate probe layers, as a share of depth
conf = lambda p: np.abs(2 * p - 1)
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))


def load(judges):
    items = [json.loads(l) for f in ("items.jsonl", "items_factuality.jsonl") for l in open(ITEMS / f)]
    D = {}
    for b in BENCHES:
        sub = [it for it in items if it["bench"] == b]
        d = dict(y=np.array([it["gold"] for it in sub]), g=np.array([it["group"] for it in sub]), J={})
        for j in judges:
            raw = ITEMS / j
            th = {json.loads(l)["id"]: json.loads(l) for l in open(raw / f"{b}_think.jsonl")}
            f = np.load(raw / f"{b}_fast.npz")
            assert len(f["p"]) == len(sub), (j, b)
            d["J"][j] = dict(hs=f["hs"].astype(np.float32), gut=f["p"],
                             think=np.array([th[it["id"]]["p_budget"][str(TB)] for it in sub]))
        D[b] = d
    return D


def pick_layer(hs, y, g):
    nL = hs.shape[1] - 1
    cands = sorted({max(1, int(round(f * nL))) for f in DEPTHS})
    if len(y) < 50:
        return cands[len(cands) // 2]
    best, bs = cands[len(cands) // 2], -1
    folds = list(GroupKFold(3).split(hs[:, 0], y, g))
    for L in cands:
        s = np.zeros(len(y))
        for a, c in folds:
            mu1, mu0 = hs[a][y[a] == 1, L].mean(0), hs[a][y[a] == 0, L].mean(0)
            s[c] = (hs[c, L] - (mu1 + mu0) / 2) @ (mu1 - mu0)
        sc = roc_auc_score(y, s)
        if sc > bs:
            best, bs = L, sc
    return best


def probe_scores(hs, y, g, lab, te):
    L = pick_layer(hs[lab], y[lab], g[lab])
    oof = np.zeros(len(lab))
    for a, c in GroupKFold(5).split(lab, y[lab], g[lab]):
        oof[c] = probe().fit(hs[lab[a], L], y[lab[a]]).decision_function(hs[lab[c], L])
    platt = LogisticRegression(C=1e4).fit(oof[:, None], y[lab])
    pr_lab = platt.predict_proba(oof[:, None])[:, 1]
    pr = platt.predict_proba(probe().fit(hs[lab, L], y[lab]).decision_function(hs[te, L])[:, None])[:, 1]
    return pr, pr_lab


def majority(V):
    """V: (judges, items) 0/1 votes -> majority (ties -> 0, i.e. reject, as in Isaac's juries)."""
    return (V.sum(0) * 2 > V.shape[0]).astype(int)


def one_draw(d, judges, seed):
    y, g = d["y"], d["g"]
    lab = draw_labels(g, np.random.default_rng(seed), N_LAB)
    te = np.setdiff1d(np.arange(len(y)), lab)
    n, k = len(te), int(round(Q * len(te)))
    G, T, FREE, CASC, GT, LAB_ACC = [], [], [], [], [], []
    for j in judges:
        J = d["J"][j]
        pr, pr_lab = probe_scores(J["hs"], y, g, lab, te)
        # calibrate the gut on the same labelled items (cascade v3), so gut and probe confidences are comparable
        cal = LogisticRegression(C=1e4).fit(logit(J["gut"][lab])[:, None], y[lab])
        gt = cal.predict_proba(logit(J["gut"][te])[:, None])[:, 1]
        gl_cal = cal.predict_proba(logit(J["gut"][lab])[:, None])[:, 1]
        tt = J["think"][te]
        free = np.where(conf(gt) >= conf(pr), gt, pr)
        mc = np.maximum(conf(gt), conf(pr))
        casc = free.copy()
        o = np.argsort(mc, kind="stable")[:k]
        casc[o] = tt[o]
        gthink = gt.copy()
        o2 = np.argsort(conf(gt), kind="stable")[:k]
        gthink[o2] = tt[o2]
        # labelled-item accuracy of this judge's free verdict (used to pick the "best single judge" without test labels)
        free_lab = np.where(conf(gl_cal) >= conf(pr_lab), gl_cal, pr_lab)
        LAB_ACC.append(float(((free_lab > 0.5) == y[lab]).mean()))
        G.append(gt); T.append(tt); FREE.append(free); CASC.append(casc); GT.append(gthink)
    G, T, FREE, CASC, GT = map(np.array, (G, T, FREE, CASC, GT))
    v = lambda P: (P > 0.5).astype(int)
    # dynamic jury: least sure items by summed log-odds of the free verdicts -> every judge thinks there
    margin = np.abs(logit(FREE).sum(0))
    dyn = FREE.copy()
    o = np.argsort(margin, kind="stable")[:k]
    dyn[:, o] = T[:, o]
    # agreement jury (Isaac): judges whose gut and thinking verdicts agree vote with their thinking verdict
    agree = v(G) == v(T)
    ag = np.where(agree.any(0), (np.where(agree, v(T), 0).sum(0) * 2 > agree.sum(0)).astype(int), majority(v(T)))
    best = int(np.argmax(LAB_ACC))
    out = {"gut majority": majority(v(G)), "free majority": majority(v(FREE)), "gut->think jury": majority(v(GT)),
           "cascade jury": majority(v(CASC)), "dynamic jury": majority(v(dyn)), "think majority": majority(v(T)),
           "agreement jury (Isaac)": ag, "best single judge (cascade)": v(CASC[best])}
    for i, j in enumerate(judges):
        out[f"{j} cascade"] = v(CASC[i])
    return te, {name: (pred == y[te]).astype(float) for name, pred in out.items()}


COST = {"gut majority": 0, "free majority": 0, "gut->think jury": Q, "cascade jury": Q, "dynamic jury": Q,
        "think majority": 1, "agreement jury (Isaac)": 1, "best single judge (cascade)": Q}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="qwen3.5-4b,gpt-oss-20b,nvidia-nemotron-nano-9b-v2")
    a = ap.parse_args()
    judges = a.judges.split(",")
    D = load(judges)
    C = {}
    for b in BENCHES:
        n = len(D[b]["y"])
        tot, cnt = {}, np.zeros(n)
        for seed in range(DRAWS):
            te, corr = one_draw(D[b], judges, seed)
            for name, c in corr.items():
                tot.setdefault(name, np.zeros(n))[te] += c
            cnt[te] += 1
        C[b] = {name: t / np.where(cnt == 0, np.nan, cnt) for name, t in tot.items()}
    names = list(C[BENCHES[0]])
    rng = np.random.default_rng(0)
    boots = {}
    for b in BENCHES:
        g = D[b]["g"]
        ug = np.unique(g)
        idx = {q: np.where(g == q)[0] for q in ug}
        boots[b] = []
        for _ in range(B_BOOT):
            ii = np.concatenate([idx[q] for q in rng.choice(ug, len(ug))])
            boots[b].append({nm: np.nanmean(C[b][nm][ii]) for nm in names})
    ci = lambda x: [round(float(np.percentile(x, 2.5)), 3), round(float(np.percentile(x, 97.5)), 3)]
    res = dict(judges=judges, think_share=Q, cost=COST, benches={})
    for b in list(BENCHES) + ["all"]:
        if b == "all":
            get = lambda nm: np.mean([[x[nm] for x in boots[bb]] for bb in BENCHES], 0)
            acc = {nm: round(float(np.mean([np.nanmean(C[bb][nm]) for bb in BENCHES])), 3) for nm in names}
        else:
            get = lambda nm, b=b: np.array([x[nm] for x in boots[b]])
            acc = {nm: round(float(np.nanmean(C[b][nm])), 3) for nm in names}
        res["benches"][b] = dict(acc=acc, dynamic_minus={nm: dict(d=round(acc["dynamic jury"] - acc[nm], 3),
                                                                   ci=ci(get("dynamic jury") - get(nm)))
                                                          for nm in names if nm != "dynamic jury"},
                                 cascade_minus={nm: dict(d=round(acc["cascade jury"] - acc[nm], 3),
                                                         ci=ci(get("cascade jury") - get(nm)))
                                                for nm in names if nm != "cascade jury"})
        print(f"== {b}: " + "  ".join(f"{nm} {v}" for nm, v in acc.items()), flush=True)
    print("dynamic jury minus (all):", json.dumps(res["benches"]["all"]["dynamic_minus"]))
    print("cascade jury minus (all):", json.dumps(res["benches"]["all"]["cascade_minus"]))
    out = HERE / "results" / "jury"
    out.mkdir(exist_ok=True)
    (out / "step10_jury.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
