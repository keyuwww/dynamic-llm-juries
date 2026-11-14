"""Can the judge tell its WRONG confident beliefs from its RIGHT ones?

Candidates the judge itself reaches often (belief >= 4/7: it would give this answer too). Label = is the candidate
actually correct. If the hidden state while judging separates these better than the judge's own verdict, the model
"knows" some of its confident beliefs are wrong and doesn't use it; if not, confident errors are invisible from inside.

Signals, all scored by AUROC (right vs wrong) on held-out questions, 95% intervals resampling questions:
  probe            ridge hidden -> correct, position (A, 25, 50, 75, C) x layer chosen by nested CV (inner folds only)
  question-only    the same probe on the AVERAGE state of all of the question's candidates (all beliefs), i.e. what
                   the model holds about the question, not this answer: the "is this a question I get wrong?" baseline
  verdict at A / C the judge's own log-odds of CORRECT before reasoning / at the verdict
  belief           4/7 .. 7/7 itself

Note: at a given belief, right and wrong candidates mostly come from DIFFERENT questions (two answers with the same
final answer are both right or both wrong), so this is largely question-level self-knowledge.

  python3 experiments/anchoring_early_answer/confident_probe.py
"""
import collections
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from belief_probe_grid import folds, ridge_fit_predict

HERE = Path(__file__).resolve().parent
CKS = ["A", "25", "50", "75", "C"]


def auc(y, s):
    m = ~np.isnan(s)
    return roc_auc_score(y[m], s[m]) if len(set(y[m])) == 2 else np.nan


