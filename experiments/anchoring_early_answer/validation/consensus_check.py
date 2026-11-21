"""Own belief vs other judges' belief (Nov 21 strict review, item B2). CPU only; no model calls; POST HOC.

Question: does a judge's OWN belief in a wrong candidate predict its approval beyond how much OTHER models agree
with that candidate? If not, the finding is about shared answer agreement (the candidate is a popular wrong answer)
rather than anything specific to the judge.

For every (judge, wrong candidate) judgment:
  own        the judge's belief (share of its 7 own answers reaching the candidate)
  cons_j     leave-that-judge-out consensus: mean belief of the OTHER judges in the same candidate
  cons_f     leave-that-family-out consensus: mean belief of judges from OTHER families (stricter: a Qwen judge's
             consensus uses no Qwen)
  own_c, cons_c   the same for the competing (right) response, pairwise data only
Analyses, per dataset:
  1. Linear probability model, benchmark-by-judge fixed effects: y ~ cons, and y ~ cons + own (coefficients 0->1 in
     points, 95% question-cluster bootstrap, 2,000 draws).
  2. Prediction on held-out questions: logistic regression with benchmark-by-judge intercepts; 10-fold split by
     question; out-of-fold log loss, Brier and AUROC for intercepts only / cons / cons + own / own. The paired
     difference (cons + own) - cons resamples questions (2,000 draws). Repeated over 5 fold partitions.
  3. Collinearity and identifying sample: corr(own, cons); judgments with |own - cons| >= 2/7.
Datasets: original study (7 judges, audited wrong answers), MMLU-Pro replication (4 judges; lenient parser; key and
complete-audit labels), math replication (4 judges; key and audited labels).

  python validation/consensus_check.py   -> validation/consensus_check.{json,md}
"""
import collections
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parent
HERE = V.parent
sys.path.insert(0, str(V))
import paper_numbers as P  # noqa: E402

NB = 2000


def _mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(m)
    return m


def family(j):
    j = j.lower()
    return "qwen" if j.startswith("qwen") else "nvidia" if "nemotron" in j else "deepseek" if "deepseek" in j else \
        "kimi" if "kimi" in j else j


# ------------------------------------------------------------------------------------------------ datasets
def original():
    rows = []
    for _, od, sfx in P.FAM:
        raw = {(r["judge"], r["item"]): r for r in json.load(open(HERE / od / "belief_rows_clean.json"))}
        for r in P.load(od, sfx):
            if r["ok"] or not r["audited"]:
                continue
            bo = raw[r["judge"], r["item"]].get("belief_other")
            rows.append(dict(judge=r["judge"], cand=f"{r['bench']}|{r['item']}", qid=r["qid"], bench=r["bench"],
                             y=r["y"], own=r["belief"], own_c=None if bo is None else float(bo)))
    return rows


def replication(kind, labels):
    if kind == "mmlu":
        A = _mod("rep_analyze", HERE / "replication" / "analyze.py")
        A.LENIENT = True
        audit = {r["qid"]: r["verdict"] for f in ("audit.jsonl", "audit_extra.jsonl") for r in A.load(A.DATA / f)}
        R, _ = A.rows(80, 6000, audit)
    else:
        M = _mod("math_analyze", HERE / "replication_math" / "analyze_math.py")
        audit = {r["qid"]: r["verdict"] for r in M.A.load(M.DATA / "audit.jsonl")}
        R, _ = M.rows(80, 1800, audit)
    if labels == "audited":
        R = [r for r in R if r["audit"] == "LABEL_OK"]
    return [dict(judge=r["judge"], cand=r["qid"], qid=r["qid"], bench=kind, y=r["y"], own=r["belief"],
                 own_c=r["belief_other"]) for r in R]


def add_consensus(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["cand"]].append(r)
    out = []
    for r in rows:
        oth = [o for o in by[r["cand"]] if o["judge"] != r["judge"]]
        ofam = [o for o in oth if family(o["judge"]) != family(r["judge"])]
        if not ofam:
            continue
        r = dict(r, cons_j=float(np.mean([o["own"] for o in oth])), cons_f=float(np.mean([o["own"] for o in ofam])))
        if r["own_c"] is not None:
            oc = [o["own_c"] for o in ofam if o["own_c"] is not None]
            r["cons_c"] = float(np.mean(oc)) if oc else None
        out.append(r)
    return out


