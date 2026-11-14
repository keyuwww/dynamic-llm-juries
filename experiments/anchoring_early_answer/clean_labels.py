"""RB2-Math label audit (Nov 13): "wrong" candidates whose final answer has the same value as the right one.

RewardBench 2 Math marks some answers wrong although they reach the reference value, written differently
(476,000,000 vs 476,252,000 eV; 9 L vs 9.02 L; 4.20 x 10^11 vs "420" in units of 10^9). A judge that accepts them
is not anchoring. tinker_jobs.py --phase audit asks GLM-5.3-Flash (the answer matcher) whether each wrong candidate's
final answer is the SAME as each right candidate's for that question -> out/label_audit_glm5.3-flash.jsonl.

analyze.py --clean and belief.py --clean drop these candidates from every wrong-answer table.

  python3 experiments/anchoring_early_answer/clean_labels.py     (prints the audit summary)
"""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "out" / "label_audit_glm5.3-flash.jsonl"


def same_value_items(path=AUDIT):
    """Wrong RB2-Math item_ids that GLM judged SAME as a right candidate of the same question."""
    if not path.exists():
        raise SystemExit(f"{path} is missing: run tinker_jobs.py --phase audit first (modal_app.py::run)")
    out = set()
    for line in open(path):
        r = json.loads(line)
        if r["verdict"] == "SAME":
            out.add(r["cache_key"].split("|")[1])
    return out


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(AUDIT)]
    c = collections.Counter(r["verdict"] for r in rows)
    wrong = {r["cache_key"].split("|")[1] for r in rows}
    print(f"{len(rows)} wrong-vs-right pairs: {dict(c)}")
    print(f"{len(same_value_items())} of {len(wrong)} wrong RB2-Math candidates reach the right value")
