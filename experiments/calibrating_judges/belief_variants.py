#!/usr/bin/env python
"""Belief escalation: (1) different budgets, (2) flip instead of escalate, (3) different escalation targets. Saved records only, Qwen3.5-4B / 9B.
Belief trust score = out-of-fold logistic regression on [belief_k, |belief_k-0.5|, first solve matches, verdict follows belief, verdict] (5 folds by
question, 3 seeds); k = 1 (cheap) and 7. P(wrong) = 1 - score.
 BFF: our judges' verdicts; stronger judge = README's top-3 pool vote; confidence baseline = verdict-token probability (token_stats.py).
 RB2 Math: team's saved verdicts, clean labels; stronger judge = Qwen3.6-35B; confidence baseline = |log-odds at the verdict|.
(1) accuracy with 10/20/30/50% escalated: belief k=1, k=7, confidence, verdict-only rule, random.
(2) flip-only: flip every verdict with P(wrong) > 0.5, no stronger judge; escalate+flip: escalate 20% as in (1), flip the rest with P(wrong) > 0.5.
    Pre-registered: escalate+flip (k=1) beats escalate-only (k=1) at 20% with 95% paired bootstrap CI above 0 in >= 2 of the 4 judge x benchmark settings.
(3) same 20% (k=1), escalated to: the stronger judge / a human (gold label, the ceiling)."""
import json, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
AD = "../dynamic-llm-juries/experiments/anchoring_early_answer/out/"
R = pd.DataFrame(json.load(open(AD + "belief_rows_clean.json")))
for c in ["belief", "target_ok", "spoken", "m_C", "match0"]: R[c] = pd.to_numeric(R[c], errors="coerce")
K = pd.DataFrame([dict(zip(["judge", "item", "x", "s"], r["cache_key"].split("|")), v=r["verdict"]) for r in map(json.loads, open(AD + "matches_glm5.3-flash_k.jsonl"))])
K = K.sort_values("x").drop_duplicates(["judge", "item", "s"]); K["si"] = K.s.str[1:].astype(int); K["same"] = (K.v == "SAME").astype(float)
TG = json.load(open("targets/strong_judge_correct.json"))
def belief_k(j, items, k):
    d = K[(K.judge == j) & (K.si <= k)].groupby("item").same.mean(); return np.array([d.get(i, np.nan) for i in items])
def feats(b, v, m0):
    b = np.nan_to_num(b, nan=0.5); return np.c_[b, np.abs(b - 0.5), m0, ((v == 1) == (b >= 0.5)).astype(float), v]
def oof(X, y, g, seeds=3):
    S = np.zeros((seeds, len(y)))
    for s in range(seeds):
        ug = np.random.default_rng(s).permutation(np.unique(g)); fo = {q: i % 5 for i, q in enumerate(ug)}; f = np.array([fo[q] for q in g])
        for k in range(5):
            tr, te = f != k, f == k; sc = StandardScaler().fit(X[tr]); S[s, te] = LogisticRegression(max_iter=2000).fit(sc.transform(X[tr]), y[tr]).predict_proba(sc.transform(X[te]))[:, 1]
    return S
