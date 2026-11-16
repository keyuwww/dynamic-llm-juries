#!/usr/bin/env python
"""What do the activations add beyond the verdict, and does removing the verdict direction make the probe transfer to a new benchmark?

Verdict direction (label-free): per benchmark, mean activation of finished items where the judge said verdict a minus where it said verdict b
(Correct vs Incorrect on BFF / Safety, A vs B on JudgeBench). 'Projected' activations have this direction removed (per benchmark).
Same probe, layer and training settings as the README (evaluate.train_probe). For each cheap judge:
  test 1 (within benchmark)  train the error probe on items with one verdict, test on items with the other, and the reverse; compared with
                             5-fold (grouped by question) inside each verdict group. Reported, no decision attached.
  test 2 (pre-registered)    leave one benchmark out: train on the other two benchmarks, score the held-out one, with and without projection.
                             KILL unless projected AUROC >= 0.60 on at least 2 of the 3 held-out benchmarks.
Also: accuracy with 20% escalated (unfinished first) for the held-out probes, the verdict-only rule (random among items the judge marked
'good'; JudgeBench: random) and random, with the README's stronger judges (targets/strong_judge_correct.json).
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH


def project_out(X, verdict, fin):
    a, b = sorted(set(verdict[fin]))[:2]; d = X[fin & (verdict == a)].mean(0) - X[fin & (verdict == b)].mean(0); d = d / (np.linalg.norm(d) + 1e-8)
    return X - np.outer(X @ d, d)


def esc20(trust, ol, oh, fin, seed):
    n = len(ol); m = int(round(0.2 * n)); r = np.random.default_rng(seed).random(n); key = np.where(~fin, -1e9, trust) + 1e-9 * r
    esc = np.zeros(n, bool); esc[np.argsort(key, kind="stable")[:m]] = True; return np.where(esc, oh, ol).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="Qwen3.5-4B:16,Qwen3.5-9B:16,gpt-oss-20b:8"); ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json")
    ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_verdict_confound")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); rows1, rows2 = [], []
    for spec in a.judges.split(","):
        j, layer = spec.split(":"); layer = int(layer); D = {}
        for b in BENCH:
            _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"])
            L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]; layers = json.load(open(f"{p}_layers.json")); X = np.load(f"{p}_acts.npy", mmap_mode="r")[:, layers.index(layer)].astype(np.float32)
            v = L["verdict"].astype(str).values; fin = L["verdict"].notna().values
            D[b] = dict(X=X, Xp=project_out(X, v, fin), y=L["correct"].values.astype(int), v=v, fin=fin, g=itm["group"].astype(str).values, oh=np.array([TG[j][b][i] for i in ids]))
        for b in BENCH:                                                            # test 1: across verdict groups within a benchmark
            d = D[b]; vs = sorted(set(d["v"][d["fin"]]))[:2]
            for src, dst in [(vs[0], vs[1]), (vs[1], vs[0])]:
                ms, md = d["fin"] & (d["v"] == src), d["fin"] & (d["v"] == dst)
                if len(set(d["y"][md])) < 2: continue
                cross = np.mean([roc_auc_score(d["y"][md], predict(train_probe(d["X"][ms], d["y"][ms], seed=s), d["X"][md])) for s in range(a.seeds)])
                gi = d["g"][md]; ug = np.unique(gi); fo = {x: k % 5 for k, x in enumerate(np.random.default_rng(0).permutation(ug))}; f = np.array([fo[x] for x in gi]); Xd, yd = d["X"][md], d["y"][md]; oof = np.zeros(md.sum())
                for k in range(5):
                    te, tr = f == k, f != k
                    if len(set(yd[tr])) > 1: oof[te] = predict(train_probe(Xd[tr], yd[tr], seed=k), Xd[te])
                rows1.append(dict(judge=j, bench=b, train_verdict=src, test_verdict=dst, auroc_cross_verdict=cross, auroc_within_verdict=roc_auc_score(yd, oof), error_rate_test=1 - yd.mean()))
        for held in BENCH:                                                         # test 2: leave one benchmark out
            tr_b = [x for x in BENCH if x != held]; h = D[held]
            for kind in ["raw", "projected"]:
                key = "X" if kind == "raw" else "Xp"; Xtr = np.concatenate([D[x][key] for x in tr_b]); ytr = np.concatenate([D[x]["y"] for x in tr_b])
                S = [predict(train_probe(Xtr, ytr, seed=s), h[key]) for s in range(a.seeds)]
                rows2.append(dict(judge=j, held_out=held, probe=kind, auroc=np.mean([roc_auc_score(h["y"], s_) for s_ in S]), acc20=np.mean([esc20(s_, h["y"], h["oh"], h["fin"], k) for k, s_ in enumerate(S)]) * 100))
            vtr = np.where(h["v"] == ("1.0" if held != "judgebench" else "nan"), 0.0, 1.0)              # verdict-only rule: items marked 'good' first (JudgeBench: random)
            rows2.append(dict(judge=j, held_out=held, probe="verdict-only rule", auroc=np.nan, acc20=np.mean([esc20(vtr + np.random.default_rng(s).random(len(vtr)) * 0.5, h["y"], h["oh"], h["fin"], s) for s in range(200)]) * 100))
            rows2.append(dict(judge=j, held_out=held, probe="random", auroc=0.5, acc20=(h["y"].mean() + 0.2 * (h["oh"].mean() - h["y"].mean())) * 100))
        print(f"{j} done", flush=True)
    R1, R2 = pd.DataFrame(rows1), pd.DataFrame(rows2); R1.to_csv(os.path.join(a.out, "test1_cross_verdict.csv"), index=False); R2.to_csv(os.path.join(a.out, "test2_leave_one_out.csv"), index=False)
    pd.set_option("display.width", 220); print(R1.round(3).to_string(index=False)); print(R2.round(3).to_string(index=False))
    P = R2[R2.probe == "projected"]; ok = (P.auroc >= 0.60).groupby(P.judge).sum()
    print("\nPRE-REGISTERED KILL RULE (projected AUROC >= 0.60 on >= 2 of 3 held-out benchmarks), per judge:", dict(ok)); print("verdict:", "PASSED for " + ", ".join(ok[ok >= 2].index) if (ok >= 2).any() else "KILLED")


if __name__ == "__main__":
    main()
