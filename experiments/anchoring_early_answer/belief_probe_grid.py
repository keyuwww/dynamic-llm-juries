"""Where (reasoning position x layer) is the judge's belief in the candidate's answer most readable? With an honest
held-out estimate: the position and layer are chosen on validation folds only.

Hidden states: cannon_belief/out/<judge>/hidden_ckpt.npy (+ meta_ckpt.jsonl): last token at A (before writing),
25 / 50 / 75 % of the written reasoning, and C (at the verdict word), every layer; RB2 Math + BFF, thinking off.
belief = share of the judge's 7 fresh solves reaching the candidate's answer (belief.py).

Probe: ridge regression hidden -> belief, trained on ALL candidates (right and wrong). Score = AUROC, among WRONG
candidates, for believed (>= 4/7) vs never reached (0/7): belief that is not just correctness.

  1. Grid: 5-fold cross-validated score for every (position, layer) - descriptive.
  2. Nested: outer 5 folds by question; inside each outer training set, 4 inner folds choose (position, layer);
     that one probe is then scored on the outer test questions. Reported with the choices made.
  3. At the chosen cell, compared with the verdict the judge would give there and with a correctness probe.

  python3 experiments/anchoring_early_answer/belief_probe_grid.py [--judges qwen3.5-9b,qwen3.5-4b]
  python3 experiments/anchoring_early_answer/belief_probe_grid.py --judges llama3.1-8b \
      --rows experiments/anchoring_early_answer/out/belief_rows_llama3.1-8b.json \
      --out experiments/anchoring_early_answer/out/belief_probe_grid_llama.md
"""
import argparse
import collections
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
CKS = ["A", "25", "50", "75", "C"]


def folds(groups, k, seed):
    u = sorted(set(groups))
    f = dict(zip(np.random.default_rng(seed).permutation(u), np.arange(len(u)) % k))
    return np.array([f[g] for g in groups])


def ridge_fit_predict(Xtr, ytr, Xte, lam=1.0):
    """Standardised ridge in dual form (n << d): w = Z^T (Z Z^T + lam*d I)^-1 (y - mean)."""
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd = np.where(sd < 1e-6, np.inf, sd)
    Z, Zt = (Xtr - mu) / sd, (Xte - mu) / sd
    K = Z @ Z.T
    a = np.linalg.solve(K + lam * Z.shape[1] * np.eye(len(K)), ytr - ytr.mean())
    return Zt @ (Z.T @ a) + ytr.mean()


def score(y_belief, wrong, pred):
    m = wrong & ((y_belief >= 4 / 7) | (y_belief == 0))
    yy = (y_belief[m] >= 4 / 7).astype(int)
    return roc_auc_score(yy, pred[m]) if len(set(yy)) == 2 else np.nan


