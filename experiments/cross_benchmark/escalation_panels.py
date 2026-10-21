"""How well do panels of judges detect the primary judge's errors? (stored verdicts, no new calls)

The primary judge is the best on the training folds. A panel of m extra judges (m = 1..7) checks it, and the item is
escalated when the panel disagrees with the primary under one of three rules:
  any       at least one panel judge disagrees
  two       at least two panel judges disagree (m >= 2)
  majority  more than half of the panel disagrees
Panels are picked on training folds in two ways:
  accuracy       the m most accurate other judges
  complementary  greedy: add the judge that most improves F1 of the "any" trigger at catching the primary's
                 training errors (so it favours judges that disagree exactly where the primary is wrong)
A last sweep uses the full pool: escalate when at least t of the 7 other judges disagree (t = 1..7).

Everything is cross-validated (5 x 5-fold grouped by conversation / prompt). Metrics on held-out items:
escalation rate, precision (escalated items where the primary was wrong), recall (share of the primary's errors
escalated), and the ceiling (accuracy if every escalated item were then judged correctly). Judges called = 1 + m.

Usage: uv run python experiments/cross_benchmark/escalation_panels.py <folder with data/ and results/>
"""
import sys

import numpy as np
import pandas as pd

base = sys.argv[1]
T = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
     "nemotron3-super-120b", "nemotron3-nano-30b"]
BENCHES = ["bff", "mtb", "bffpair", "safety", "bbeh", "judgebench", "rb2", "alpacafarm", "mtbhuman"]


def f1(esc, err):
    tp = (esc & err).sum()
    return 2 * tp / max(esc.sum() + err.sum(), 1)


def trigger(dis, rule):
    """dis: items x panel bool matrix of 'panel judge disagrees with the primary'."""
    k = dis.sum(1)
    if rule == "any":
        return k >= 1
    if rule == "two":
        return k >= 2
    return k > dis.shape[1] / 2


rows = []
for b in BENCHES:
    d = pd.read_pickle(f"{base}/data/{b}_decisions.pkl")
    d = d[(d.condition == "none") & d.judge.isin(T)]
    A = d.pivot_table(index="key", columns="judge", values="agree").dropna()
    V = d.pivot_table(index="key", columns="judge", values="verdict").loc[A.index].astype(int)
    g = d.drop_duplicates("key").set_index("key").loc[A.index].group.astype(str).values
    Am, Vm = A.values.astype(int), V.values
    J = Am.shape[1]
    ug = np.unique(g)
    acc_store = {}
    for rep in range(5):
        rng = np.random.default_rng(rep)
        fo = dict(zip(rng.permutation(ug), np.arange(len(ug)) % 5))
        f = np.array([fo[x] for x in g])
        esc = {}
        err = np.zeros(len(A), bool)
        for k in range(5):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            acc = Am[tr].mean(0)
            p = int(np.argmax(acc))
            others = [j for j in range(J) if j != p]
            e_tr = Am[tr, p] == 0
            err[te] = Am[te, p] == 0
            dis_tr = Vm[tr][:, others] != Vm[tr, p][:, None]
            dis_te = Vm[te][:, others] != Vm[te, p][:, None]
            # panels by accuracy and by greedy complementarity
            by_acc = sorted(range(len(others)), key=lambda i: -acc[others[i]])
            greedy, left = [], list(range(len(others)))
            while left:
                best = max(left, key=lambda i: f1(dis_tr[:, greedy + [i]].any(1), e_tr))
                greedy.append(best)
                left.remove(best)
            for m in range(1, len(others) + 1):
                for sel, order in [("accuracy", by_acc), ("complementary", greedy)]:
                    cols = order[:m]
                    for rule in ["any", "two", "majority"]:
                        if rule == "two" and m < 2:
                            continue
                        key = (sel, m, rule)
                        esc.setdefault(key, np.zeros(len(A), bool))[te] = trigger(dis_te[:, cols], rule)
            for t in range(1, len(others) + 1):
                esc.setdefault(("pool_threshold", t, f">= {t} of 7"), np.zeros(len(A), bool))[te] = dis_te.sum(1) >= t
        for key, E in esc.items():
            acc_store.setdefault(key, []).append([E.mean(), (E & err).sum() / max(E.sum(), 1),
                                                  (E & err).sum() / max(err.sum(), 1), 1 - (err & ~E).sum() / len(E),
                                                  1 - err.mean()])
    for (sel, m, rule), v in acc_store.items():
        mu = np.mean(v, 0)
        rows.append(dict(bench=b, selection=sel, extra_judges=m if sel != "pool_threshold" else 7, rule=rule,
                         threshold=m if sel == "pool_threshold" else None, escalated=mu[0], precision=mu[1],
                         recall=mu[2], ceiling=mu[3], primary=mu[4]))

t = pd.DataFrame(rows)
t.to_csv(f"{base}/results/escalation_panels.csv", index=False)
pd.set_option("display.width", 220)
avg = t.groupby(["selection", "extra_judges", "rule", "threshold"], dropna=False)[["escalated", "precision", "recall", "ceiling"]].mean()
avg["gain"] = t.groupby(["selection", "extra_judges", "rule", "threshold"], dropna=False).apply(lambda x: (x.ceiling - x.primary).mean())
print(avg.round(3).to_string())