def escmask(trust, fin, tie, rate):
    n = len(trust); m = int(round(rate * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True; return e
def acc(ol, oh, esc, flip=None):
    out = np.where(esc, oh, ol); return (np.where(flip & ~esc, 1 - ol, out) if flip is not None else out).mean()
def boot(f, g, nb=1000):
    gi = {q: np.where(g == q)[0] for q in np.unique(g)}; ug = np.array(list(gi)); rb = np.random.default_rng(7)
    D = np.array([f(np.concatenate([gi[q] for q in rb.choice(ug, len(ug))])) for _ in range(nb)]) * 100; return np.percentile(D, 2.5), np.percentile(D, 97.5)
settings = []
for J, j in [("Qwen3.5-4B", "qwen3.5-4b"), ("Qwen3.5-9B", "qwen3.5-9b")]:
    L = pd.read_json(f"local_results/{J}__bff__uncertainty__n1_t0.0/{J}__bff__uncertainty__n1_t0.0_gen.jsonl", lines=True, dtype={"item_id": str}); it = L.item_id.values
    T = pd.read_csv(f"local_results/{J}__bff__uncertainty__n1_t0.0/{J}__bff__uncertainty__n1_t0.0_tokstats.csv", dtype={"item_id": str}).set_index("item_id").reindex(it)
    settings.append(dict(name=f"BFF {J}", j=j, items=it, ol=L.correct.values.astype(int), fin=L.verdict.notna().values, v=(L.verdict.values == 1.0).astype(float),
                         oh=np.array([TG[J]["bff"][i] for i in it]), g=np.array([i.split("-t")[0] for i in it]), conf=np.nan_to_num(T.verdict_prob.values, nan=0.0), strong="top-3 pool vote"))
S35 = R[(R.bench == "rb2math") & (R.judge == "qwen3.6-35b-a3b")].drop_duplicates("item").set_index("item")
for J, j in [("Qwen3.5-4B", "qwen3.5-4b"), ("Qwen3.5-9B", "qwen3.5-9b")]:
    d = R[(R.bench == "rb2math") & (R.judge == j)].drop_duplicates("item"); d = d[d.item.isin(S35.index) & d.spoken.notna()]; d = d[S35.loc[d.item, "spoken"].notna().values]
    y = d.target_ok.values.astype(int); v = d.spoken.values.astype(float)
    settings.append(dict(name=f"RB2 Math {J}", j=j, items=d.item.values, ol=(v == y).astype(int), fin=np.ones(len(y), bool), v=v, oh=(S35.loc[d.item, "spoken"].values.astype(float) == y).astype(int),
                         g=np.array([i.rsplit("-", 1)[0] for i in d.item.values]), conf=np.abs(d.m_C.values.astype(float)), strong="Qwen3.6-35B"))
r1, r2, r3, passes = [], [], [], 0
for st in settings:
    ol, oh, fin, v, g = st["ol"], st["oh"], st["fin"], st["v"], st["g"]; n = len(ol); tie = np.random.default_rng(12345).random(n); m0 = np.nan_to_num(belief_k(st["j"], st["items"], 1), nan=0.5)
    SC = {k: oof(feats(belief_k(st["j"], st["items"], k), v, m0), ol, g) for k in [1, 7]}
    row = dict(setting=st["name"], cheap_alone=ol.mean() * 100, stronger_alone=oh.mean() * 100)
    for rate in [0.1, 0.2, 0.3, 0.5]:
        for k in [1, 7]: row[f"belief{k}@{int(rate*100)}"] = np.mean([acc(ol, oh, escmask(SC[k][s], fin, tie, rate)) for s in range(3)]) * 100
        row[f"confidence@{int(rate*100)}"] = acc(ol, oh, escmask(st["conf"], fin, tie, rate)) * 100
        row[f"verdict_only@{int(rate*100)}"] = np.mean([acc(ol, oh, escmask(np.where(v == 1, 0, 1) + 0.5 * np.random.default_rng(s).random(n), fin, tie, rate)) for s in range(20)]) * 100
        row[f"random@{int(rate*100)}"] = (ol.mean() + rate * (oh.mean() - ol.mean())) * 100
    r1.append(row)
    pw = 1 - SC[1]; flip_only = np.mean([acc(ol, oh, np.zeros(n, bool), (pw[s] > 0.5) & fin) for s in range(3)]) * 100
    esc_only = lambda bi: np.mean([acc(ol[bi], oh[bi], escmask(SC[1][s][bi], fin[bi], tie[bi], 0.2)) for s in range(3)])
    esc_flip = lambda bi: np.mean([acc(ol[bi], oh[bi], escmask(SC[1][s][bi], fin[bi], tie[bi], 0.2), (pw[s][bi] > 0.5) & fin[bi]) for s in range(3)])
    al = np.arange(n); lo, hi = boot(lambda bi: esc_flip(bi) - esc_only(bi), g); passes += lo > 0
    r2.append(dict(setting=st["name"], cheap_alone=ol.mean() * 100, flip_only=flip_only, flipped_share=np.mean([(pw[s] > 0.5).mean() for s in range(3)]) * 100,
                   escalate_only_20=esc_only(al) * 100, escalate_plus_flip_20=esc_flip(al) * 100, gain=f"{(esc_flip(al) - esc_only(al))*100:+.1f} [{lo:+.1f},{hi:+.1f}]"))
    r3.append(dict(setting=st["name"], to_stronger_judge=esc_only(al) * 100, stronger=st["strong"],
                   to_human=np.mean([acc(ol, np.ones(n, int), escmask(SC[1][s], fin, tie, 0.2)) for s in range(3)]) * 100,
                   errors_in_escalated=np.mean([(1 - ol[escmask(SC[1][s], fin, tie, 0.2)]).mean() for s in range(3)]) * 100))
pd.set_option("display.width", 260)
B = pd.DataFrame(r1); print("== (1) accuracy by budget (escalate x% to the stronger judge)")
for rate in [10, 20, 30, 50]: print(f"-- {rate}% --"); print(B[["setting", f"random@{rate}", f"verdict_only@{rate}", f"confidence@{rate}", f"belief1@{rate}", f"belief7@{rate}"]].round(1).to_string(index=False))
print("\n== (2) flip instead of / as well as escalate (belief from 1 solve)"); print(pd.DataFrame(r2).round(1).to_string(index=False))
print(f"PRE-REGISTERED: escalate+flip beats escalate-only with CI above 0 in >= 2 of 4: {passes} -> {'PASS' if passes >= 2 else 'FAIL'}")
print("\n== (3) where the 20% go (belief from 1 solve)"); print(pd.DataFrame(r3).round(1).to_string(index=False))
