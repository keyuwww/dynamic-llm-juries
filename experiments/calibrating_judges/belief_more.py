#!/usr/bin/env python
"""Belief escalation: (1) fewer solves on BFF, (2) a second benchmark (RB2 Math) using the team's saved verdicts. Saved records only, no activations.
Belief_k = share of the judge's first k own solves (s1..sk) that reach the candidate's answer (GLM-5.3-Flash matches, NONE counts as not reaching).
Combiner = logistic regression on [belief_k, |belief_k - 0.5|, first solve matches, verdict follows belief_k, verdict], trained on half... (see below).
Splits: 5 folds by question, 3 seeds; combiner trained on the other folds; accuracy with 20% escalated, 95% paired bootstrap CIs over questions.
 Part 1 (BFF): our cheap judges' verdicts (our runs), stronger judge = README's (targets/strong_judge_correct.json). k = 1, 2, 3, 5, 7.
 Part 2 (RB2 Math, clean labels): cheap judge Qwen3.5-4B or 9B and stronger judge Qwen3.6-35B, all with the team's saved spoken verdicts;
   baselines: verdict confidence |m_C| (the judge's own log-odds at its verdict, single pass), verdict-only rule (accepted answers first), random.
   Pre-registered pass bar (Part 2): belief (k = 7) beats verdict confidence at 20% with CI above 0 for at least 1 of the 2 cheap judges."""
import json, sys, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
AD = "../dynamic-llm-juries/experiments/anchoring_early_answer/out/"
R = pd.DataFrame(json.load(open(AD + "belief_rows_clean.json")))
for c in ["belief", "target_ok", "spoken", "m_C", "match0"]: R[c] = pd.to_numeric(R[c], errors="coerce")
K = pd.DataFrame([dict(zip(["judge", "item", "x", "s"], r["cache_key"].split("|")), v=r["verdict"]) for r in map(json.loads, open(AD + "matches_glm5.3-flash_k.jsonl"))])
K = K.sort_values("x").drop_duplicates(["judge", "item", "s"]); K["si"] = K.s.str[1:].astype(int); K["same"] = (K.v == "SAME").astype(float)
def belief_k(j, items, k):
    d = K[(K.judge == j) & (K.si <= k)].groupby("item").same.mean(); return np.array([d.get(i, np.nan) for i in items])
def feats(b, v, m0):
    b = np.nan_to_num(b, nan=0.5); return np.c_[b, np.abs(b - 0.5), m0, ((v == 1) == (b >= 0.5)).astype(float), v]
