#!/usr/bin/env python
"""Escalate where the stronger judge would CHANGE the verdict for the better, not where the cheap judge looks wrong.

Verdicts are binary / pairwise, so escalating item i changes the system's correctness by  ok_h[i] - ok_l[i]  in {-1, 0, +1}
(+1: cheap wrong, strong right; -1: cheap right, strong wrong; 0: they agree). The best items to escalate are those with the largest expected
change E[ok_h - ok_l | activations] (the two-model deferral rule of Jitkrittum et al., NeurIPS 2023), not those with the lowest P(ok_l).

Probes, all on the cheap judge's last-token activations at the paper's fixed layer, the paper's training settings (evaluate.train_probe:
linear, squared loss, AdamW 1e-4, wd 0.01, batch 4, 10 epochs, output clipped to [0,1]), pooled over the three benchmarks, 5 folds grouped by
question, the SAME folds and seeds for every probe:
  error   target ok_l                      escalate lowest P(cheap right)          (the README's probe)
  gain    target (ok_h - ok_l + 1) / 2     escalate highest predicted gain          (PRIMARY new method, fixed before running)
  gain2   two probes, P(ok_h) - P(ok_l)    escalate highest difference              (secondary variant)
Baselines at the same budget: random, 10 reruns (share agreeing with the greedy verdict), and two oracles (cheap judge's errors first; gain first).
Unfinished answers are escalated first for every probe-based rule and for the reruns, as in the README.
Stronger judge = the README's: saved top-3 vote of the 8-judge pool without the cheap judge's own model (BFF, RewardBench-2), one other hosted judge (JudgeBench).
Primary comparison: gain vs error, accuracy at 20% escalated, per setting, mean over seeds, 95% paired bootstrap CI over questions. Run niced, few threads."""
import argparse, json, os, sys
import numpy as np, pandas as pd, torch
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH

RATES_REPORT = [0.1, 0.2, 0.3, 0.4]


