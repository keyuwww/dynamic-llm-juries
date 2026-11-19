"""How many own answers does belief need? Held-out prediction of approval from k = 1, 2, 3, 5, 7 own answers (Nov 18).

Reviewer item B2. Rows: the audited wrong-answer judgments of paper_numbers.py (all seven judges). For each row the
per-sample votes (own answer s = 1..7 reaches the candidate's answer: True / False / None = undecided) are rebuilt
exactly as belief.py:build does, keeping each sample's index. A subset of k sample indices is drawn per
(judge, question) and shared by every candidate of that judge and question; belief_k = share of the subset's decided
votes that match (rows with no decided vote in the subset get the training-fold mean).

Model: logistic regression, approval ~ judge-by-benchmark intercepts + feature(s), fit by IRLS with a small ridge
(1e-3, intercepts unpenalised is not needed at this size). Five outer folds grouped by question: every judge and
candidate of a question is in the same fold. Methods:
  base      intercepts only
  one       + the separate one-sample label (sample 0; prior work's "matches my answer")
  b{k}      + belief from k of the 7 samples
  b7+one    + both
JudgeBench (pairwise) protocol, separately: b{k} vs b{k} + competitor belief from the same k samples.
Losses: held-out Brier and log loss (probabilities clipped to [1e-4, 1 - 1e-4]); AUROC secondary.
Uncertainty: R subset draws per k (Monte-Carlo SD of the pooled loss), and 2,000 question-bootstrap draws of the
paired per-row loss difference (averaged over subset draws) for each method vs base and vs one.
Writes validation/sample_budget.json and .md.
"""
import collections
import gzip
import json
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parent
HERE = V.parent
sys.path.insert(0, str(V))
sys.path.insert(0, str(HERE))
import paper_numbers as P  # noqa: E402

KS = [1, 2, 3, 5, 7]
R = 100
NBOOT = 2000
EPS = 1e-4
FOLDS = 5


def letter(text):
    import re
    x = re.findall(r"\b([A-J])\1{4}\b", text or "")
    return x[-1] if x else None


def loadj(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def votes_for_family(od, sfx):
    """(judge, item) -> dict(t=[v1..v7], o=[competitor v1..v7] or None) exactly as belief.py:build."""
    src = HERE / od
    jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, gzip.open(HERE / "inputs" / f"readout_jobs{sfx}.jsonl.gz", "rt"))
            if j["bench"] in ("rb2math", "judgebench", "bff")}
    own = collections.defaultdict(dict)
    for s in loadj(src / "solves_k.jsonl"):
        own[(s["model"], s["qid"])][s["sample"]] = s
    glm = {r["cache_key"]: r["verdict"] for r in loadj(src / "matches_glm5.3-flash_k.jsonl")}
    for s in loadj(src / "solves_k_rerun.jsonl"):
        own[(s["model"], s["qid"])][s["sample"]] = s
    glm.update({r["cache_key"]: r["verdict"] for r in loadj(src / "matches_glm5.3-flash_k_rerun.jsonl")})

    def votes(judge, j, ci):
        out = [None] * 7
        cand = j["candidates"][ci]
        for s, o in own[(judge, j["qid"])].items():
            if not 1 <= s <= 7:
                continue
            if j["bench"] == "judgebench" and letter(o["answer"]) and letter(cand):
                out[s - 1] = letter(o["answer"]) == letter(cand)
            else:
                v = glm.get(f"{judge}|{j['item_id']}|{ci}|s{s}")
                out[s - 1] = None if v not in ("SAME", "DIFFERENT") else v == "SAME"
        return out
    return jobs, votes


def rows():
    R_ = []
    for fam, od, sfx in P.FAM:
        raw = {(r["judge"], r["item"]): r for r in json.load(open(HERE / od / "belief_rows_clean.json"))}
        jobs, votes = votes_for_family(od, sfx)
        for r in P.load(od, sfx):
            if r["ok"] or not r["audited"]:
                continue
            j = jobs[(r["judge"], r["item"])]
            src = raw[(r["judge"], r["item"])]
            if j["bench"] == "judgebench":
                gold = int(j["gold"])
                ti = 0 if ((gold == 1) if src["target_ok"] else (gold == 0)) else 1
            else:
                ti = 0
            t = votes(r["judge"], j, ti)
            dec = [v for v in t if v is not None]
            assert abs(np.mean(dec) - r["belief"]) < 1e-9, (r["judge"], r["item"])  # same belief as the paper
            o = votes(r["judge"], j, 1 - ti) if j["bench"] == "judgebench" else None
            R_.append(dict(r, fam=fam, t=t, o=o, jq=f"{r['judge']}|{r['qid']}", jb=f"{r['judge']}|{r['bench']}"))
    return R_


