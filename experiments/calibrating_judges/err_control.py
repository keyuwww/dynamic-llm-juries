#!/usr/bin/env python
"""Control for err_eval.py, same cost (2 judge runs): is the warning sign from the WORDING, or would any second run disagree in the same places?
Second run = sample 0 of the existing 10 reruns at temperature 0.7 with the normal question (prompt 'uncertainty'). Same escalation rule as
err_eval.py ('disagreement first, then verdict-only rule', unfinished first), same stronger judge. Pre-registered: the wording version must beat
the resample version at 20% in at least 3 of the 4 settings, or the wording adds nothing beyond a second sample. Runs on Modal CPU."""
import argparse, json, os
import numpy as np, pandas as pd
from cascade_eval import gen, load_run
from err_eval import esc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json"); ap.add_argument("--out", default="results_err")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); rows = []
    for j in ["Qwen3.5-4B", "Qwen3.5-9B"]:
        for b in ["bff", "rb2safety"]:
            _, pa = load_run(a.results, j, b, "uncertainty__n1_t0.0"); _, pb = load_run(a.results, j, b, "error__n1_t0.0"); _, ps = load_run(a.results, j, b, "uncertainty__n10_t0.7")
            A = gen(f"{pa}_gen.jsonl").set_index("item_id"); ids = list(A.index); B = gen(f"{pb}_gen.jsonl").set_index("item_id").loc[ids]
            S = gen(f"{ps}_gen.jsonl"); S = S[S["sample"] == 0].set_index("item_id").loc[ids]
            ol = A["correct"].values.astype(int); oh = np.array([TG[j][b][i] for i in ids]); fin = A["verdict"].notna().values; fine = (A["verdict"].values == 1.0)
            def dis_with(X):
                fx = X["verdict"].notna().values; return ~(fin & fx) | (A["verdict"].values != X["verdict"].values)
            dB, dS = dis_with(B), dis_with(S)
            rule = lambda d: (lambda r: np.where(d, 0, 2) + np.where(fine, 0, 1) + 0.5 * r.random(len(ol)))
            rows.append(dict(judge=j, bench=b, disagree_wording=dB.mean() * 100, disagree_resample=dS.mean() * 100,
                             cheap_wrong_when_disagree_wording=(1 - ol[dB]).mean() * 100, cheap_wrong_when_disagree_resample=(1 - ol[dS]).mean() * 100,
                             esc_wording=esc(rule(dB), ol, oh, fin), esc_resample=esc(rule(dS), ol, oh, fin), esc_verdict_only=esc(lambda r: np.where(fine, 0, 1) + 0.5 * r.random(len(ol)), ol, oh, fin)))
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "err_control.csv"), index=False); pd.set_option("display.width", 250); print(R.round(2).T.to_string())
    w = int((R.esc_wording > R.esc_resample).sum()); print(f"\nWORDING BEATS A SECOND SAMPLE (>= 3 of 4): {w} -> {'PASS' if w >= 3 else 'FAIL'}")


if __name__ == "__main__":
    main()
