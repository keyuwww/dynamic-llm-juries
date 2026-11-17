#!/bin/bash
# Local: copy code + inputs to Cannon over the open control socket and submit the 70B jobs.
#   1) you:  ssh -M -S ~/.ssh/cm-cannon -o ControlPersist=24h keyuwang@login.rc.fas.harvard.edu   (password + 2FA)
#   2) then: sh experiments/beyond_capability/azure/cannon_70b/sync_and_submit.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); BC=$(cd "$HERE/../.." && pwd)
R=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer/bc70b
SSH="ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes keyuwang@login.rc.fas.harvard.edu"
$SSH "mkdir -p $R/inputs $R/logs $R/out70b"
rsync -a -e "ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes" \
  "$BC/azure/pair_pipeline.py" "$BC/azure/dir_capture.py" "$BC/azure/vllm_solve.py" "$BC/azure/cot_vllm.py" \
  "$BC/azure/direct_local.py" "$HERE/setup_70b.sh" "$HERE/job_pair_70b.sh" "$HERE/job_vllm_70b.sh" "$HERE/submit_70b.sh" \
  keyuwang@login.rc.fas.harvard.edu:$R/
cd "$BC/inputs"
rsync -a -e "ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes" mmlu_full_items.jsonl.gz math_full_items.jsonl.gz bbeh_items.jsonl.gz \
  sm_mmlu_items.jsonl.gz sm_math_items.jsonl.gz sm_bbeh_items.jsonl.gz sm2_mmlu_items.jsonl.gz sm2_math_items.jsonl.gz \
  solveq_mmlu.jsonl solveq_math.jsonl solveq_bbeh.jsonl keyuwang@login.rc.fas.harvard.edu:$R/inputs/
$SSH "cd $R && bash submit_70b.sh"