def fit_predict(Xtr, ytr, Xte, lam=1e-3, it=50):
    w = np.zeros(Xtr.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-(Xtr @ w)))
        g = Xtr.T @ (p - ytr) + lam * w
        H = (Xtr * (p * (1 - p))[:, None]).T @ Xtr + lam * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return 1 / (1 + np.exp(-(Xte @ w)))


def losses(p, y):
    p = np.clip(p, EPS, 1 - EPS)
    return (p - y) ** 2, -(y * np.log(p) + (1 - y) * np.log(1 - p))


def auroc(p, y):
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return np.nan
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order)); ranks[order] = np.arange(1, len(order) + 1)
    # average ranks for ties
    allp = np.concatenate([pos, neg])
    for v in np.unique(allp):
        m = allp == v
        ranks[m] = ranks[m].mean()
    return (ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def subset_belief(rows_, k, rng, which="t"):
    """belief_k per row with one subset of k indices per (judge, question)."""
    sub = {}
    out = np.full(len(rows_), np.nan)
    for i, r in enumerate(rows_):
        if r["jq"] not in sub:
            sub[r["jq"]] = rng.choice(7, k, replace=False) if k < 7 else np.arange(7)
        vs = [r[which][s] for s in sub[r["jq"]] if r[which] is not None and r[which][s] is not None]
        if vs:
            out[i] = np.mean(vs)
    return out


def evaluate(rows_, feats_fn, folds, y, D):
    """feats_fn() -> (n, f) feature matrix (may contain nan: filled with train mean). Returns held-out p."""
    F = feats_fn()
    p = np.zeros(len(y))
    for f in range(FOLDS):
        tr, te = folds != f, folds == f
        Ft = F.copy()
        if F.shape[1]:
            mu = np.nanmean(F[tr], axis=0)
            for c in range(F.shape[1]):
                Ft[np.isnan(Ft[:, c]), c] = mu[c]
        X = np.hstack([D, Ft])
        p[te] = fit_predict(X[tr], y[tr], X[te])
    return p


def run(rows_, tag):
    y = np.array([r["y"] for r in rows_], float)
    qs = sorted({r["qid"] for r in rows_})
    rng0 = np.random.default_rng(0)
    perm = rng0.permutation(len(qs))
    fold_of = {q: perm[i] % FOLDS for i, q in enumerate(qs)}
    folds = np.array([fold_of[r["qid"]] for r in rows_])
    jbs = sorted({r["jb"] for r in rows_})
    D = np.array([[r["jb"] == j for j in jbs] for r in rows_], float)
    one = np.array([[r["match0"]] for r in rows_], float)
    res, per_row = {}, {}

    def record(name, ps):
        B = np.array([losses(p, y)[0] for p in ps]); L = np.array([losses(p, y)[1] for p in ps])
        res[name] = dict(brier=float(B.mean()), logloss=float(L.mean()),
                         brier_mc_sd=float(B.mean(1).std()), logloss_mc_sd=float(L.mean(1).std()),
                         auroc=float(np.nanmean([auroc(p, y) for p in ps])), draws=len(ps))
        per_row[name] = (B.mean(0), L.mean(0))

    if True:
        record("base", [evaluate(rows_, lambda: np.zeros((len(y), 0)), folds, y, D)])
        record("one", [evaluate(rows_, lambda: one, folds, y, D)])
    for k in KS:
        rng = np.random.default_rng(1000 + k)
        ps = []
        for _ in range(R if k < 7 else 1):
            st = np.random.default_rng(rng.integers(1 << 31))
            bt = subset_belief(rows_, k, st, "t")
            ps.append(evaluate(rows_, lambda: bt[:, None], folds, y, D))
        record(f"b{k}", ps)
    if True:
        b7 = subset_belief(rows_, 7, np.random.default_rng(0))
        record("b7+one", [evaluate(rows_, lambda: np.column_stack([b7, one[:, 0]]), folds, y, D)])
    # paired question bootstrap of loss differences
    byq = collections.defaultdict(list)
    for i, r in enumerate(rows_):
        byq[r["qid"]].append(i)
    qlist = list(byq)
    rngb = np.random.default_rng(7)
    idx = [np.concatenate([byq[qlist[j]] for j in rngb.choice(len(qlist), len(qlist))]) for _ in range(NBOOT)]
    comps = {}
    refs = ["base", "one", "b1", "b2", "b3", "b5"]
    for ref in refs:
        for name in per_row:
            if name == ref:
                continue
            d = {}
            for li, lname in enumerate(["brier", "logloss"]):
                diff = per_row[name][li] - per_row[ref][li]
                bs = [diff[ix].mean() for ix in idx]
                d[lname] = dict(diff=float(diff.mean()), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)))
            comps[f"{name} - {ref}"] = d
    return dict(tag=tag, n_rows=len(rows_), n_questions=len(qs), n_judges=len({r['judge'] for r in rows_}),
                approval_rate=float(y.mean()), methods=res, paired=comps)


