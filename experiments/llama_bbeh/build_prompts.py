"""Build the exact BBEH solve + judge prompts the Tinker pool saw, for a model run on Modal.

Solve prompts: copied from the pool's own answers.jsonl `messages` (same question + BBEH suffix).
Judge prompts: the same 920 (item, examinee) candidates the 8 pool judges graded, rebuilt with
run_judges.bbeh_items (same seed, 2 per item) and run_judges.build_prompt (condition = none).

Writes experiments/llama_bbeh/prompts.jsonl. No API calls, no GPU.
  python3 experiments/llama_bbeh/build_prompts.py
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / "tinker_pool"
sys.path.insert(0, str(POOL))
import run_judges  # noqa: E402  (imports only stdlib + local modules at import time)

ANS = POOL / "bbeh_results" / "answers.jsonl"
JUD = POOL / "bbeh_results" / "judgments.jsonl"


class Rows:  # read-only stand-in for JsonlCache (never opens the file for writing)
    def __init__(self, path):
        self.rows = {}
        for line in open(path):
            if line.strip():
                r = json.loads(line)
                self.rows[r["cache_key"]] = r


def main():
    answers = Rows(ANS)
    out = []
    # 1. solve prompts: one per item, identical to what every pool model got
    seen = set()
    for r in sorted(answers.rows.values(), key=lambda r: r["item"]):
        if r["item"] in seen:
            continue
        seen.add(r["item"])
        out.append(dict(kind="solve", id=r["item"], task=r["task"], target=r["target"],
                        messages=r["messages"]))
    # 2. judge prompts: same candidates as the pool (seed 0, 2 per item)
    a = SimpleNamespace(bbeh_path=None, seed=0, per_item=2)
    items = run_judges.bbeh_items(a, answers)
    for it in items:
        prompt = run_judges.build_prompt("bbeh", it, "none", None)
        out.append(dict(kind="judge", id=it["id"], uid=it["uid"], examinee=it["examinee"], gold=it["gold"],
                        messages=[{"role": "user", "content": prompt}]))

    # sanity check: rebuilt candidates must be exactly the ones the pool judged
    pool_ids = {json.loads(l)["item_id"] for l in open(JUD) if '"condition": "none"' in l}
    ours = {o["id"] for o in out if o["kind"] == "judge"}
    assert ours == pool_ids, f"candidate mismatch: {len(ours ^ pool_ids)} differ"

    dest = HERE / "prompts.jsonl"
    with open(dest, "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    n_s = sum(o["kind"] == "solve" for o in out)
    print(f"wrote {dest.relative_to(HERE.parent.parent)}: {n_s} solve + {len(out) - n_s} judge prompts "
          f"(candidates match the pool's {len(pool_ids)})")


if __name__ == "__main__":
    main()
