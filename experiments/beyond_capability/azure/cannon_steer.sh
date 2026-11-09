#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 2-00:00
#SBATCH --array=0-4
#SBATCH --exclude=holygpu8a31105
#SBATCH -o logs/steer_%A_%a.out
# Steering while Qwen3.5-9B reasons (thinking on): one condition per array task, one GPU each. Resumes if resubmitted.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load python/3.12.11-fasrc01
export HF_HOME=$PWD/hf_cache HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# no home folder on this account: keep every cache (triton / torch kernels, pip, etc.) in scratch
mkdir -p $PWD/home $PWD/cache
# compiled-kernel caches on the node's local disk, one per job (several jobs sharing one on the network drive collide)
LC=/tmp/bc_${SLURM_JOB_ID}; mkdir -p $LC
export HOME=$PWD/home XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton TORCHINDUCTOR_CACHE_DIR=$LC/inductor
source .venv/bin/activate
CONDS=(none "shift:Jt:4" "shift:Jt:-4" "stretch:Jt:10" "shift:Rt:4")
c=${CONDS[$SLURM_ARRAY_TASK_ID]}
tag=$(echo "$c" | tr ':' '_')
nvidia-smi --query-gpu=name,memory.total --format=csv
python dir_capture.py --phase steergen --model Qwen/Qwen3.5-9B --items inputs/dir_items.jsonl.gz --out out --tag "$tag" \
  --edit "$c" --batch 4 --directions inputs/steer_think_dirs.json --steer-ids inputs/steer_think_ids.json