def esc(trust, ol, oh, fin, tie, rate=0.2):
    n = len(ol); m = int(round(rate * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True; return np.where(e, oh, ol).mean()
def oof_scores(X, y, g, seeds=3):
    S = np.zeros((seeds, len(y)))
    for s in range(seeds):
        ug = np.random.default_rng(s).permutation(np.unique(g)); fo = {q: i % 5 for i, q in enumerate(ug)}; f = np.array([fo[q] for q in g])
        for k in range(5):
            tr, te = f != k, f == k; sc = StandardScaler().fit(X[tr]); S[s, te] = LogisticRegression(max_iter=2000).fit(sc.transform(X[tr]), y[tr]).predict_proba(sc.transform(X[te]))[:, 1]
    return S
def boot(fa, fb, g, nb=1000):
    gi = {q: np.where(g == q)[0] for q in np.unique(g)}; ug = np.array(list(gi)); rb = np.random.default_rng(7); D = []
    for _ in range(nb):
        bi = np.concatenate([gi[q] for q in rb.choice(ug, len(ug))]); D.append(fa(bi) - fb(bi))
    D = np.array(D) * 100; return np.percentile(D, 2.5), np.percentile(D, 97.5)

print("== Part 1: BFF, fewer solves (escalate 20% to the README's stronger judge)")
TG = json.load(open("targets/strong_judge_correct.json"))
for J, j in [("Qwen3.5-4B", "qwen3.5-4b"), ("Qwen3.5-9B", "qwen3.5-9b")]:
    gfile = f"local_results/{J}__bff__uncertainty__n1_t0.0/{J}__bff__uncertainty__n1_t0.0_gen.jsonl"; L = pd.read_json(gfile, lines=True, dtype={"item_id": str})
    items = L.item_id.values; ol = L.correct.values.astype(int); fin = L.verdict.notna().values; v = (L.verdict.values == 1.0).astype(float); oh = np.array([TG[J]["bff"][i] for i in items])
    g = np.array([i.split("-t")[0] for i in items]); tie = np.random.default_rng(12345).random(len(ol)); m0 = np.nan_to_num(belief_k(j, items, 1), nan=0.5); out = {}
    for k in [1, 2, 3, 5, 7]:
        S = oof_scores(feats(belief_k(j, items, k), v, m0), ol, g); out[k] = np.mean([esc(S[s], ol, oh, fin, tie) for s in range(3)]) * 100
    vo = np.mean([esc(np.where(v == 1, 0, 1) + 0.5 * np.random.default_rng(s).random(len(ol)), ol, oh, fin, tie) for s in range(20)]) * 100
    print(f"{J}: random {(ol.mean() + 0.2 * (oh.mean() - ol.mean())) * 100:.1f} | verdict-only {vo:.1f} | belief from k solves: " + "  ".join(f"k={k}: {a:.1f}" for k, a in out.items()))

print("\n== Part 2: RB2 Math (clean labels), stronger judge = Qwen3.6-35B, team's saved verdicts")
S35 = R[(R.bench == "rb2math") & (R.judge == "qwen3.6-35b-a3b")].drop_duplicates("item").set_index("item")
passes = 0
for j in ["qwen3.5-4b", "qwen3.5-9b"]:
    d = R[(R.bench == "rb2math") & (R.judge == j)].drop_duplicates("item"); d = d[d.item.isin(S35.index) & d.spoken.notna() & S35.loc[d.item.where(d.item.isin(S35.index), d.item.iloc[0]), "spoken"].notna().values]
    items = d.item.values; y = d.target_ok.values.astype(int); v = d.spoken.values.astype(float); ol = (v == y).astype(int); oh = (S35.loc[items, "spoken"].values.astype(float) == y).astype(int)
    fin = np.ones(len(ol), bool); g = np.array([i.rsplit("-", 1)[0] for i in items]); tie = np.random.default_rng(12345).random(len(ol)); m0 = d.match0.values.astype(float)
    S = oof_scores(feats(belief_k(j, items, 7), v, m0), ol, g); conf = np.abs(d.m_C.values.astype(float))
    fb = lambda bi: np.mean([esc(S[s][bi], ol[bi], oh[bi], fin[bi], tie[bi]) for s in range(3)]); fc = lambda bi: esc(conf[bi], ol[bi], oh[bi], fin[bi], tie[bi])
    fv = lambda bi: np.mean([esc((np.where(v == 1, 0, 1) + 0.5 * np.random.default_rng(s).random(len(ol)))[bi], ol[bi], oh[bi], fin[bi], tie[bi]) for s in range(20)])
    al = np.arange(len(ol)); lo, hi = boot(fb, fc, g); passes += lo > 0
    print(f"{j}: n={len(ol)} | cheap alone {ol.mean()*100:.1f} | 35B alone {oh.mean()*100:.1f} | random {(ol.mean() + 0.2 * (oh.mean() - ol.mean()))*100:.1f} | verdict-only {fv(al)*100:.1f} | "
          f"verdict confidence {fc(al)*100:.1f} | belief {fb(al)*100:.1f} | belief - confidence {(fb(al) - fc(al))*100:+.1f} [{lo:+.1f},{hi:+.1f}]")
print(f"\nPRE-REGISTERED (Part 2): belief beats verdict confidence with CI above 0 for >= 1 of 2 cheap judges: {passes} -> {'PASS' if passes >= 1 else 'FAIL'}")
