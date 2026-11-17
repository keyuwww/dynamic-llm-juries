#!/bin/bash
# Run on a Cannon login node from .../beyond_capability_steer/bc70b:  bash submit_70b.sh
# Submits: setup (weights + env) -> 3 pair jobs (one per benchmark, 2 GPUs >= 80 GB) and 1 vLLM job (2 x H200).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs out70b
P="-p seas_gpu,gpu_requeue --requeue --constraint=h200|h100|a100"
S=$(sbatch --parsable setup_70b.sh); echo "setup $S"
for B in mmlu math bbeh; do
  echo "pair $B $(sbatch --parsable $P --dependency=afterok:$S -J p70_$B job_pair_70b.sh $B)"
done
# vLLM at a 32K window needs > 2 x 80 GB for a 70B model: H200 (141 GB) only
echo "vllm $(sbatch --parsable -p seas_gpu,gpu_requeue --requeue --constraint=h200 --dependency=afterok:$S -J v70 job_vllm_70b.sh)"
squeue -u $USER -o "%.10i %.12j %.8T %.10M %.20R" | head
