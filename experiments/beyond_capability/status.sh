#!/bin/sh
# Pull outputs from the Modal volume and print line counts (progress of every run).
cd "$(dirname "$0")/../.." && .venv/bin/modal run experiments/beyond_capability/modal_app.py --phase pull >/dev/null 2>&1
wc -l experiments/beyond_capability/out/*.jsonl | grep -v existing_rows
