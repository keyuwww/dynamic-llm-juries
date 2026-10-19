"""Escalation triggers simulated from stored verdicts (no new calls). Cross-validated: every choice is made on
Usage: uv run python experiments/cross_benchmark/escalation_sim.py <folder with data/ and results/>
training folds (5 x 5-fold grouped by conversation / prompt) and scored on held-out items.

Primary judge = best on training folds. Escalate when:
  top2     the second-best judge (by training accuracy) disagrees
  diverse  the judge that would have caught the most of the primary's training errors per escalation disagrees
           (best precision * recall on training folds), i.e. a complementary second judge
  any2     either of the two complementary judges disagrees (3 judges called)
  pool     the majority of the other 7 judges disagrees with the primary (8 judges called)
  hardcat  the item's category has a training error rate for the primary above its overall rate (no extra judge)
  diverse+hardcat  either of the above
Metrics: escalation rate, precision (escalated items the primary got wrong), recall (primary's errors caught),
accuracy on items not escalated, and the ceiling if every escalated item were then judged correctly."""
import sys
import numpy as np
import pandas as pd

base = sys.argv[1]
T = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
     "nemotron3-super-120b", "nemotron3-nano-30b"]
RULES = ["top2", "diverse", "any2", "pool", "hardcat", "diverse+hardcat"]
out = []
for b in ["bff", "mtb", "bffpair", "safety", "bbeh", "judgebench", "rb2", "alpacafarm", "mtbhuman"]:
    d = pd.read_pickle(f"{base}/data/{b}_decisions.pkl")
    d = d[(d.condition == "none") & d.judge.isin(T)]
    A = d.pivot_table(index="key", columns="judge", values="agree").dropna()
    V = d.pivot_table(index="key", columns="judge", values="verdict").loc[A.index].astype(int)
    info = d.drop_duplicates("key").set_index("key").loc[A.index]
    g, cat = info.group.astype(str).values, info.category.astype(str).values
    Am, Vm, J = A.values.astype(int), V.values, list(A.columns)
    ug = np.unique(g)
    res = {r: [] for r in RULES}
    for rep in range(5):
        rng = np.random.default_rng(rep)
        fo = dict(zip(rng.permutation(ug), np.arange(len(ug)) % 5))
        f = np.array([fo[x] for x in g])
        esc = {r: np.zeros(len(A), bool) for r in RULES}
        err = np.zeros(len(A), bool)
        for k in range(5):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            acc = Am[tr].mean(0)
            p = int(np.argmax(acc))
            others = [j for j in range(len(J)) if j != p]
            sec = max(others, key=lambda j: acc[j])
            e_tr = Am[tr, p] == 0

            def score(j):  # F1 of "j disagrees" as a detector of the primary's training errors
                dis = Vm[tr, j] != Vm[tr, p]
                tp = (dis & e_tr).sum()
                return 2 * tp / max(dis.sum() + e_tr.sum(), 1)
            ranked = sorted(others, key=score, reverse=True)
            div, div2 = ranked[0], ranked[1]
            rate = {c: (Am[tr][cat[tr] == c, p] == 0).mean() for c in np.unique(cat[tr])}
            hard = {c for c, r in rate.items() if r > e_tr.mean() and (cat[tr] == c).sum() >= 15}
            pv = Vm[te, p]
            err[te] = Am[te, p] == 0
            esc["top2"][te] = Vm[te, sec] != pv
            esc["diverse"][te] = Vm[te, div] != pv
            esc["any2"][te] = (Vm[te, div] != pv) | (Vm[te, div2] != pv)
            esc["pool"][te] = (Vm[te][:, others].mean(1) > 0.5).astype(int) != pv
            esc["hardcat"][te] = np.isin(cat[te], list(hard))
            esc["diverse+hardcat"][te] = esc["diverse"][te] | esc["hardcat"][te]
        for r in RULES:
            E = esc[r]
            res[r].append([E.mean(), (E & err).sum() / max(E.sum(), 1), (E & err).sum() / max(err.sum(), 1),
                           1 - (err & ~E).sum() / max((~E).sum(), 1), 1 - (err & ~E).sum() / len(E), 1 - err.mean()])
    for r in RULES:
        m = np.mean(res[r], 0)
        out.append(dict(bench=b, rule=r, escalated=m[0], precision=m[1], caught=m[2], acc_kept=m[3], ceiling=m[4], primary=m[5]))
t = pd.DataFrame(out)
t.to_csv(f"{base}/results/escalation_sim.csv", index=False)
pd.set_option("display.width", 200)
for col in ["escalated", "caught", "acc_kept", "ceiling"]:
    print(f"\n== {col}")
    print(t.pivot(index="bench", columns="rule", values=col)[RULES].round(3).to_string())
print("\nprimary (CV best) acc:", t.drop_duplicates("bench").set_index("bench").primary.round(3).to_dict())
