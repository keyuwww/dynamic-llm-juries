#!/bin/bash
# On a Cannon login node, from .../beyond_capability_steer/outer:  bash submit.sh [smoke]
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs out outcot
P="-p seas_gpu,gpu_requeue --requeue --constraint=h200|h100|a100"
DEP=""
if [ ! -f setup_done ]; then S=$(sbatch --parsable setup_outer.sh); echo "setup $S"; DEP="--dependency=afterok:$S"; fi
if [ "${1:-}" = smoke ]; then
  echo "smoke outer $(sbatch --parsable $P $DEP -J os_llama job_outer.sh llama3.1-8b mmlu 60)"
  echo "smoke cot $(sbatch --parsable $P $DEP -J cs_mistral job_cot.sh mistral-7b mmlu 20)"
  exit 0
fi
for J in llama3.1-8b qwen2.5-7b phi4-mini granite3.3-8b; do
  for B in mmlu math bbeh; do echo "outer $J $B $(sbatch --parsable $P $DEP -J o_${J}_$B job_outer.sh $J $B)"; done
done
declare -A CB=([llama3.1-8b]="mmlu math bbeh" [llama3.2-3b]="mmlu math bbeh" [phi4-mini]="mmlu math bbeh"
  [llama3.2-1b]="mmlu math bbeh" [mistral-7b]="mmlu math" [granite3.3-8b]="mmlu bbeh" [qwen2.5-7b]="mmlu bbeh" [qwen3.5-4b]="bbeh")
for J in "${!CB[@]}"; do echo "cot $J $(sbatch --parsable $P $DEP -J c_$J job_cot.sh $J "${CB[$J]}")"; done
squeue -u $USER -o "%.10i %.16j %.8T %.10M %.20R" | head -30
