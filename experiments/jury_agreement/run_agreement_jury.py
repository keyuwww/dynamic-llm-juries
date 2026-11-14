"""Agreement-aware vs family-aware jury on BBEH (tinker pool, condition=none).

Question: when aggregating 8 judges' verdicts, does it help more to condition each vote on the
judge's model FAMILY relative to the examinee (proposal method B: family recusal) or on whether
the judge's OWN Phase-1 answer AGREES with the candidate's answer?

Inputs (already on disk, no API calls):
  experiments/tinker_pool/bbeh_results/answers.jsonl    each model's own answer per item
  experiments/tinker_pool/bbeh_results/judgments.jsonl  each judge's verdict per (item, examinee)

Run:  python3 experiments/jury_agreement/run_agreement_jury.py
"""
import collections
import json
import os
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "experiments", "tinker_pool"))
from data import _extract_answer  # noqa: E402

A = os.path.join(ROOT, "experiments/tinker_pool/bbeh_results/answers.jsonl")
J = os.path.join(ROOT, "experiments/tinker_pool/bbeh_results/judgments.jsonl")
COMMITTED_ONLY = "--committed-only" in sys.argv  # drop candidates whose own answer was truncated
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "results_committed_only.md" if COMMITTED_ONLY else "results.md")
N_REPEATS, N_FOLDS = 50, 5


def family(m):
    for f in ("qwen", "gpt-oss", "nemotron", "deepseek"):
        if m.startswith(f):
            return f
    raise ValueError(m)


def norm(ans):
    """Committed final answer, or None when the model never wrote one (truncated)."""
    if not ans or ("The answer is" not in ans and "final answer is" not in ans):
        return None
    p = _extract_answer(ans.strip()).lower().replace(", ", ",").replace("**", "")
    p = p.split("\n")[0].strip()
    p = p[:-1] if p.endswith(".") else p
    if len(p) == 3 and p[0] == "(" and p[-1] == ")":
        p = p[1]
    return p or None


# ---- load -------------------------------------------------------------------------------------
own, solved = {}, {}
for line in open(A):
    r = json.loads(line)
    own[(r["model"], r["item"])] = norm(r["answer"])
    solved[(r["model"], r["item"])] = int(r["correct"])
judges = sorted({m for m, _ in own})
solve_acc = {m: np.mean([v for (mm, _), v in solved.items() if mm == m]) for m in judges}

cases = collections.defaultdict(dict)  # (item, examinee) -> {judge: verdict}
gold = {}
for line in open(J):
    r = json.loads(line)
    if r["condition"] != "none":
        continue
    item = r["item_id"].split("|")[0]
    votes = [x or 0 for x in (r["votes"] or [])]  # unparsed -> INCORRECT, as in judges_summary.md
    cases[(item, r["examinee"])][r["judge"]] = 1 if votes and sum(votes) / len(votes) > 0.5 else 0
    gold[(item, r["examinee"])] = int(r["gold"])
keys = sorted(k for k in cases if len(cases[k]) == len(judges))
if COMMITTED_ONLY:
    keys = [k for k in keys if own.get((k[1], k[0])) is not None]
items = np.array([k[0] for k in keys])
y = np.array([gold[k] for k in keys])

V = np.array([[cases[k][j] for j in judges] for k in keys])                       # verdict 0/1
SF = np.array([[family(j) == family(k[1]) for j in judges] for k in keys])        # same family
SELF = np.array([[j == k[1] for j in judges] for k in keys])
cand = [own.get((k[1], k[0])) for k in keys]
MATCH = np.array([[own[(j, k[0])] is not None and cand[i] is not None and own[(j, k[0])] == cand[i]
                   for j in judges] for i, k in enumerate(keys)])
NOANS = np.array([[own[(j, k[0])] is None for j in judges] for k in keys])
DIFF = ~MATCH & ~NOANS


# ---- metrics ----------------------------------------------------------------------------------
def kappa(y, p):
    po = np.mean(y == p)
    pe = y.mean() * p.mean() + (1 - y.mean()) * (1 - p.mean())
    return (po - pe) / (1 - pe) if pe < 1 else 0.0


