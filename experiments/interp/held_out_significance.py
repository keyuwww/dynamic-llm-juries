#!/usr/bin/env python3
"""
Formal significance testing for the "best interior layer beats final answer" (kappa) effect,
on top of the project's existing held-out split-half validation.

The held-out method (see mech_interp_findings.html Figure 10) already corrects for the
multiple-comparisons / selection-bias problem of picking "the best of N layers": pick the
winning layer on one random half, score ONLY that fixed layer on the other half, repeat over
many splits, report the mean. What it has NOT produced so far (run ad hoc in chat, not saved)
is a paper-grade significance statement: a confidence interval and a p-value on the mean
held-out gap, and a check for whether the SAME layer wins reliably (not noise jumping around).

This script reruns that procedure with --n-splits (default 200, far more than the 20 used
informally before) and adds:
  - percentile bootstrap 95% CI on the mean held-out gap (resample splits, not items --
    the splits themselves are already randomized half/half item partitions)
  - a sign-permutation p-value: under H0 "no systematic gap", each split's gap is equally
    likely positive or negative; this is a two-sided exact/Monte-Carlo sign test against that null
  - the fraction of splits whose winning layer (on half A) falls within +-2 of the modal winning
    layer, as a direct "is it the same layer each time" stability statistic

Usage:
  python held_out_significance.py --pilot logit_lens_results/biggen_gpt-oss-120b/pilot_results.json \
      --pcn-field pcn_rubric --pred-field pred_rubric --n-splits 200 --seed 0
"""
import argparse
import json
import random
from collections import Counter
from pathlib import Path


def kappa(y1, y2):
    n = len(y1)
    po = sum(1 for a, b in zip(y1, y2) if a == b) / n
    p1, p2 = sum(y1) / n, sum(y2) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return 1.0 if pe >= 0.999999 else (po - pe) / (1 - pe)


def pred_from_pcn(pcn_val):
    return 1 if pcn_val >= 0.5 else 0


def final_pred_binary(pred_field_val, label_pos):
    if isinstance(pred_field_val, (int, bool)):
        return int(bool(pred_field_val))
    return 1 if str(pred_field_val) == label_pos else 0


def held_out_gap(items, pcn_field, pred_field, label_pos, n_splits, seed):
    gold = [it["gold"] for it in items]
    n_layers = len(items[0][pcn_field])
    final_preds = [final_pred_binary(it[pred_field], label_pos) for it in items]
    kappa_final_full = kappa(gold, final_preds)

    rng = random.Random(seed)
    idx = list(range(len(items)))
    gaps, winners = [], []
    for s in range(n_splits):
        rng.shuffle(idx)
        half = len(idx) // 2
        a_idx, b_idx = idx[:half], idx[half:]

        best_L, best_k = None, None
        gold_a = [gold[i] for i in a_idx]
        for L in range(n_layers):
            preds_a = [pred_from_pcn(items[i][pcn_field][L]) for i in a_idx]
            k = kappa(gold_a, preds_a)
            if best_k is None or k > best_k:
                best_k, best_L = k, L

        gold_b = [gold[i] for i in b_idx]
        preds_b_layer = [pred_from_pcn(items[i][pcn_field][best_L]) for i in b_idx]
        preds_b_final = [final_preds[i] for i in b_idx]
        k_layer_b = kappa(gold_b, preds_b_layer)
        k_final_b = kappa(gold_b, preds_b_final)
        gaps.append(k_layer_b - k_final_b)
        winners.append(best_L)
    return dict(kappa_final_full=kappa_final_full, gaps=gaps, winners=winners, n_layers=n_layers)


def bootstrap_ci(gaps, n_boot=10000, seed=0):
    rng = random.Random(seed)
    n = len(gaps)
    means = []
    for _ in range(n_boot):
        resample = [gaps[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return lo, hi


def sign_permutation_p(gaps, n_perm=100000, seed=0):
    """Two-sided Monte Carlo sign test: H0 = each split's gap sign is a fair coin flip."""
    rng = random.Random(seed)
    observed = sum(gaps) / len(gaps)
    n = len(gaps)
    mags = [abs(g) for g in gaps]
    count = 0
    for _ in range(n_perm):
        signed = sum(m if rng.random() < 0.5 else -m for m in mags)
        if abs(signed / n) >= abs(observed):
            count += 1
    return (count + 1) / (n_perm + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--pcn-field", default="pcn")
    ap.add_argument("--pred-field", default="pred")
    ap.add_argument("--label-pos", default="CORRECT")
    ap.add_argument("--n-splits", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    pilot = json.loads(Path(a.pilot).read_text())
    items = pilot["items"]
    items = [it for it in items if a.pcn_field in it and it[a.pcn_field] is not None]

    res = held_out_gap(items, a.pcn_field, a.pred_field, a.label_pos, a.n_splits, a.seed)
    gaps = res["gaps"]
    mean_gap = sum(gaps) / len(gaps)
    lo, hi = bootstrap_ci(gaps, seed=a.seed)
    p = sign_permutation_p(gaps, seed=a.seed)
    n_pos = sum(1 for g in gaps if g > 0)
    n_neg = sum(1 for g in gaps if g < 0)

    winner_counts = Counter(res["winners"])
    modal_layer, modal_count = winner_counts.most_common(1)[0]
    near_modal = sum(1 for w in res["winners"] if abs(w - modal_layer) <= 2)

    out = dict(
        pilot=a.pilot, pcn_field=a.pcn_field, pred_field=a.pred_field, n_items=len(items),
        n_layers=res["n_layers"], n_splits=a.n_splits,
        kappa_final_full_sample=res["kappa_final_full"],
        mean_held_out_gap=mean_gap, ci95=[lo, hi], sign_permutation_p=p,
        splits_positive=n_pos, splits_negative=n_neg, splits_total=len(gaps),
        modal_winning_layer=modal_layer, modal_layer_depth_pct=100 * modal_layer / (res["n_layers"] - 1),
        frac_splits_near_modal_layer=near_modal / len(gaps),
        all_gaps=gaps,
    )
    print(json.dumps({k: v for k, v in out.items() if k != "all_gaps"}, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=2))
        print(f"\nWritten to {a.out}")


if __name__ == "__main__":
    main()
