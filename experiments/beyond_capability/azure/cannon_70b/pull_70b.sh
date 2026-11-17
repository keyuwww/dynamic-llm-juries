#!/bin/bash
# Local: copy the 70B results back (not the hidden-state arrays) into out_allpairs/llama3.1-70b_<bench>/ and show job state.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); BC=$(cd "$HERE/../.." && pwd)
R=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer/bc70b
ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes keyuwang@login.rc.fas.harvard.edu "squeue -u keyuwang -o '%.10i %.12j %.8T %.10M %.20R'; tail -n 3 $R/logs/*.out 2>/dev/null | tail -n 40"
rsync -a --exclude "*.npy" --exclude "captured_*" -e "ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes" \
  keyuwang@login.rc.fas.harvard.edu:$R/out70b/ "$BC/out_allpairs/"
ls "$BC"/out_allpairs/llama3.1-70b_*/ 2>/dev/null