def masked_majority(mask):
    """Majority over jurors where mask is True; ties and empty juries -> INCORRECT."""
    n = mask.sum(1)
    yes = (V * mask).sum(1)
    return ((n > 0) & (yes > n / 2)).astype(int), n


# ---- unsupervised juries ----------------------------------------------------------------------
best = judges[int(np.argmax([kappa(y, V[:, i]) for i in range(len(judges))]))]
def at_least(k):
    return (MATCH.sum(1) >= k).astype(int), np.ones(len(y)) * len(judges)


unsup = {
    f"Best single judge ({best}, picked in hindsight)": (V[:, judges.index(best)], np.ones(len(y))),
    "Majority, all 8": masked_majority(np.ones_like(V, bool)),
    "Majority, self-recusal": masked_majority(~SELF),
    "Majority, family recusal (proposal method B)": masked_majority(~SF),
    "Majority, agreement recusal (drop jurors whose own answer matches)": masked_majority(~MATCH),
    "Majority, keep only jurors with a committed differing answer": masked_majority(DIFF),
    "No verdicts: CORRECT if >= 1 juror's own answer matches": at_least(1),
    "No verdicts: CORRECT if >= 2 jurors' own answers match": at_least(2),
    "No verdicts: CORRECT if >= 3 jurors' own answers match": at_least(3),
}

# ---- supervised (label-light) juries: logistic regression, item-grouped CV -------------------
pm = 2 * V - 1  # vote as +1 / -1


def feats(name):
    if name == "verdicts":
        return pm
    if name == "verdicts x family":
        return np.hstack([pm * SF, pm * ~SF])
    if name == "verdicts x agreement":
        return np.hstack([pm * MATCH, pm * DIFF, pm * NOANS])
    if name == "verdicts x family x agreement":
        return np.hstack([pm * (SF & s) for s in (MATCH, DIFF, NOANS)] + [pm * (~SF & s) for s in (MATCH, DIFF, NOANS)])
    if name == "agreement only (no verdicts)":
        return np.hstack([MATCH.astype(float), DIFF.astype(float)])
    if name == "verdicts x agreement + agreement":
        return np.hstack([pm * MATCH, pm * DIFF, pm * NOANS, MATCH.astype(float), DIFF.astype(float)])
    raise KeyError(name)


SUP = ["verdicts", "verdicts x family", "verdicts x agreement", "verdicts x family x agreement",
       "agreement only (no verdicts)", "verdicts x agreement + agreement"]
uniq = np.unique(items)
res = {n: {"acc": [], "kappa": []} for n in SUP}
oof_store = {n: [] for n in SUP}
for rep in range(N_REPEATS):
    rng = np.random.default_rng(rep)
    fold_of = dict(zip(rng.permutation(uniq), np.arange(len(uniq)) % N_FOLDS))
    folds = np.array([fold_of[i] for i in items])
    for n in SUP:
        X = feats(n)
        oof = np.zeros(len(y), int)
        for f in range(N_FOLDS):
            tr, te = folds != f, folds == f
            clf = LogisticRegression(C=1.0, max_iter=2000).fit(X[tr], y[tr])
            oof[te] = clf.predict(X[te])
        res[n]["acc"].append(np.mean(oof == y))
        res[n]["kappa"].append(kappa(y, oof))
        oof_store[n].append(oof)


def paired(a, b):
    """Share of repeats where a beats b on kappa, and mean difference."""
    d = np.array(res[a]["kappa"]) - np.array(res[b]["kappa"])
    return d.mean(), np.mean(d > 0)


def boot_ci(a, b, n_boot=2000):
    """Item-cluster bootstrap CI of kappa(a) - kappa(b), using repeat-0 out-of-fold predictions."""
    pa, pb = oof_store[a][0], oof_store[b][0]
    idx_by_item = collections.defaultdict(list)
    for i, it in enumerate(items):
        idx_by_item[it].append(i)
    groups = list(idx_by_item.values())
    rng = np.random.default_rng(123)
    ds = []
    for _ in range(n_boot):
        pick = np.concatenate([groups[g] for g in rng.integers(0, len(groups), len(groups))])
        ds.append(kappa(y[pick], pa[pick]) - kappa(y[pick], pb[pick]))
    return np.percentile(ds, [2.5, 97.5])