def boot(g, f, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    u = np.array(sorted(set(g)))
    idx = {x: np.where(g == x)[0] for x in u}
    bs = [f(np.concatenate([idx[x] for x in rng.choice(u, len(u))])) for _ in range(n)]
    return np.nanpercentile(bs, [2.5, 97.5])


def nested(X, y, g, cells):
    """Outer 5 folds by question; inner 4 folds pick the cell; returns held-out predictions and the cells chosen."""
    outer = folds(g, 5, 1)
    p = np.full(len(y), np.nan)
    chosen = []
    for f in range(5):
        tr, te = np.where(outer != f)[0], np.where(outer == f)[0]
        inner = folds(g[tr], 4, 2)
        best, cell = -1, None
        for c in cells:
            pi = np.full(len(tr), np.nan)
            for k in range(4):
                a_, b_ = tr[inner != k], tr[inner == k]
                if len(set(y[a_])) < 2:
                    continue
                pi[inner == k] = ridge_fit_predict(X(c)[a_], y[a_].astype(float), X(c)[b_])
            s = auc(y[tr], pi)
            if np.nan_to_num(s) > best:
                best, cell = s, c
        chosen.append(cell)
        p[te] = ridge_fit_predict(X(cell)[tr], y[tr].astype(float), X(cell)[te])
    return p, chosen


def main():
    B = {(r["judge"], r["item"]): r for r in json.load(open(HERE / "out" / "belief_rows.json"))}
    L = ["# Can the judge tell its wrong confident beliefs from its right ones?\n",
         "Candidates with belief >= 4/7 (the judge itself gives this answer in at least 4 of 7 tries). AUROC for "
         "right vs wrong on held-out questions (0.5 = chance). 95% intervals resample questions. 'Probe minus verdict' "
         "is paired on the same candidates.\n"]
    for judge in ("qwen3.5-9b", "qwen3.5-4b"):
        d = HERE / "cannon_belief" / "out" / judge
        meta = [json.loads(l) for l in open(d / "meta_ckpt.jsonl")]
        H = np.load(d / "hidden_ckpt.npy", mmap_mode="r")
        pos = {(m["item_id"], m["ckpt"]): i for i, m in enumerate(meta)}
        for bench in ("rb2math", "bff"):
            allit = sorted({m["item_id"] for m in meta if m["bench"] == bench and (judge, m["item_id"]) in B})
            allit = [it for it in allit if all((it, c) in pos for c in CKS)]
            qof = {it: B[(judge, it)]["q"] or it.rsplit("-", 1)[0] for it in allit}
            items = [it for it in allit if B[(judge, it)]["belief"] >= 4 / 7]
            R = [B[(judge, it)] for it in items]
            y = np.array([r["target_ok"] for r in R])
            g = np.array([qof[it] for it in items])
            layers = list(range(2, H.shape[1], 2))
            Xc = {c: np.asarray(H[[pos[(it, c)] for it in items]], np.float32) for c in CKS}
            # question-only: mean state over ALL the question's candidates (any belief)
            byq = collections.defaultdict(list)
            for it in allit:
                byq[qof[it]].append(it)
            Xq = {}
            for c in CKS:
                full = np.asarray(H[[pos[(it, c)] for it in allit]], np.float32)
                rowof = {it: i for i, it in enumerate(allit)}
                qm = {q: full[[rowof[it] for it in its]].mean(0) for q, its in byq.items()}
                Xq[c] = np.stack([qm[q] for q in g])
            cells = [(c, l) for c in CKS for l in layers]
            pp, ch = nested(lambda cl: Xc[cl[0]][:, cl[1]], y, g, cells)
            pq, chq = nested(lambda cl: Xq[cl[0]][:, cl[1]], y, g, cells)
            mA = np.array([r.get("m_A") if r.get("m_A") is not None else np.nan for r in R], float)
            mC = np.array([r.get("m_C") if r.get("m_C") is not None else np.nan for r in R], float)
            bel = np.array([r["belief"] for r in R], float)
            nq = len(set(g))
            mixed = sum(1 for q in set(g) if len(set(y[g == q])) == 2)
            L.append(f"\n## {judge}, {bench}: {len(R)} confident candidates ({int(y.sum())} right, "
                     f"{int((1 - y).sum())} wrong) on {nq} questions; {mixed} questions have both\n")
            L.append("| signal | AUROC right vs wrong | minus the verdict at C (paired) |")
            L.append("|---|---|---|")
            for name, s in (("probe on this answer's state", pp), ("question-only probe (no answer-specific "
                            "information)", pq), ("judge's verdict at A (before reasoning)", mA),
                            ("judge's verdict at C (at the verdict)", mC), ("belief (4/7 .. 7/7)", bel)):
                lo, hi = boot(g, lambda ii, s=s: auc(y[ii], s[ii]))
                dl, dh = boot(g, lambda ii, s=s: auc(y[ii], s[ii]) - auc(y[ii], mC[ii]))
                diff = auc(y, s) - auc(y, mC)
                L.append(f"| {name} | {auc(y, s):.2f} [{lo:.2f}, {hi:.2f}] | "
                         + ("–" if s is mC else f"{diff:+.2f} [{dl:+.2f}, {dh:+.2f}]") + " |")
            L.append(f"\nCells chosen (answer probe): {', '.join(f'{c}/L{l}' for c, l in ch)}; "
                     f"(question-only): {', '.join(f'{c}/L{l}' for c, l in chq)}\n")
            # what a flag would buy: among WRONG confident beliefs the judge accepted, how many does the probe catch
            acc = np.array([r["acc_C"] if r["acc_C"] is not None else -1 for r in R])
            if np.isfinite(pp).all():
                thr = np.quantile(pp, 0.2)  # flag the 20% the probe thinks least likely right
                flag = pp <= thr
                wa = (y == 0) & (acc == 1)
                ca = (y == 1) & (acc == 1)
                L.append(f"Flag the 20% the probe rates least likely right: catches {flag[wa].sum()} of {wa.sum()} "
                         f"wrong answers the judge accepted, and flags {flag[ca].sum()} of {ca.sum()} right answers "
                         f"it accepted.\n")
                fv = np.nan_to_num(mC, nan=np.inf) <= np.quantile(mC[np.isfinite(mC)], 0.2)
                L.append(f"Same rule on the judge's own verdict log-odds at C: catches {fv[wa].sum()} of {wa.sum()} "
                         f"and flags {fv[ca].sum()} of {ca.sum()}.\n")
                # the errors that matter: among answers the judge ACCEPTED, can the signal still tell right from wrong?
                A_ = np.where(acc == 1)[0]
                ya, ga = y[A_], g[A_]
                L.append(f"Among the {len(A_)} confident answers the judge accepted ({int((1 - ya).sum())} wrong): "
                         "AUROC right vs wrong\n")
                L.append("| signal | AUROC among accepted | minus the verdict at C (paired) |")
                L.append("|---|---|---|")
                for name, s_ in (("probe on this answer's state", pp[A_]), ("question-only probe", pq[A_]),
                                 ("judge's verdict at A", mA[A_]), ("judge's verdict at C", mC[A_])):
                    lo, hi = boot(ga, lambda ii, s_=s_: auc(ya[ii], s_[ii]))
                    dl, dh = boot(ga, lambda ii, s_=s_: auc(ya[ii], s_[ii]) - auc(ya[ii], mC[A_][ii]))
                    L.append(f"| {name} | {auc(ya, s_):.2f} [{lo:.2f}, {hi:.2f}] | "
                             + ("–" if name.endswith("at C") else
                                f"{auc(ya, s_) - auc(ya, mC[A_]):+.2f} [{dl:+.2f}, {dh:+.2f}]") + " |")
                L.append("")
            print(f"done {judge} {bench}", flush=True)
    (HERE / "out" / "confident_probe.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
