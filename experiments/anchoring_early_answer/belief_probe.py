"""Does the judge's hidden state at position A (before it writes anything) already encode how strongly it believes
the candidate's answer?

belief = share of the judge's 7 fresh solves that reach the candidate's final answer (belief.py). Hidden states:
out_probe/<judge>/hidden.npy at A (probe_steer.py --phase capture; RB2 Math + JudgeBench, Qwen3.5-4B/9B).

  1. Belief probe: ridge regression hidden_A[layer] -> belief, folds = whole questions. Out-of-fold Spearman with the
     real belief, on all candidates and on WRONG candidates only (where belief is not just correctness).
  2. Among wrong candidates, how well does each signal at A pick out the ones the judge believes (>= 4 of 7) from
     the ones it never reaches (0 of 7)? belief probe vs correctness probe (trained on gold) vs the verdict at A.
  3. Does A foresee the verdict? Among wrong candidates, AUROC for "accepted at C" from the verdict at A, from the
     belief probe, and from both (logistic, out of fold).
JudgeBench is pairwise: the target is belief in the response the row is about (belief.py), signed like the verdict.

  python3 experiments/anchoring_early_answer/belief_probe.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from probes import cv_scores, folds_by_group  # noqa: E402

LAYERS_EVERY = 2


def qkey(bench, item):
    return f"{bench}|{item.rsplit('-', 1)[0]}" if bench == "rb2math" else f"{bench}|{item}"


def cv_ridge(X, y, groups, alpha=None):
    fold = folds_by_group(groups)
    p = np.full(len(y), np.nan)
    for f in range(fold.max() + 1):
        tr, te = fold != f, fold == f
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd = np.where(sd < max(1e-3 * np.median(sd), 1e-8), np.inf, sd)
        z = lambda M: np.clip((M - mu) / sd, -10, 10)
        p[te] = Ridge(alpha=alpha or X.shape[1]).fit(z(X[tr]), y[tr]).predict(z(X[te]))
    return p


def auc(y, s):
    ok = ~np.isnan(s)
    return roc_auc_score(y[ok], s[ok]) if len(set(y[ok])) == 2 else float("nan")


def boot_auc(y, s, groups, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    u = np.array(sorted(set(groups)))
    idx = {g: np.where(groups == g)[0] for g in u}
    bs = []
    for _ in range(n):
        ii = np.concatenate([idx[g] for g in rng.choice(u, len(u))])
        bs.append(auc(y[ii], s[ii]))
    return np.nanpercentile(bs, [2.5, 97.5])


def fmt(y, s, g):
    lo, hi = boot_auc(y, s, g)
    return f"{auc(y, s):.2f} [{lo:.2f}, {hi:.2f}]"


def main():
    B = {(r["judge"], r["item"]): r for r in json.load(open(HERE / "out" / "belief_rows.json"))}
    L = ["# Does the hidden state before reasoning (A) encode the judge's belief in the candidate's answer?\n",
         "belief = share of 7 fresh own solves reaching the candidate's answer. Probes on the hidden state at A, folds "
         "= whole questions, 95% intervals resample questions. 'Believed' = at least 4 of 7; 'never' = 0 of 7.\n"]
    for judge in ("qwen3.5-4b", "qwen3.5-9b"):
        meta = [json.loads(l) for l in open(HERE / "out_probe" / judge / "meta.jsonl")]
        H = np.load(HERE / "out_probe" / judge / "hidden.npy", mmap_mode="r")
        for bench in ("rb2math", "judgebench"):
            ix = [i for i, m in enumerate(meta) if m["bench"] == bench and (judge, m["item_id"]) in B]
            R = [B[(judge, meta[i]["item_id"])] for i in ix]
            belief = np.array([r["belief"] for r in R])
            gold = np.array([r["target_ok"] for r in R])
            mA = np.array([r["m_A"] for r in R], float)
            accC = np.array([np.nan if r["acc_C"] is None else r["acc_C"] for r in R], float)
            g = np.array([qkey(bench, r["item"]) for r in R])
            W = gold == 0
            layers = list(range(0, H.shape[1], LAYERS_EVERY)) + ([H.shape[1] - 1] if (H.shape[1] - 1) % 2 else [])
            L.append(f"\n## {judge}, {bench} ({len(R)} candidates, {W.sum()} wrong; "
                     f"wrong & believed {((belief >= 4 / 7) & W).sum()}, wrong & never {((belief == 0) & W).sum()})\n")
            L.append("### 1. Belief probe by layer (out-of-fold Spearman with the real belief)\n")
            L.append("| layer | all candidates | wrong candidates only |")
            L.append("|---|---|---|")
            best, bp = -1, None
            for l in layers:
                X = np.asarray(H[ix, l], np.float32)
                p = cv_ridge(X, belief, g)
                rho_all = spearmanr(p, belief).statistic
                rho_w = spearmanr(p[W], belief[W]).statistic
                L.append(f"| {l} | {rho_all:.2f} | {rho_w:.2f} |")
                if rho_all > best:
                    best, bp, bl = rho_all, p, l
            Xb = np.asarray(H[ix, bl], np.float32)
            pc = cv_scores(Xb, gold, g)  # correctness probe, same layer
            sel = W & ((belief >= 4 / 7) | (belief == 0))
            yb = (belief[sel] >= 4 / 7).astype(int)
            L.append(f"\n### 2. Wrong candidates: telling believed from never-reached (best belief layer = {bl})\n")
            L.append("| signal at A | AUROC |")
            L.append("|---|---|")
            L.append(f"| belief probe | {fmt(yb, bp[sel], g[sel])} |")
            L.append(f"| correctness probe ('is this right?') | {fmt(yb, pc[sel], g[sel])} |")
            L.append(f"| verdict at A (margin) | {fmt(yb, mA[sel], g[sel])} |")
            ok = W & ~np.isnan(accC)
            yc = accC[ok].astype(int)
            Z = np.column_stack([mA, bp])
            both = np.full(len(R), np.nan)
            fold = folds_by_group(g)
            for f in range(fold.max() + 1):
                tr, te = ok & (fold != f), ok & (fold == f)
                if len(set(accC[tr])) == 2:
                    both[te] = LogisticRegression().fit(Z[tr], accC[tr].astype(int)).predict_proba(Z[te])[:, 1]
            L.append("\n### 3. Wrong candidates: does A foresee acceptance at the verdict (C)?\n")
            L.append("| signal at A | AUROC for accepted at C |")
            L.append("|---|---|")
            L.append(f"| verdict at A | {fmt(yc, mA[ok], g[ok])} |")
            L.append(f"| belief probe | {fmt(yc, bp[ok], g[ok])} |")
            L.append(f"| verdict at A + belief probe | {fmt(yc, both[ok], g[ok])} |")
            L.append(f"| real belief (7 solves; not available at A) | {fmt(yc, belief[ok], g[ok])} |")
            print(f"done {judge} {bench}", flush=True)
    (HERE / "out" / "belief_probe.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