# ------------------------------------------------------------------------------------------------ models
def lpm(R, xs):
    return P.ols(R, "y", xs, [lambda r: f"{r['bench']}|{r['judge']}"])


def design(R, xs, levels):
    idx = {g: i for i, g in enumerate(levels)}
    D = np.zeros((len(R), len(levels) + len(xs)))
    for n, r in enumerate(R):
        g = f"{r['bench']}|{r['judge']}"
        if g in idx:
            D[n, idx[g]] = 1
        for k, x in enumerate(xs):
            D[n, len(levels) + k] = r[x]
    return D


def logit_fit(X, y, ridge=1e-3):
    w = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y) + ridge * w
        H = (X * (p * (1 - p))[:, None]).T @ X + ridge * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-9:
            break
    return w


def auroc(p, y):
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return np.nan
    allp = np.concatenate([pos, neg])
    ranks = np.empty(len(allp))
    order = allp.argsort(kind="mergesort")
    ranks[order] = np.arange(1, len(allp) + 1)
    for v in np.unique(allp):  # average ties
        m = allp == v
        ranks[m] = ranks[m].mean()
    return (ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def oof(R, xs, seed, k=10):
    qs = sorted({r["qid"] for r in R})
    rng = np.random.default_rng(seed)
    fold = dict(zip(qs, rng.permutation(len(qs)) % k))
    levels = sorted({f"{r['bench']}|{r['judge']}" for r in R})
    y = np.array([r["y"] for r in R], float)
    f = np.array([fold[r["qid"]] for r in R])
    X = design(R, xs, levels)
    p = np.zeros(len(R))
    for i in range(k):
        tr, te = f != i, f == i
        p[te] = 1 / (1 + np.exp(-X[te] @ logit_fit(X[tr], y[tr])))
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return p


def per_row_loss(p, y):
    return -(y * np.log(p) + (1 - y) * np.log(1 - p)), (p - y) ** 2


def paired_boot(R, d, seed=0):
    by = collections.defaultdict(float)
    for r, v in zip(R, d):
        by[r["qid"]] += v
    qs = list(by)
    s = np.array([by[q] for q in qs])
    n = len(R)
    cnt = collections.Counter(r["qid"] for r in R)
    c = np.array([cnt[q] for q in qs], float)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(NB):
        i = rng.integers(0, len(qs), len(qs))
        draws.append(s[i].sum() / c[i].sum())
    return float(s.sum() / n), *np.percentile(draws, [2.5, 97.5]).tolist()


def analyse(name, R, cons="cons_f"):
    R = [r for r in R if r.get(cons) is not None]
    y = np.array([r["y"] for r in R], float)
    own = np.array([r["own"] for r in R])
    cs = np.array([r[cons] for r in R])
    res = dict(n=len(R), questions=len({r["qid"] for r in R}), candidates=len({r["cand"] for r in R}),
               corr_own_cons=float(np.corrcoef(own, cs)[0, 1]),
               n_diff_2of7=int((np.abs(own - cs) >= 2 / 7 - 1e-9).sum()),
               n_own_gt_cons=int((own - cs >= 2 / 7 - 1e-9).sum()), n_own_lt_cons=int((cs - own >= 2 / 7 - 1e-9).sum()))
    for lab, xs in (("lpm_cons", [cons]), ("lpm_cons_own", [cons, "own"])):
        e, lo, hi = P.boot(R, lambda X, xs=xs: lpm(X, xs))
        res[lab] = dict(zip(xs, [[100 * e[i], 100 * lo[i], 100 * hi[i]] for i in range(len(xs))]))
    pair = [r for r in R if r.get("own_c") is not None and r.get("cons_c") is not None]
    if len(pair) > 200:
        xs = ["cons_c", cons, "own_c", "own"]
        e, lo, hi = P.boot(pair, lambda X: lpm(X, xs))
        res["lpm_pairwise"] = dict(n=len(pair), **dict(zip(xs, [[100 * e[i], 100 * lo[i], 100 * hi[i]]
                                                               for i in range(len(xs))])))
    # held-out prediction
    specs = {"intercepts": [], "cons": [cons], "cons+own": [cons, "own"], "own": ["own"]}
    pred = {}
    for seed in range(5):
        for s, xs in specs.items():
            pred.setdefault(s, []).append(oof(R, xs, seed))
    ho = {}
    for s in specs:
        P0 = np.mean(pred[s], axis=0)  # average over partitions for the point metrics
        ll, br = per_row_loss(P0, y)
        ho[s] = dict(logloss=float(ll.mean()), brier=float(br.mean()), auroc=float(auroc(P0, y)))
    ll_c, br_c = per_row_loss(np.mean(pred["cons"], axis=0), y)
    ll_co, br_co = per_row_loss(np.mean(pred["cons+own"], axis=0), y)
    ho["delta_logloss_own_given_cons"] = paired_boot(R, ll_co - ll_c)
    ho["delta_brier_own_given_cons"] = paired_boot(R, br_co - br_c)
    ho["delta_logloss_by_partition"] = [float((per_row_loss(pred["cons+own"][i], y)[0]
                                              - per_row_loss(pred["cons"][i], y)[0]).mean()) for i in range(5)]
    ll_o, _ = per_row_loss(np.mean(pred["own"], axis=0), y)
    ho["delta_logloss_cons_given_own"] = paired_boot(R, ll_co - ll_o)
    res["heldout"] = ho
    print(name, cons, json.dumps({k: v for k, v in res.items() if k != "heldout"}), flush=True)
    return res


def main():
    D = {"original (7 judges, audited)": add_consensus(original())}
    for kind, labs in (("mmlu", ("key", "audited")), ("math", ("key", "audited"))):
        for lab in labs:
            D[f"{'MMLU-Pro' if kind == 'mmlu' else 'math'} ({lab})"] = add_consensus(replication(kind, lab))
    out = {}
    for name, R in D.items():
        out[name] = {c: analyse(name, R, c) for c in ("cons_f", "cons_j")}
    (V / "consensus_check.json").write_text(json.dumps(out, indent=1) + "\n")
    f = lambda t: f"{t[0]:+.0f} [{t[1]:+.0f}, {t[2]:+.0f}]"
    L = ["# Own belief vs other judges' belief (Nov 21 review B2; post hoc)\n", __doc__.split("Datasets")[0], "",
         "cons_f = other families only; cons_j = all other judges. LPM: points per 0->1, benchmark-by-judge FE.",
         "Held-out: 10-fold by question, logistic, 5 partitions averaged; delta = (cons+own) - cons, negative = own helps.\n",
         "| data | consensus | n (q) | corr | |own-cons|>=2/7 | LPM cons alone | LPM cons (+own) | LPM own (+cons) | "
         "logloss cons | logloss cons+own | delta logloss [95%] | AUROC cons -> cons+own |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, v in out.items():
        for c, r in v.items():
            h = r["heldout"]
            d = h["delta_logloss_own_given_cons"]
            L.append(f"| {name} | {c} | {r['n']} ({r['questions']}) | {r['corr_own_cons']:.2f} | {r['n_diff_2of7']} | "
                     f"{f(r['lpm_cons'][c])} | {f(r['lpm_cons_own'][c])} | {f(r['lpm_cons_own']['own'])} | "
                     f"{h['cons']['logloss']:.4f} | {h['cons+own']['logloss']:.4f} | "
                     f"{d[0]:+.4f} [{d[1]:+.4f}, {d[2]:+.4f}] | {h['cons']['auroc']:.3f} -> {h['cons+own']['auroc']:.3f} |")
    L += ["", "Pairwise (competing right response included), cons_f:"]
    for name, v in out.items():
        r = v["cons_f"].get("lpm_pairwise")
        if r:
            L.append(f"- {name}: n={r['n']}; own {f(r['own'])}, cons {f(r['cons_f'])}, own (right) {f(r['own_c'])}, "
                     f"cons (right) {f(r['cons_c'])}")
    (V / "consensus_check.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