def run_competitor(rows_):
    """JudgeBench: belief_k alone vs belief_k + competitor belief_k from the same k samples."""
    y = np.array([r["y"] for r in rows_], float)
    qs = sorted({r["qid"] for r in rows_})
    perm = np.random.default_rng(0).permutation(len(qs))
    fold_of = {q: perm[i] % FOLDS for i, q in enumerate(qs)}
    folds = np.array([fold_of[r["qid"]] for r in rows_])
    jbs = sorted({r["jb"] for r in rows_})
    D = np.array([[r["jb"] == j for j in jbs] for r in rows_], float)
    out = {}
    for k in KS:
        rng = np.random.default_rng(2000 + k)
        A, B = [], []
        for _ in range(R if k < 7 else 1):
            sub = {}
            bt, bo = np.full(len(y), np.nan), np.full(len(y), np.nan)
            for i, r in enumerate(rows_):
                if r["jq"] not in sub:
                    sub[r["jq"]] = rng.choice(7, k, replace=False) if k < 7 else np.arange(7)
                vt = [r["t"][s] for s in sub[r["jq"]] if r["t"][s] is not None]
                vo = [r["o"][s] for s in sub[r["jq"]] if r["o"][s] is not None]
                bt[i] = np.mean(vt) if vt else np.nan
                bo[i] = np.mean(vo) if vo else np.nan
            A.append(losses(evaluate(rows_, lambda: bt[:, None], folds, y, D), y))
            B.append(losses(evaluate(rows_, lambda: np.column_stack([bt, bo]), folds, y, D), y))
        out[f"k{k}"] = {m: dict(brier=float(np.mean([a[0].mean() for a in X])), logloss=float(np.mean([a[1].mean() for a in X])))
                        for m, X in [("target", A), ("target+competitor", B)]}
    return dict(n_rows=len(rows_), by_k=out)


def main():
    rows_ = rows()
    print(f"{len(rows_)} audited wrong-answer judgments rebuilt; belief matches the paper's on every row", flush=True)
    out = dict(settings=dict(ks=KS, subset_draws=R, bootstrap=NBOOT, eps=EPS, folds=FOLDS, ridge=1e-3),
               all=run(rows_, "all seven judges"))
    print(json.dumps(out["all"]["methods"], indent=1), flush=True)
    jb = [r for r in rows_ if r["bench"] == "judgebench" and r["o"] is not None]
    out["judgebench_competitor"] = run_competitor(jb)
    (V / "sample_budget.json").write_text(json.dumps(out, indent=1) + "\n")
    A = out["all"]
    L = [f"# How many own answers does belief need? (held-out prediction of approval)\n",
         f"{A['n_rows']} audited wrong-answer judgments, {A['n_questions']} questions, {A['n_judges']} judges; "
         f"approval rate {A['approval_rate']:.3f}. 5 folds grouped by question; logistic, judge-by-benchmark intercepts; "
         f"{R} subset draws per k; {NBOOT} question-bootstrap draws.\n",
         "| method | Brier | log loss | AUROC | MC SD (Brier) |", "|---|---|---|---|---|"]
    for n, m in A["methods"].items():
        L.append(f"| {n} | {m['brier']:.4f} | {m['logloss']:.4f} | {m['auroc']:.3f} | {m['brier_mc_sd']:.5f} |")
    L.append("\nPaired differences (negative = better than the reference), 95% question-bootstrap interval:\n")
    L.append("| comparison | Brier diff | log-loss diff |\n|---|---|---|")
    for n, d in A["paired"].items():
        L.append(f"| {n} | {d['brier']['diff']:+.4f} [{d['brier']['lo']:+.4f}, {d['brier']['hi']:+.4f}] | "
                 f"{d['logloss']['diff']:+.4f} [{d['logloss']['lo']:+.4f}, {d['logloss']['hi']:+.4f}] |")
    C = out["judgebench_competitor"]
    L.append(f"\n## JudgeBench pairwise protocol ({C['n_rows']} judgments): target belief alone vs + competitor belief\n")
    L.append("| k | target Brier | +competitor Brier | target log loss | +competitor log loss |\n|---|---|---|---|---|")
    for k, d in C["by_k"].items():
        L.append(f"| {k} | {d['target']['brier']:.4f} | {d['target+competitor']['brier']:.4f} | "
                 f"{d['target']['logloss']:.4f} | {d['target+competitor']['logloss']:.4f} |")
    (V / "sample_budget.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