def acc_at(trust, ok_l, ok_h, rate, tie):
    """accuracy when the round(rate * n) items with the LOWEST trust are escalated (ties broken by a fixed random vector)"""
    n = len(trust); m = int(round(rate * n)); order = np.lexsort((tie, trust)); esc = np.zeros(n, bool); esc[order[:m]] = True
    return np.where(esc, ok_h, ok_l).mean(), esc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", required=True); ap.add_argument("--high-jb", required=True); ap.add_argument("--layer", type=int, required=True); ap.add_argument("--results", default="local_results")
    ap.add_argument("--judgments-bff", default="../tinker_pool_8models_judgments_bff.jsonl"); ap.add_argument("--judgments-rb2", default="../tinker_pool_8models_judgments.jsonl")
    ap.add_argument("--seeds", type=int, default=5); ap.add_argument("--n-boot", type=int, default=1000); ap.add_argument("--threads", type=int, default=2); ap.add_argument("--out", default="results_gain_probe")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels")); from data import load_judgments; from audit import match_matrix
    A, OL, OH, G, B, PARSED, CONS = [], [], [], [], [], [], []
    for b in BENCH:
        _, p = load_run(a.results, a.low, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"])
        L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]; layers = json.load(open(f"{p}_layers.json"))
        A.append(np.load(f"{p}_acts.npy", mmap_mode="r")[:, layers.index(a.layer)].astype(np.float32)); OL.append(L["correct"].values.astype(int)); PARSED.append(L["verdict"].notna().values)
        G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(ids)
        _, ps = load_run(a.results, a.low, b, "uncertainty__n10_t0.7"); S = gen(f"{ps}_gen.jsonl"); gv = L["verdict"]; cons = np.zeros(len(ids)); pos = {i: k for k, i in enumerate(ids)}
        for iid, d in S.groupby("item_id"):                                       # 10 reruns: share of the samples that agree with the greedy verdict (README's 'consistency')
            if iid in pos and gv.iloc[pos[iid]] is not None and not (isinstance(gv.iloc[pos[iid]], float) and np.isnan(gv.iloc[pos[iid]])):
                cons[pos[iid]] = float((d["verdict"] == gv.iloc[pos[iid]]).sum()) / len(d)
        CONS.append(cons)
        if b == "judgebench":
            _, ph = load_run(a.results, a.high_jb, b, "uncertainty__n1_t0.0"); OH.append(gen(f"{ph}_gen.jsonl").set_index("item_id").loc[ids, "correct"].values.astype(int))
        else:
            d = load_judgments(a.judgments_bff if b == "bff" else a.judgments_rb2, b, condition="none"); C = match_matrix(d.Z, d.Y).astype(int); idx = {i: k for k, i in enumerate(d.item_ids)}
            sel = np.array([idx[i] for i in ids]); accx = C[sel].mean(0); accx[[k for k, n_ in enumerate(list(d.judge_names)) if n_.lower() == a.low.lower()]] = -1.0
            top3 = list(np.argsort(-accx)[:3]); OH.append(((d.Z[sel][:, top3].sum(1) * 2 > 3).astype(int) == d.Y[sel]).astype(int))
            print(f"[{b}] stronger panel: {[list(d.judge_names)[i] for i in top3]}", flush=True)
    A = np.concatenate(A); OL = np.concatenate(OL); OH = np.concatenate(OH); G = np.array(G); B = np.array(B); PARSED = np.concatenate(PARSED); CONS = np.concatenate(CONS)
    GAIN = (OH - OL + 1) / 2.0; tie = np.random.default_rng(12345).random(len(OL)); NEG = -1e6
    scores = {m: np.zeros((a.seeds, len(OL))) for m in ["error", "gain", "gain2"]}
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        for k in range(5):
            te = np.where(f == k)[0]; tr = np.where(f != k)[0]
            p_l = predict(train_probe(A[tr], OL[tr], seed=seed + k), A[te]); p_g = predict(train_probe(A[tr], GAIN[tr], seed=seed + k), A[te]); p_h = predict(train_probe(A[tr], OH[tr], seed=seed + k), A[te])
            scores["error"][seed, te] = p_l; scores["gain"][seed, te] = -p_g; scores["gain2"][seed, te] = -(p_h - p_l)     # trust = low means escalate
        print(f"seed {seed} done", flush=True)
    rows, comp = [], []
    for b in BENCH:
        m = B == b; ol, oh, pa, tb, g = OL[m], OH[m], PARSED[m], tie[m], G[m]; n = m.sum()
        def trust_of(s):                                                          # unfinished answers first, as in the README
            return np.where(pa, s, NEG)
        rules = {"random": None, "10 reruns": trust_of(CONS[m]), "oracle: cheap errors first": ol.astype(float), "oracle: gain first": -(oh - ol).astype(float)}
        res = {}
        for r_ in RATES_REPORT:
            res[("random", r_)] = [ol.mean() + r_ * (oh.mean() - ol.mean())]
            for nm, t in rules.items():
                if t is not None:
                    res[(nm, r_)] = [acc_at(t, ol, oh, r_, tb)[0]]
            for nm in scores:
                res[(nm, r_)] = [acc_at(trust_of(scores[nm][s_, m]), ol, oh, r_, tb)[0] for s_ in range(a.seeds)]
        for nm in ["random", "error", "gain", "gain2", "10 reruns", "oracle: cheap errors first", "oracle: gain first"]:
            row = dict(judge=a.low, bench=b, method=nm, n=int(n), cheap_alone=ol.mean() * 100, strong_alone=oh.mean() * 100)
            for r_ in RATES_REPORT:
                row[f"acc{int(r_ * 100)}"] = float(np.mean(res[(nm, r_)])) * 100
            if nm in scores:
                _, esc = acc_at(trust_of(scores[nm][0, m]), ol, oh, 0.2, tb); row["share_esc_changed"] = float((ol != oh)[esc].mean()) * 100
            rows.append(row)
        ug = np.unique(g); gi = {x: np.where(g == x)[0] for x in ug}; rb = np.random.default_rng(7); diffs = []
        for _ in range(a.n_boot):                                                 # paired bootstrap over questions: gain minus error at 20%, mean over seeds
            bi = np.concatenate([gi[x] for x in rb.choice(ug, len(ug))]); d_ = []
            for s_ in range(a.seeds):
                d_.append(acc_at(trust_of(scores["gain"][s_, m])[bi], ol[bi], oh[bi], 0.2, tb[bi])[0] - acc_at(trust_of(scores["error"][s_, m])[bi], ol[bi], oh[bi], 0.2, tb[bi])[0])
            diffs.append(np.mean(d_))
        obs = float(np.mean(res[("gain", 0.2)]) - np.mean(res[("error", 0.2)])) * 100
        comp.append(dict(judge=a.low, bench=b, gain_minus_error_at20=obs, ci_lo=np.percentile(diffs, 2.5) * 100, ci_hi=np.percentile(diffs, 97.5) * 100))
    R = pd.DataFrame(rows); C_ = pd.DataFrame(comp); R.to_csv(os.path.join(a.out, f"gain_probe_{a.low}.csv"), index=False); C_.to_csv(os.path.join(a.out, f"gain_vs_error_{a.low}.csv"), index=False)
    pd.set_option("display.width", 200); print(R.round(1).to_string(index=False)); print(C_.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
