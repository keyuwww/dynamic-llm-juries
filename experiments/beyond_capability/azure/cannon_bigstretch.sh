#!/bin/bash
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-08:00
#SBATCH --exclude=holygpu8a31105
#SBATCH --constraint=a100|h100|h200
#SBATCH -o logs/bigstretch_%x_%j.out
# Stronger stretches (x21, x31, x51, x101) with the directions an earlier stretch_pipeline.py run already learned.
# Each half is steered with the direction from the other half, judge + random direction, as before.
# usage: sbatch -p seas_gpu,gpu_requeue --requeue -J <name> cannon_bigstretch.sh <hf model> <items> <out dir> <tag> [betas] [suffix]
#   -> <out dir>/steer_<tag>_<suffix>_h{1,2}.jsonl (defaults: betas 20,30,50,100, suffix big)
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load python/3.12.11-fasrc01
LC=/tmp/bc_${SLURM_JOB_ID}; mkdir -p $LC $PWD/home
export HF_HOME=$PWD/hf_cache HF_HUB_OFFLINE=1 HOME=$PWD/home XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source .venv/bin/activate
for h in h1 h2; do
  python dir_capture.py --phase steer --model "$1" --items "$2" --out "$3" --tag "$4_${6:-big}_$h" \
    --directions "$3/dirs_$4_$h.json" --steer-ids "$3/ids_$4_$h.json" --alphas=0 --betas=${5:-20,30,50,100}
done
echo "done: bigstretch"
