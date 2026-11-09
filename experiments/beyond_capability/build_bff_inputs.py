"""BFF-Bench inputs (needs the HF datasets kensho/VERDICTS and kensho/BFFBench; run locally, no API calls).

  inputs/bff_items.jsonl      the 459 VERDICTS responses with a unanimous expert label (same items as the pool)
  inputs/bff_questions.jsonl  one row per (conversation, turn): the messages a solver sees and the expert
                              reference. Turn 2 is asked after the EXPERT's turn-1 answer, so "can the judge
                              solve this question" does not depend on its own turn-1 mistakes.

  .venv/bin/python experiments/beyond_capability/build_bff_inputs.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from data import bff_key_to_uid, load_bff, load_verdicts_items  # noqa: E402


def main():
    bff = load_bff()
    items, dropped = load_verdicts_items()
    key2uid = bff_key_to_uid(bff)
    with open(HERE / "inputs" / "bff_items.jsonl", "w") as f:
        for it in items:
            it = dict(it, uid=key2uid.get(str(it["qid"]), str(it["qid"])), turn=int(it["turn"]), human=int(it["human"]))
            f.write(json.dumps(it) + "\n")
    n = 0
    with open(HERE / "inputs" / "bff_questions.jsonl", "w") as f:
        for r in bff:
            for t in range(len(r["turns"])):
                msgs = []
                for u in range(t):
                    msgs += [{"role": "user", "content": r["turns"][u]}, {"role": "assistant", "content": r["refs"][u]}]
                msgs.append({"role": "user", "content": r["turns"][t]})
                f.write(json.dumps(dict(id=f"{r['uid']}|{t + 1}", uid=r["uid"], turn=t + 1, messages=msgs,
                                        ref=r["refs"][t] if t < len(r["refs"]) else None)) + "\n")
                n += 1
    print(f"{len(items)} items (dropped {dropped}); {n} questions")


if __name__ == "__main__":
    main()
