#!/bin/bash
# Local: pull the outer-evaluation and repaired-reasoning outputs (no hidden states) over the control socket.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); BC=$(cd "$HERE/../.." && pwd)
R=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer/outer
E="ssh -S $HOME/.ssh/cm-cannon -o BatchMode=yes"
mkdir -p "$BC/out_outer" "$BC/out_cot_exact"
rsync -a -e "$E" --include='*/' --include='outer_*' --include='meta_*' --exclude='*' keyuwang@login.rc.fas.harvard.edu:$R/out/ "$BC/out_outer/"
rsync -a -e "$E" keyuwang@login.rc.fas.harvard.edu:$R/outcot/ "$BC/out_cot_exact/"
rsync -a -e "$E" keyuwang@login.rc.fas.harvard.edu:$R/logs/ "$HERE/logs/"
echo pulled
