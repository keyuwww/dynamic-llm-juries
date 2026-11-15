#!/usr/bin/env python3
"""One-off repair: think files fetched from the Modal volume before the item_ids fix carry wrong ids. Rows are in item
order (the same order as the prompts), so relabel them by position.  usage: repair_ids.py <judge folder name> [--smoke]"""
import json, sys
from pathlib import Path
ITEMS = Path(__file__).resolve().parent / "results" / "raw" / "step1"
judge, tag = sys.argv[1], ("smoke_" if "--smoke" in sys.argv else "")
items = [json.loads(l) for f in ("items.jsonl", "items_factuality.jsonl") for l in open(ITEMS / f)]
for b in ("safety", "focus", "math", "bff", "factuality"):
    p = ITEMS / judge / f"{tag}{b}_think.jsonl"
    if not p.exists():
        continue
    rows = [json.loads(l) for l in open(p)]
    ids = [it["id"] for it in items if it["bench"] == b]
    ids = ids[:len(rows)] if tag else ids
    assert len(ids) == len(rows), (b, len(ids), len(rows))
    with open(p, "w") as fh:
        for i, r in zip(ids, rows):
            r["id"] = i
            fh.write(json.dumps(r) + "\n")
    print("relabelled", p.name, len(rows))
