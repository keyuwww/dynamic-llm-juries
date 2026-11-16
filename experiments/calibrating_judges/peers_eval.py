#!/usr/bin/env python
"""Escalate with more evidence instead of a bigger judge: re-judge with other systems' answers to the same question shown (prompt 'peers').

Compares, for one cheap judge on BFF:
  cheap alone                      the judge's normal verdict
  re-judged with peers (all)       every item re-judged with 3 other systems' answers shown
  shared mistakes fixed            items where the cheap judge AND the stronger top-3 jury are both wrong: share the peer re-judge gets right
  correct verdicts broken          items the cheap judge got right: share the peer re-judge gets wrong
  escalate 20% -> stronger jury    README cascade (the README probe chooses the 20%)
  escalate 20% -> peer re-judge    same 20%, but their verdict comes from the peer re-judge (no bigger judge)
Pre-registered kill rule: the peer re-judge fixes fewer than 25% of the shared mistakes -> dropped. Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os
import numpy as np, pandas as pd, torch
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", default="Qwen3.5-4B"); ap.add_argument("--layer", type=int, default=16); ap.add_argument("--results", default="local_results")
    ap.add_argument("--targets", default="targets/strong_judge_correct.json"); ap.add_argument("--seeds", type=int, default=5); ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_peers")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets))
    A, Y, G, B, FIN, IDS = [], [], [], [], [], []                                  # the README probe, to pick the 20% (pooled training, 5 folds by question)
    for b in BENCH:
        _, p = load_run(a.results, a.low, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]
        layers = json.load(open(f"{p}_layers.json")); A.append(np.load(f"{p}_acts.npy", mmap_mode="r")[:, layers.index(a.layer)].astype(np.float32))
        Y.append(L["correct"].values.astype(int)); FIN.append(L["verdict"].notna().values); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(itm); IDS += list(itm["item_id"])
    A = np.concatenate(A); Y = np.concatenate(Y); FIN = np.concatenate(FIN); G = np.array(G); B = np.array(B); IDS = np.array(IDS); m = B == "bff"
    S = np.zeros((a.seeds, len(Y)))
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        for k in range(5):
            te, tr = np.where(f == k)[0], np.where(f != k)[0]; S[seed, te] = predict(train_probe(A[tr], Y[tr], seed=seed + k), A[te])
    ids = IDS[m]; ol = Y[m]; fin = FIN[m]; oh = np.array([TG[a.low]["bff"][i] for i in ids])
    _, pp = load_run(a.results, a.low, "bff", "peers__n1_t0.0"); P = gen(f"{pp}_gen.jsonl").set_index("item_id").loc[ids]
    op = P["correct"].values.astype(int); n = len(ids); k20 = int(round(0.2 * n))
    shared = (ol == 0) & (oh == 0); right = ol == 1
    res = dict(n=n, cheap_alone=ol.mean() * 100, strong_jury_alone=oh.mean() * 100, peers_rejudge_all=op.mean() * 100, peers_parsed=float(P["verdict"].notna().mean()) * 100,
               shared_mistakes=int(shared.sum()), shared_fixed_by_peers=op[shared].mean() * 100, cheap_errors=int((ol == 0).sum()), cheap_errors_fixed_by_peers=op[ol == 0].mean() * 100,
               cheap_errors_fixed_by_jury=oh[ol == 0].mean() * 100, correct_broken_by_peers=(1 - op[right]).mean() * 100)
    acc_j, acc_p = [], []
    for s in range(a.seeds):
        t = np.where(fin, S[s, m], -1e9) + 1e-9 * np.random.default_rng(1).random(n); esc = np.zeros(n, bool); esc[np.argsort(t, kind="stable")[:k20]] = True
        acc_j.append(np.where(esc, oh, ol).mean()); acc_p.append(np.where(esc, op, ol).mean())
    res.update(escalate20_to_jury=np.mean(acc_j) * 100, escalate20_to_peers_rejudge=np.mean(acc_p) * 100)
    pd.DataFrame([res]).to_csv(os.path.join(a.out, f"peers_{a.low}.csv"), index=False)
    for k, v in res.items(): print(f"{k:<32} {v:.1f}" if isinstance(v, float) else f"{k:<32} {v}")
    print("\nPRE-REGISTERED KILL RULE (peer re-judge fixes < 25% of shared mistakes):", "KILLED" if res["shared_fixed_by_peers"] < 25 else "PASSED - not killed")


if __name__ == "__main__":
    main()
