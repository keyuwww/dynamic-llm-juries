"""Does pushing the judge's belief direction while it reasons change its spoken verdicts, selectively?

Reads cannon_belief/out_steer/<cond>_L14-26.jsonl (cannon_belief/steer.py: Qwen3.5-9B, thinking off, greedy, push at
layers 14-26 on every token, each item with a direction fitted on the other half of its benchmark's questions).

For each condition and item group (wrong & believed >= 4/7, wrong & never reached, correct):
  accept rate   share of judgments ending in VERDICT: CORRECT (an output with no verdict counts as not accepting)
  broke         share of outputs that never finished (looped to the 8,192-token pilot cap) or gave no verdict
  change        paired difference from 'none' on the same items, 95% interval resampling whole questions
Selectivity = change for wrong & believed minus change for correct (negative = removes believed errors more than it
hurts right answers).

  python3 experiments/anchoring_early_answer/belief_steer_analysis.py
"""
import collections
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / "cannon_belief" / "out_steer"
CONDS = ["none", "belief:-4", "belief:-6", "belief_orth:-6", "correct:-6", "random:-6", "belief:4",
         # SCALE: each item's own position along the direction (around the fitting half's mean) times lam
         "belief*0", "belief*-2", "belief*-5", "belief*5", "belief_orth*-5", "correct*-5", "random*-5"]
GROUPS = ["wrong_believed", "wrong_never", "correct"]
NAMES = {"wrong_believed": "wrong, believed", "wrong_never": "wrong, never reached", "correct": "correct"}


def load(cond):
    p = SRC / f"{cond.replace(':', '_').replace('*', '_x')}_L14-26.jsonl"
    return {r["aid"]: r for r in map(json.loads, open(p))} if p.exists() else {}


def boot(keys_by_q, f, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    qs = list(keys_by_q)
    vals = [f([k for q in rng.choice(qs, len(qs)) for k in keys_by_q[q]]) for _ in range(n)]
    return np.nanpercentile(vals, [2.5, 97.5])


def main():
    D = {c: load(c) for c in CONDS}
    base = D["none"]
    L = ["# Belief steering while the judge reasons (Qwen3.5-9B, layers 14-26, held-out directions)\n",
         "Accept rate = share ending in VERDICT: CORRECT. 'Broke' = looped without finishing (8,192-token cap) or gave "
         "no verdict; it counts as not accepting. Changes are paired against 'none' on the same items; 95% intervals "
         "resample whole questions. Push sizes are per layer, in units of the belief projection's spread at that layer; "
         "every direction gets the same push length. 'x*lam' rows SCALE instead: each item's own position along the direction "
         "(around its average) is multiplied by lam (0 = removed, -5 = reversed and stretched, 5 = stretched), so the "
         "push differs by item; a random direction varies less across items, so its scaled push is smaller.\n"]
    for bench in ("rb2math", "bff", "both"):
        L.append(f"\n## {bench}\n")
        L.append("| condition | " + " | ".join(f"{NAMES[g]}" for g in GROUPS) + " | selectivity | broke |")
        L.append("|---|---|---|---|---|---|")
        for c in CONDS:
            R = D[c]
            if not R:
                L.append(f"| {c} | (not run yet) |||||")
                continue
            ks = [k for k in R if k in base and (bench == "both" or R[k]["bench"] == bench)]
            acc = lambda r: int(r["verdict"] == 1)
            cells, deltas = [], {}
            for g in GROUPS:
                kg = [k for k in ks if R[k]["group"] == g]
                if not kg:
                    cells.append("–")
                    continue
                a = np.mean([acc(R[k]) for k in kg])
                if c == "none":
                    cells.append(f"{100 * a:.0f}% (n={len(kg)})")
                    continue
                byq = collections.defaultdict(list)
                for k in kg:
                    byq[R[k]["q"]].append(k)
                d = lambda S: np.mean([acc(R[k]) - acc(base[k]) for k in S])
                lo, hi = boot(byq, d)
                deltas[g] = kg
                cells.append(f"{100 * a:.0f}% ({100 * d(kg):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}])")
            sel = "–"
            if c != "none" and "wrong_believed" in deltas and "correct" in deltas:
                kb, kc = deltas["wrong_believed"], deltas["correct"]
                byq = collections.defaultdict(list)
                for k in kb + kc:
                    byq[R[k]["q"]].append(k)

                def s(S):
                    b = [acc(R[k]) - acc(base[k]) for k in S if R[k]["group"] == "wrong_believed"]
                    cc = [acc(R[k]) - acc(base[k]) for k in S if R[k]["group"] == "correct"]
                    return np.mean(b) - np.mean(cc) if b and cc else np.nan
                lo, hi = boot(byq, s)
                sel = f"{100 * s(kb + kc):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}]"
            broke = np.mean([(not R[k]["clean"]) or R[k]["verdict"] is None for k in ks])
            L.append(f"| {c} | " + " | ".join(cells) + f" | {sel} | {100 * broke:.0f}% |")
    out = HERE / "out" / "belief_steering.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
