#!/usr/bin/env python
"""Ask the same question the other way round: 'is the response correct?' (A, prompt 'uncertainty') vs 'does the response contain an error?' (B, prompt 'error').
Same judge, same items, same instructions apart from the question; greedy decoding. Per cheap judge (Qwen3.5-4B, Qwen3.5-9B) and benchmark (BFF, Safety):
  acc_A, acc_B                  verdict accuracy against the human labels (unfinished answers count as wrong)
  disagree                      share of items where A and B give different verdicts (an unfinished answer counts as disagreeing)
  err_corr_A_B                  correlation of the two wordings' mistakes (same judge)
  err_corr_models               correlation of the two judges' mistakes under wording A (different models), for comparison
  accuracy with 20% escalated   to the README's stronger judge, choosing the 20% by:
      random | verdict-only rule (random among items the judge marked 'correct' under A) | disagreement first (then random) |
      disagreement first, then verdict-only rule | README probe (fixed numbers from the README, 5-seed means)
Pre-registered pass bars (fixed before the results):
  Q1 different mistakes: err_corr_A_B < err_corr_models in at least 3 of the 4 settings
  Q2 useful warning sign: 'disagreement first, then verdict-only rule' beats BOTH random and the verdict-only rule at 20% in at least 2 of 4 settings
  Q3 better wording: acc_B > acc_A by at least 1 point in at least 3 of 4 settings
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os
import numpy as np, pandas as pd
from cascade_eval import gen, load_run

README_PROBE = {("Qwen3.5-4B", "bff"): 81.5, ("Qwen3.5-4B", "rb2safety"): 85.8, ("Qwen3.5-9B", "bff"): 82.3, ("Qwen3.5-9B", "rb2safety"): 88.7}


def esc(order_key, ol, oh, fin, n_rep=200):
    """order_key(rng) -> keys (lower escalates first); unfinished answers always first; returns mean accuracy at 20%"""
    n = len(ol); m = int(round(0.2 * n)); accs = []
    for s in range(n_rep):
        r = np.random.default_rng(s); k = np.where(~fin, -1e9, order_key(r)); e = np.zeros(n, bool); e[np.argsort(k, kind="stable")[:m]] = True
        accs.append(np.where(e, oh, ol).mean())
    return float(np.mean(accs)) * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json"); ap.add_argument("--out", default="results_err")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); rows = []; D = {}
    for j in ["Qwen3.5-4B", "Qwen3.5-9B"]:
        for b in ["bff", "rb2safety"]:
            _, pa = load_run(a.results, j, b, "uncertainty__n1_t0.0"); _, pb = load_run(a.results, j, b, "error__n1_t0.0")
            A = gen(f"{pa}_gen.jsonl").set_index("item_id"); B = gen(f"{pb}_gen.jsonl").set_index("item_id").loc[A.index]; D[(j, b)] = (A, B)
    for j in ["Qwen3.5-4B", "Qwen3.5-9B"]:
        for b in ["bff", "rb2safety"]:
            A, B = D[(j, b)]; ids = list(A.index); ol = A["correct"].values.astype(int); ob = B["correct"].values.astype(int); oh = np.array([TG[j][b][i] for i in ids])
            fa, fb = A["verdict"].notna().values, B["verdict"].notna().values; va, vb = A["verdict"].values, B["verdict"].values
            dis = ~(fa & fb) | (va != vb); fin = fa; fine = (va == 1.0)
            other = "Qwen3.5-9B" if j == "Qwen3.5-4B" else "Qwen3.5-4B"; O = D[(other, b)][0].loc[ids]; oo = O["correct"].values.astype(int)
            rnd = (ol.mean() + 0.2 * (oh.mean() - ol.mean())) * 100
            rows.append(dict(judge=j, bench=b, n=len(ids), acc_A=ol.mean() * 100, acc_B=ob.mean() * 100, parsed_B=fb.mean() * 100, disagree=dis.mean() * 100,
                             A_right_when_disagree=ol[dis].mean() * 100, B_right_when_disagree=ob[dis].mean() * 100,
                             err_corr_A_B=np.corrcoef(1 - ol, 1 - ob)[0, 1], err_corr_models=np.corrcoef(1 - ol, 1 - oo)[0, 1],
                             esc_random=rnd, esc_verdict_only=esc(lambda r: np.where(fine, 0, 1) + 0.5 * r.random(len(ol)), ol, oh, fin),
                             esc_disagree_then_random=esc(lambda r: np.where(dis, 0, 1) + 0.5 * r.random(len(ol)), ol, oh, fin),
                             esc_disagree_then_verdict=esc(lambda r: np.where(dis, 0, 2) + np.where(fine, 0, 1) + 0.5 * r.random(len(ol)), ol, oh, fin),
                             esc_readme_probe=README_PROBE[(j, b)]))
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "err_results.csv"), index=False); pd.set_option("display.width", 250); print(R.round(2).T.to_string())
    q1 = int((R.err_corr_A_B < R.err_corr_models).sum()); q2 = int(((R.esc_disagree_then_verdict > R.esc_random) & (R.esc_disagree_then_verdict > R.esc_verdict_only)).sum()); q3 = int((R.acc_B - R.acc_A >= 1).sum())
    print(f"\nQ1 different mistakes (>= 3 of 4): {q1} -> {'PASS' if q1 >= 3 else 'FAIL'}\nQ2 useful warning sign (>= 2 of 4): {q2} -> {'PASS' if q2 >= 2 else 'FAIL'}\nQ3 better wording (>= 3 of 4): {q3} -> {'PASS' if q3 >= 3 else 'FAIL'}")


if __name__ == "__main__":
    main()
