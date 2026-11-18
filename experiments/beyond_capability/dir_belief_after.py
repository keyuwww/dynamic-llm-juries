"""Belief vs correctness directions read AFTER the judge has reasoned (Nov 17), next to the snap verdict.

New capture roles (cannon_nano/capture_last.py, items from dir_items_after_<key>.jsonl.gz):
  JX  judge, thinking OFF: the usual grading prompt + the judge's own written explanation (its pool transcript, BBEH,
      condition none, first sample), read at the final "VERDICT:"
  JT  judge, thinking ON: the grading prompt + the whole thinking trace + the answer text (out/think_gen.jsonl), read at
      the final "VERDICT:"
Each is analysed with dir_belief.py's own code, intersected with the snap-verdict role J (and the solving role N) on the
same answers, so the comparison is on identical items.

  python3 experiments/beyond_capability/dir_belief_after.py --key qwen3.5-9b --tags main,neutral,after [--audited]
      -> out_dirs/belief_dirs_after_<key>[_audited].md
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dir_belief as db  # noqa: E402

db.NAMES.update({"JX": "judge after its written explanation (VERDICT:)", "JT": "judge after thinking (VERDICT:)"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--tags", required=True)
    ap.add_argument("--audited", action="store_true")
    a = ap.parse_args()
    db.AUDIT = a.audited
    parts = [db.load(a.key, t) for t in a.tags.split(",")]
    L = []
    for roles in (["J", "N", "JX"], ["J", "N", "JT"]):
        db.ROLES = roles
        L += [f"\n# Roles {', '.join(roles)}\n"] + db.run_bench(a.key, "bbeh", parts)
    out = HERE / "out_dirs" / f"belief_dirs_after_{a.key}{'_audited' if a.audited else ''}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("wrote", out)


if __name__ == "__main__":
    main()
