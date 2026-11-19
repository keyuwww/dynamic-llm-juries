#!/bin/bash
# Local: copy code + inputs to Cannon over the open control socket (ssh -M -S ~/.ssh/cm-cannon ...).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); BC=$(cd "$HERE/../.." && pwd)
R=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer/outer
SSH="ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes keyuwang@login.rc.fas.harvard.edu"
$SSH "mkdir -p $R/inputs $R/logs $R/out $R/outcot"
rsync -a -e "ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes" "$BC/azure/pair_pipeline.py" "$BC/azure/dir_capture.py" \
  "$BC/azure/outer_pipeline.py" "$BC/azure/cot_exact.py" "$HERE/"*.sh "$HERE/PROTOCOL.md" keyuwang@login.rc.fas.harvard.edu:$R/
cd "$BC/inputs"
rsync -a -e "ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes" mmlu_full_items.jsonl.gz math_full_items.jsonl.gz bbeh_items.jsonl.gz \
  sm_mmlu_items.jsonl.gz sm_math_items.jsonl.gz sm_bbeh_items.jsonl.gz sm2_mmlu_items.jsonl.gz sm2_math_items.jsonl.gz \
  keyuwang@login.rc.fas.harvard.edu:$R/inputs/
echo synced
