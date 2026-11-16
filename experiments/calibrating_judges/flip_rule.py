#!/usr/bin/env python
"""Kill test, step 2: keep / flip / escalate with a calibrated probe, against escalate-only, at equal strong-judge budgets.

Verdicts are binary / pairwise, so for a FINISHED verdict with calibrated error probability p: keep -> error p, flip -> error 1-p (free),
escalate -> error ~ q (the stronger judge's error rate, estimated on the training fold; cheap activations do not predict it, see the diagnostic).
Unfinished answers (no verdict) cannot be kept or flipped: they are escalated first, as in the README.
Calibration uses TRAINING questions only: per test fold, the probe is trained on 85% of the training questions and an isotonic map from probe
output to P(wrong) is fitted on the other 15%; the probe is then retrained on all training questions and the map applied to the test fold.
Rules at budget B (share of items sent to the stronger judge):
  escalate_only   the README's rule: the B items with the lowest P(right), unfinished first; the rest keep their verdict
  flip_only       no escalation; flip every finished verdict with calibrated p > 0.5
  three_action    unfinished first; then escalate the finished items where escalation beats the better free action by the most
                  (min(p, 1-p) - q largest, only if > 0) up to B; every other finished item is flipped if p > 0.5, kept otherwise
Pre-registered kill rule: three_action must beat escalate_only with a 95% paired bootstrap CI (over questions) above 0 in at least 2 of the
9 settings at B = 20%; otherwise the idea is dropped. 10% and 30% are reported too. Same probe, folds, seeds and stronger judges as the README.
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, sys
import numpy as np, pandas as pd, torch
from sklearn.isotonic import IsotonicRegression
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH

BUDGETS = [0.1, 0.2, 0.3]


def apply_rule(rule, p, fin, ol, oh, q, B, tie):
    """accuracy of the final verdicts; p = calibrated P(cheap wrong) (finished items), fin = has a verdict"""
    n = len(ol); m = int(round(B * n)); esc = np.zeros(n, bool); flip = np.zeros(n, bool)
    unf = np.where(~fin)[0]; esc[unf[:m]] = True; left = m - min(m, len(unf))
    if rule == "escalate_only":
        cand = np.where(fin)[0]; cand = cand[np.lexsort((tie[cand], -p[cand]))]; esc[cand[:left]] = True        # highest P(wrong) = lowest P(right)
    elif rule == "flip_only":
        esc[:] = False; esc[unf] = False; flip = fin & (p > 0.5)
    elif rule == "three_action":
        benefit = np.minimum(p, 1 - p) - q; cand = np.where(fin & (benefit > 0))[0]; cand = cand[np.lexsort((tie[cand], -benefit[cand]))]
        esc[cand[:left]] = True; flip = fin & ~esc & (p > 0.5)
    ok = np.where(esc, oh, np.where(flip, 1 - ol, ol)); ok = np.where(~fin & ~esc, 0, ok)          # unfinished and not escalated: wrong
    return ok.mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="Qwen3.5-4B:16:Qwen3.5-9B,Qwen3.5-9B:16:gpt-oss-20b,gpt-oss-20b:8:Qwen3.5-9B"); ap.add_argument("--results", default="local_results")
    ap.add_argument("--targets", default="targets/strong_judge_correct.json", help="per cheap judge and benchmark: is its stronger judge (README definition) right on each item")
    ap.add_argument("--seeds", type=int, default=5); ap.add_argument("--n-boot", type=int, default=1000); ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_flip_rule")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True)
    TG = json.load(open(a.targets))
    rows, comp = [], []
    for spec in a.judges.split(","):
        j, layer, high_jb = spec.split(":"); layer = int(layer); A, OL, OH, G, B, FIN = [], [], [], [], [], []
        for b in BENCH:
            _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"])
            L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]; layers = json.load(open(f"{p}_layers.json"))
            A.append(np.load(f"{p}_acts.npy", mmap_mode="r")[:, layers.index(layer)].astype(np.float32)); OL.append(L["correct"].values.astype(int)); FIN.append(L["verdict"].notna().values)
            G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(ids)
            OH.append(np.array([TG[j][b][i] for i in ids], dtype=int))
        A = np.concatenate(A); OL = np.concatenate(OL); OH = np.concatenate(OH); G = np.array(G); B = np.array(B); FIN = np.concatenate(FIN)
        P = np.zeros((a.seeds, len(OL))); Q = np.zeros((a.seeds, len(OL))); tie = np.random.default_rng(12345).random(len(OL))
        for seed in range(a.seeds):
            rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
            for k in range(5):
                te = np.where(f == k)[0]; tr_all = np.where(f != k)[0]; tg = rng.permutation(np.unique(G[tr_all])); va_g = set(tg[:max(1, int(round(0.15 * len(tg))))])
                va = tr_all[np.isin(G[tr_all], list(va_g))]; tr = tr_all[~np.isin(G[tr_all], list(va_g))]
                iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1, increasing=False).fit(predict(train_probe(A[tr], OL[tr], seed=seed + k), A[va]), 1 - OL[va])   # probe output -> P(wrong)
                P[seed, te] = iso.predict(predict(train_probe(A[tr_all], OL[tr_all], seed=seed + k), A[te]))
                for b in BENCH:                                                    # stronger judge's error rate, per benchmark, from the training fold only
                    mt = tr_all[B[tr_all] == b]; Q[seed, te[B[te] == b]] = 1 - OH[mt].mean()
            print(f"{j} seed {seed} done", flush=True)
        for b in BENCH:
            m = B == b; ol, oh, fin, tb, g = OL[m], OH[m], FIN[m], tie[m], G[m]
            for Bd in BUDGETS:
                for rule in ["escalate_only", "flip_only", "three_action"]:
                    accs = [apply_rule(rule, P[s, m], fin, ol, oh, Q[s, m][0], Bd, tb) for s in range(a.seeds)]
                    rows.append(dict(judge=j, bench=b, budget=int(Bd * 100), rule=rule, acc=np.mean(accs) * 100, cheap_alone=ol.mean() * 100, strong_alone=oh.mean() * 100))
            ug = np.unique(g); gi = {x: np.where(g == x)[0] for x in ug}; rb = np.random.default_rng(7)
            for Bd in BUDGETS:
                obs = np.mean([apply_rule("three_action", P[s, m], fin, ol, oh, Q[s, m][0], Bd, tb) - apply_rule("escalate_only", P[s, m], fin, ol, oh, Q[s, m][0], Bd, tb) for s in range(a.seeds)])
                diffs = []
                for _ in range(a.n_boot):
                    bi = np.concatenate([gi[x] for x in rb.choice(ug, len(ug))])
                    diffs.append(np.mean([apply_rule("three_action", P[s, m][bi], fin[bi], ol[bi], oh[bi], Q[s, m][0], Bd, tb[bi]) - apply_rule("escalate_only", P[s, m][bi], fin[bi], ol[bi], oh[bi], Q[s, m][0], Bd, tb[bi]) for s in range(a.seeds)]))
                comp.append(dict(judge=j, bench=b, budget=int(Bd * 100), three_minus_escalate=obs * 100, ci_lo=np.percentile(diffs, 2.5) * 100, ci_hi=np.percentile(diffs, 97.5) * 100))
    R = pd.DataFrame(rows); C_ = pd.DataFrame(comp); R.to_csv(os.path.join(a.out, "flip_rule.csv"), index=False); C_.to_csv(os.path.join(a.out, "flip_rule_vs_escalate.csv"), index=False)
    pd.set_option("display.width", 220); print(R.pivot_table(index=["judge", "bench", "budget"], columns="rule", values="acc").round(1).to_string()); print(C_.round(2).to_string(index=False))
    wins = C_[(C_.budget == 20) & (C_.ci_lo > 0)]; print(f"\nPRE-REGISTERED KILL RULE (>= 2 of 9 settings with CI above 0 at 20%): {len(wins)} -> {'PASSED - not killed' if len(wins) >= 2 else 'KILLED'}")


if __name__ == "__main__":
    main()
