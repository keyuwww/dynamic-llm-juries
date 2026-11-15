#!/usr/bin/env bash
# Run Step 1 for one judge on Modal, keeping the Mac awake, then download the results.
#   caffeinate -is   keeps the Mac from sleeping until this script ends (lid must stay open)
#   --detach         keeps the Modal jobs running even if the Mac does sleep or disconnect;
#                    each job saves its results on the Modal volume, and the fetch step below downloads them
# If the connection drops anyway, rerun only the fetch line once the jobs are done.
#
#   experiments/trust_read_think/run_judge.sh openai/gpt-oss-20b            # full run
#   experiments/trust_read_think/run_judge.sh openai/gpt-oss-20b --limit 4  # smoke test
set -euo pipefail
MODEL="${1:?usage: run_judge.sh <hf model id> [extra step1 args]}"
shift
cd "$(dirname "$0")/../.."
SMOKE=""
[[ " $* " == *" --limit "* ]] && SMOKE="--smoke"
caffeinate -is bash -c "
  modal run --detach experiments/trust_read_think/step1.py::main --model '$MODEL' $* &&
  modal run experiments/trust_read_think/step1.py::fetch --model '$MODEL' $SMOKE
"