def boot(groups, f, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    u = np.array(sorted(set(groups)))
    idx = {g: np.where(groups == g)[0] for g in u}
    bs = [f(np.concatenate([idx[g] for g in rng.choice(u, len(u))])) for _ in range(n)]
    return np.nanpercentile(bs, [2.5, 97.5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="qwen3.5-9b,qwen3.5-4b")
    ap.add_argument("--src", default=str(HERE / "cannon_belief" / "out"))
    ap.add_argument("--rows", default=str(HERE / "out" / "belief_rows.json"))
    ap.add_argument("--out", default=str(HERE / "out" / "belief_probe_grid.md"))
    a = ap.parse_args()
    B = {(r["judge"], r["item"]): r for r in json.load(open(a.rows))}
    L = ["# Where is the judge's belief readable? Position x layer, chosen on validation folds\n",
         "Ridge probe hidden -> belief (share of 7 own solves reaching the candidate's answer), trained on all "
         "candidates. Score: AUROC among WRONG candidates, believed (>= 4/7) vs never reached (0/7). Folds = whole "
         "questions. 95% intervals resample questions.\n"]
    for judge in a.judges.split(","):
        d = Path(a.src) / judge
        meta = [json.loads(l) for l in open(d / "meta_ckpt.jsonl")]
        H = np.load(d / "hidden_ckpt.npy", mmap_mode="r")
        pos = {(m["item_id"], m["ckpt"]): i for i, m in enumerate(meta)}
        for bench in ("rb2math", "bff"):
            items = sorted({m["item_id"] for m in meta if m["bench"] == bench and (judge, m["item_id"]) in B})
            items = [it for it in items if all((it, c) in pos for c in CKS)]  # every checkpoint present
            R = [B[(judge, it)] for it in items]
            if not R:
                continue
            y = np.array([r["belief"] for r in R])
            gold = np.array([r["target_ok"] for r in R])
            wrong = gold == 0
            g = np.array([f"{bench}|{r['q']}" if r.get("q") else f"{bench}|{r['item'].rsplit('-', 1)[0]}" for r in R])
            layers = list(range(1, H.shape[1]))
            X = {c: np.asarray(H[[pos[(it, c)] for it in items]], np.float32) for c in CKS}  # [n, layers, d]
            nb, nn = int((wrong & (y >= 4 / 7)).sum()), int((wrong & (y == 0)).sum())
            L.append(f"\n## {judge}, {bench}: {len(R)} candidates; wrong & believed {nb}, wrong & never {nn}\n")

            # 1. descriptive grid (5-fold CV)
            fo = folds(g, 5, 0)
            grid = {}
            for c in CKS:
                for l in layers:
                    p = np.full(len(y), np.nan)
                    for f in range(5):
                        tr, te = fo != f, fo == f
                        p[te] = ridge_fit_predict(X[c][tr, l], y[tr], X[c][te, l])
                    grid[(c, l)] = (score(y, wrong, p), p)
            L.append("### 1. Cross-validated score by position and layer (every 4th layer shown)\n")
            show = [l for l in layers if l % 4 == 0 or l == layers[-1]]
            L.append("| position | " + " | ".join(f"L{l}" for l in show) + " | best layer |")
            L.append("|---|" + "---|" * (len(show) + 1))
            for c in CKS:
                bl = max(layers, key=lambda l: np.nan_to_num(grid[(c, l)][0]))
                L.append(f"| {c} | " + " | ".join(f"{grid[(c, l)][0]:.2f}" for l in show) +
                         f" | L{bl}: {grid[(c, bl)][0]:.2f} |")

            # 2. nested selection
            outer = folds(g, 5, 1)
            pn = np.full(len(y), np.nan)
            chosen = []
            for f in range(5):
                tr, te = np.where(outer != f)[0], np.where(outer == f)[0]
                inner = folds(g[tr], 4, 2)
                best, cell = -1, None
                for c in CKS:
                    for l in layers[::2]:
                        pi = np.full(len(tr), np.nan)
                        for k in range(4):
                            a_, b_ = tr[inner != k], tr[inner == k]
                            pi[inner == k] = ridge_fit_predict(X[c][a_, l], y[a_], X[c][b_, l])
                        s = score(y[tr], wrong[tr], pi)
                        if np.nan_to_num(s) > best:
                            best, cell = s, (c, l)
                chosen.append(cell)
                pn[te] = ridge_fit_predict(X[cell[0]][tr, cell[1]], y[tr], X[cell[0]][te, cell[1]])
            lo, hi = boot(g, lambda ii: score(y[ii], wrong[ii], pn[ii]))
            L.append(f"\n### 2. Held-out (nested) score: {score(y, wrong, pn):.2f} [{lo:.2f}, {hi:.2f}]\n")
            L.append("Cells chosen in the 5 outer folds: " + ", ".join(f"{c}/L{l}" for c, l in chosen) + "\n")

            # 3. baselines at the most-chosen cell
            c, l = collections.Counter(chosen).most_common(1)[0][0]
            cv_p = grid[(c, l)][1]
            m_ck = np.array([r.get(f"m_{c}") if r.get(f"m_{c}") is not None else np.nan for r in R], float)
            pc = np.full(len(y), np.nan)
            for f in range(5):
                tr, te = fo != f, fo == f
                pc[te] = ridge_fit_predict(X[c][tr, l], gold[tr].astype(float), X[c][te, l])
            L.append(f"### 3. At {c} / L{l}: belief probe vs other signals (wrong candidates, believed vs never)\n")
            L.append("| signal | AUROC |")
            L.append("|---|---|")
            for name, s in (("belief probe", cv_p), ("correctness probe (same position and layer)", pc),
                            (f"verdict the judge would give at {c}", m_ck)):
                lo, hi = boot(g, lambda ii, s=s: score(y[ii], wrong[ii], s[ii]))
                L.append(f"| {name} | {score(y, wrong, s):.2f} [{lo:.2f}, {hi:.2f}] |")
            print(f"done {judge} {bench}", flush=True)
    out = Path(a.out)
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
