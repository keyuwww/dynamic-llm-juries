#!/usr/bin/env python3
"""
Step 1.2 analysis: does a judge that may answer UNSURE use it where it would otherwise be wrong?

Compares, per judge and condition, three ways of deciding which answers to send to a human:
  UNSURE      the judge said UNSURE in at least one of its 5 samples (judgments_unsure.jsonl)
  split vote  the 5 binary samples were not unanimous (judgments_real.jsonl)
  disagree    another judge's binary majority differs (best partner)
For each: share of answers escalated, and share of the judge's binary errors (majority verdict vs unanimous expert
label) that would be escalated. Also UNSURE use on answers the experts split on vs clear ones.

Output: results/unsure_summary.md, results/unsure.json

  python experiments/judge_confidence/unsure_analysis.py
"""
import collections, json

from jc_common import HERE, RAW


def main():
    bin_ = [json.loads(l) for l in open(RAW / "judgments_real.jsonl")]
    uns = [json.loads(l) for l in open(RAW / "judgments_unsure.jsonl")]
    B = {(r["judge"], r["item_id"], r["condition"]): r for r in bin_}
    judges = sorted({r["judge"] for r in uns})
    res, L = {}, ["# The UNSURE option (real BFF answers)", "",
                  "Same judges, same 5 samples, but the prompt allows \"VERDICT: UNSURE ... should be checked by a human "
                  "expert\". Errors = the judge's binary-prompt majority verdict vs the unanimous expert label. "
                  "Escalated = share of answers sent to a human by each rule.", ""]
    for cond in ("none", "human"):
        rows = [r for r in uns if r["condition"] == cond]
        if not rows:
            continue
        L += [f"## {'No reference' if cond == 'none' else 'With reference'}", "",
              "| Judge | Uses UNSURE (any sample) | Majority UNSURE | Escalated by UNSURE | Errors caught by UNSURE | "
              "Escalated by split vote | Errors caught by split vote | UNSURE on expert-split answers | on clear answers |",
              "|---|---|---|---|---|---|---|---|---|"]
        for j in judges:
            rs = [r for r in rows if r["judge"] == j]
            if not rs:
                continue
            anyu = lambda r: (r.get("unsure_share") or 0) > 0
            maj = lambda r: (r.get("unsure_share") or 0) > 0.5
            lab = [r for r in rs if r["gold_unanimous"] in (0, 1) and (j, r["item_id"], cond) in B
                   and B[(j, r["item_id"], cond)]["vote_share"] is not None]
            err = [r for r in lab if (B[(j, r["item_id"], cond)]["vote_share"] >= 0.5) != (r["gold_unanimous"] == 1)]
            split_b = lambda r: B[(j, r["item_id"], cond)]["vote_share"] not in (0.0, 1.0)
            split_items = [r for r in rs if r["gold_unanimous"] is None]
            clear = [r for r in rs if r["gold_unanimous"] is not None]
            row = dict(n=len(rs), use_any=sum(map(anyu, rs)) / len(rs), use_majority=sum(map(maj, rs)) / len(rs),
                       esc_unsure=sum(map(anyu, lab)) / len(lab), caught_unsure=sum(map(anyu, err)) / max(1, len(err)),
                       esc_split=sum(map(split_b, lab)) / len(lab), caught_split=sum(map(split_b, err)) / max(1, len(err)),
                       unsure_on_split=sum(map(anyu, split_items)) / max(1, len(split_items)),
                       unsure_on_clear=sum(map(anyu, clear)) / max(1, len(clear)), n_errors=len(err))
            # does offering UNSURE change the non-UNSURE verdicts' accuracy?
            dec = [r for r in lab if r["vote_share"] is not None]
            row["acc_decided_unsure_prompt"] = (sum((r["vote_share"] >= 0.5) == (r["gold_unanimous"] == 1) for r in dec)
                                                / max(1, len(dec)))
            row["acc_binary_prompt"] = 1 - len(err) / len(lab)
            res[f"{j}|{cond}"] = row
            f = lambda x: f"{100 * x:.0f}%"
            L.append(f"| {j} | {f(row['use_any'])} | {f(row['use_majority'])} | {f(row['esc_unsure'])} | "
                     f"{f(row['caught_unsure'])} of {len(err)} | {f(row['esc_split'])} | {f(row['caught_split'])} | "
                     f"{f(row['unsure_on_split'])} | {f(row['unsure_on_clear'])} |")
        L.append("")
        L += ["Accuracy on the answers the judge did decide (UNSURE prompt) vs the binary prompt on all answers:", ""]
        for j in judges:
            r = res.get(f"{j}|{cond}")
            if r:
                L.append(f"- {j}: {100 * r['acc_decided_unsure_prompt']:.0f}% vs {100 * r['acc_binary_prompt']:.0f}%")
        L.append("")
    L.append(f"Cost of the UNSURE runs: ${sum(r['cost'] for r in uns):.2f}.")
    (HERE / "results" / "unsure_summary.md").write_text("\n".join(L) + "\n")
    (HERE / "results" / "unsure.json").write_text(json.dumps(res, indent=1))
    print("\n".join(L))


if __name__ == "__main__":
    main()
