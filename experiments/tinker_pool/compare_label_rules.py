#!/usr/bin/env python3
"""
Score one judge's BFF-Bench verdicts under three ways of turning the 3 human votes into a gold label:

  unanimous      all three votes Correct, or all three Incorrect (our default; 459 responses)
  nfl            No Free Labels' rule: at least 2 of 3 votes agree on Correct or Incorrect; a Not sure
                 majority or no majority is dropped (808 responses, matching their Table 1)
  ours_majority  run_judges.py --consensus majority: ignore Not sure, more Correct than Incorrect wins (878)

Reports accuracy and Cohen's kappa with a 95% bootstrap CI that resamples whole conversations, and splits
the result into unanimous vs split-vote responses.

Usage (repo root; needs a judgments.jsonl from run_judges.py --consensus majority, which covers all rules):
  uv run python experiments/tinker_pool/compare_label_rules.py \
      experiments/tinker_pool/bff_results_max4096_majority/judgments.jsonl --judge gpt-oss-120b
"""
import argparse, json
import numpy as np
from datasets import load_dataset

RULES = ["unanimous", "nfl", "ours_majority"]


def gold(votes, how):
    c, i, n = votes.count("correct"), votes.count("incorrect"), len(votes)
    if how == "unanimous":
        return 1 if c == n else 0 if i == n else None
    if how == "nfl":
        return 1 if c >= 2 else 0 if i >= 2 else None
    return 1 if c > i else 0 if i > c else None


def kappa(y, p):
    y, p = np.asarray(y), np.asarray(p)
    po = (y == p).mean()
    pe = y.mean() * p.mean() + (1 - y.mean()) * (1 - p.mean())
    return (po - pe) / (1 - pe)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("judgments")
    ap.add_argument("--judge", default="gpt-oss-120b")
    ap.add_argument("--condition", default="none")
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()

    verdict = {}
    for line in open(a.judgments):
        r = json.loads(line)
        if r["judge"] == a.judge and r["condition"] == a.condition:
            cid, t = r["item_id"].rsplit("-t", 1)
            verdict[(cid, int(t), r["examinee"])] = 1 if (r["vote_share"] or 0) > 0.5 else 0  # unparsed -> 0

    v = load_dataset("kensho/VERDICTS", split="train").to_pandas()
    v = v[v["dataset"].astype(str).str.lower() == "bffbench"]
    votes = {(str(cid), int(t), str(m)): [str(x).lower() for x in g["label"]]
             for (cid, t, m), g in v.groupby(["cid", "turn", "model"])}

    rng = np.random.default_rng(0)
    print(f"| Gold-label rule | n | Accuracy | κ | κ 95% CI | κ, unanimous part | κ, split-vote part (n) |")
    print("|---|---|---|---|---|---|---|")
    for how in RULES:
        rows = [(k[0], gold(vs, how), verdict[k], gold(vs, "unanimous") is not None)
                for k, vs in votes.items() if gold(vs, how) is not None and k in verdict]
        missing = sum(1 for k, vs in votes.items() if gold(vs, how) is not None and k not in verdict)
        y, p = [r[1] for r in rows], [r[2] for r in rows]
        by = {}
        for r in rows:
            by.setdefault(r[0], []).append(r)
        convs = list(by)
        ks = []
        for _ in range(a.boot):
            s = [r for c in rng.choice(convs, len(convs)) for r in by[c]]
            ks.append(kappa([r[1] for r in s], [r[2] for r in s]))
        split = [r for r in rows if not r[3]]
        ks_split = f"{kappa([r[1] for r in split], [r[2] for r in split]):.3f} ({len(split)})" if split else "–"
        una = [r for r in rows if r[3]]
        print(f"| {how} | {len(rows)}{f' ({missing} unjudged)' if missing else ''} | {np.mean(np.array(y) == np.array(p)):.3f} | "
              f"{kappa(y, p):.3f} | [{np.percentile(ks, 2.5):.3f}, {np.percentile(ks, 97.5):.3f}] | "
              f"{kappa([r[1] for r in una], [r[2] for r in una]):.3f} | {ks_split} |")


if __name__ == "__main__":
    main()
