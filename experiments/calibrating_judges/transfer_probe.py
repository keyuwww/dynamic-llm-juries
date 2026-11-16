#!/usr/bin/env python
"""A judge probe for a NEW task with zero labels from that task: train on two benchmarks, score the third; with and without the verdict direction.

Probe = confirm_probe.py's better probe (standardised logistic regression, C = 0.01, at every saved layer, probabilities averaged), last-token activations.
Verdict removal (label-free): for each benchmark and each layer, the difference between the mean activation when the judge gives one verdict and the
other (CORRECT/INCORRECT, or A/B on JudgeBench), computed from that benchmark's own activations and the judge's own verdicts, is projected out.
Per cheap judge and held-out benchmark:
  transfer_raw        trained on the other two benchmarks, no removal
  transfer_removed    trained on the other two benchmarks, verdict direction removed (PRIMARY, fixed before running)
  in_domain           trained on the held-out benchmark itself (5 folds by question); needs its labels, an upper reference
  verdict_only        random among items the judge marked 'correct' (zero labels; JudgeBench: random)
Accuracy with 20% escalated to the README's stronger judge (unfinished answers first) and AUROC. 95% paired bootstrap CIs over questions.
Pre-registered pass bar: transfer_removed beats verdict_only with the CI above 0 in at least 3 of the 6 BFF / Safety settings.
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, warnings
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from cascade_eval import gen, load_run, BENCH
warnings.filterwarnings("ignore")


def fit_pred(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr); return LogisticRegression(C=0.01, max_iter=2000).fit(sc.transform(Xtr), ytr).predict_proba(sc.transform(Xte))[:, 1]


def probe(Atr, ytr, Ate, nj):
    return np.mean(Parallel(n_jobs=nj)(delayed(fit_pred)(Atr[:, l], ytr, Ate[:, l]) for l in range(Atr.shape[1])), 0)


def remove_verdict(A, v, fin):
    vals = sorted(set(v[fin])); a_, b_ = vals[0], vals[1]; out = A.copy()
    for l in range(A.shape[1]):
        d = A[fin & (v == a_), l].mean(0) - A[fin & (v == b_), l].mean(0); d = d / (np.linalg.norm(d) + 1e-8); out[:, l] -= np.outer(out[:, l] @ d, d)
    return out


def esc_acc(trust, ol, oh, fin, tie):
    n = len(ol); m = int(round(0.2 * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True
    return np.where(e, oh, ol).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True); ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json")
    ap.add_argument("--n-boot", type=int, default=1000); ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_transfer")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); j = a.judge; nj = a.threads; D = {}
    for b in BENCH:
        _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"]); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]
        A = np.load(f"{p}_acts.npy").astype(np.float32); v = L["verdict"].astype(str).values; fin = L["verdict"].notna().values
        D[b] = dict(A=A, Ar=remove_verdict(A, v, fin), y=L["correct"].values.astype(int), v=v, fin=fin, g=itm["group"].astype(str).values, oh=np.array([TG[j][b][i] for i in ids]))
    rows = []
    for held in BENCH:
        h = D[held]; tr_b = [x for x in BENCH if x != held]; n = len(h["y"]); tie = np.random.default_rng(12345).random(n)
        S = {"transfer_raw": probe(np.concatenate([D[x]["A"] for x in tr_b]), np.concatenate([D[x]["y"] for x in tr_b]), h["A"], nj),
             "transfer_removed": probe(np.concatenate([D[x]["Ar"] for x in tr_b]), np.concatenate([D[x]["y"] for x in tr_b]), h["Ar"], nj)}
        ind = np.zeros(n); ug = np.random.default_rng(0).permutation(np.unique(h["g"])); fo = {g: k % 5 for k, g in enumerate(ug)}; f = np.array([fo[g] for g in h["g"]])
        for k in range(5):
            ind[f == k] = probe(h["A"][f != k], h["y"][f != k], h["A"][f == k], nj)
        S["in_domain"] = ind; good = (h["v"] == ("1.0" if held != "judgebench" else "__none__"))
        def scores(idx):
            o, oh, fi, t = h["y"][idx], h["oh"][idx], h["fin"][idx], tie[idx]
            r = {k_: esc_acc(s[idx], o, oh, fi, t) for k_, s in S.items()}
            r["verdict_only"] = np.mean([esc_acc((np.where(good, 0, 1) + 0.5 * np.random.default_rng(s).random(n))[idx], o, oh, fi, t) for s in range(20)]); return r
        full = scores(np.arange(n)); gi = {x: np.where(h["g"] == x)[0] for x in np.unique(h["g"])}; ugs = np.array(list(gi)); rb = np.random.default_rng(7); B_ = []
        for _ in range(a.n_boot):
            s_ = scores(np.concatenate([gi[x] for x in rb.choice(ugs, len(ugs))])); B_.append([s_["transfer_removed"] - s_["verdict_only"], s_["transfer_removed"] - s_["transfer_raw"], s_["transfer_removed"] - s_["in_domain"]])
        B_ = np.array(B_) * 100; lo, hi = np.percentile(B_, 2.5, 0), np.percentile(B_, 97.5, 0); obs = [full["transfer_removed"] - full["verdict_only"], full["transfer_removed"] - full["transfer_raw"], full["transfer_removed"] - full["in_domain"]]
        row = dict(judge=j, held_out=held, random=(h["y"].mean() + 0.2 * (h["oh"].mean() - h["y"].mean())) * 100, **{k_: v_ * 100 for k_, v_ in full.items()},
                   **{f"auroc_{k_}": roc_auc_score(h["y"], s) for k_, s in S.items()})
        for nm, o_, l_, u_ in zip(["removed_minus_verdict", "removed_minus_raw", "removed_minus_in_domain"], obs, lo, hi):
            row[nm] = f"{o_*100:+.1f} [{l_:+.1f},{u_:+.1f}]"; row[nm + "_lo"] = l_
        rows.append(row); print(f"{j} held-out {held} done", flush=True)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, f"transfer_{j}.csv"), index=False); pd.set_option("display.width", 260)
    print(R[[c for c in R.columns if not c.endswith("_lo")]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