# ---- slice: examinee stronger vs weaker than the jury's average judge ------------------------
ex_acc = np.array([solve_acc[k[1]] for k in keys])
pool_mean = np.mean(list(solve_acc.values()))
strong = ex_acc > pool_mean

# ---- write ------------------------------------------------------------------------------------
L = []
L.append("# Agreement-aware vs family-aware jury (BBEH, condition = none)"
         + (" -- committed candidates only\n" if COMMITTED_ONLY else "\n"))
L.append(f"Cases: {len(y)} (item, examinee) pairs, each judged by all {len(judges)} pool models. "
         f"Gold CORRECT share: {y.mean():.2f}. Unparsed verdicts count as INCORRECT.\n")
L.append("A juror's own answer comes from its separate Phase-1 solve call; the judging prompt never shows it. "
         "'Matches' = juror's committed answer equals the candidate's; 'differs' = committed a different answer; "
         "'no answer' = juror's solve attempt was truncated.\n")
L.append("## Unsupervised juries (no labels)\n")
L.append("| Jury | Accuracy | κ | Mean jurors |")
L.append("|---|---|---|---|")
for n, (p, sz) in unsup.items():
    L.append(f"| {n} | {np.mean(p == y):.3f} | {kappa(y, p):.3f} | {np.mean(sz):.1f} |")
L.append("\n## Label-light juries (logistic regression on votes, 5-fold CV grouped by item, "
         f"{N_REPEATS} repeats)\n")
L.append("Each model sees the same 8 verdicts; they differ only in what each vote is allowed to depend on.\n")
L.append("| Features | Accuracy (mean ± sd) | κ (mean ± sd) |")
L.append("|---|---|---|")
for n in SUP:
    L.append(f"| {n} | {np.mean(res[n]['acc']):.3f} ± {np.std(res[n]['acc']):.3f} | "
             f"{np.mean(res[n]['kappa']):.3f} ± {np.std(res[n]['kappa']):.3f} |")
L.append("\n## Head-to-head (κ)\n")
L.append("| Comparison | Mean Δκ | Repeats where first wins | 95% item-bootstrap CI (repeat 0) |")
L.append("|---|---|---|---|")
for a, b in [("verdicts x agreement", "verdicts x family"),
             ("verdicts x agreement", "verdicts"),
             ("verdicts x family", "verdicts"),
             ("verdicts x family x agreement", "verdicts x agreement"),
             ("verdicts x agreement + agreement", "verdicts x agreement"),
             ("verdicts x agreement + agreement", "agreement only (no verdicts)")]:
    m, w = paired(a, b)
    lo, hi = boot_ci(a, b)
    L.append(f"| {a} vs {b} | {m:+.3f} | {w:.0%} | [{lo:+.3f}, {hi:+.3f}] |")
L.append("\n## By examinee strength (repeat-0 out-of-fold predictions; unsupervised rows exact)\n")
L.append(f"Strong examinee = BBEH solve accuracy above the pool mean ({pool_mean:.3f}).\n")
L.append("| Jury | κ weak examinees | κ strong examinees |")
L.append("|---|---|---|")
for n in ["Majority, all 8", "Majority, family recusal (proposal method B)",
          "Majority, agreement recusal (drop jurors whose own answer matches)"]:
    p = unsup[n][0]
    L.append(f"| {n} | {kappa(y[~strong], p[~strong]):.3f} | {kappa(y[strong], p[strong]):.3f} |")
for n in ["verdicts", "verdicts x family", "verdicts x agreement", "verdicts x agreement + agreement"]:
    p = oof_store[n][0]
    L.append(f"| LR: {n} | {kappa(y[~strong], p[~strong]):.3f} | {kappa(y[strong], p[strong]):.3f} |")
L.append(f"\nn weak = {int((~strong).sum())}, n strong = {int(strong.sum())}.")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
