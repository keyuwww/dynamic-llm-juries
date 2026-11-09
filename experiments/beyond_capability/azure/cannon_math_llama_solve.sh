#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=64G
#SBATCH -t 0-12:00
#SBATCH --exclude=holygpu8a31105
#SBATCH -o logs/math_llama_solve_%j.out
# Llama-3.1-8B-Instruct answers the 1,000 MMLU-Redux questions itself (its solve labels).
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load python/3.12.11-fasrc01
LC=/tmp/bc_${SLURM_JOB_ID}; mkdir -p $LC $PWD/home
export HF_HOME=$PWD/hf_cache HOME=$PWD/home XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source .venv/bin/activate
python -c "from huggingface_hub import snapshot_download; snapshot_download('meta-llama/Llama-3.1-8B-Instruct')"
export HF_HUB_OFFLINE=1
python dir_capture.py --phase solvegen --model meta-llama/Llama-3.1-8B-Instruct --qfile inputs/math_full.jsonl \
  --out out --tag math_full_llama3.1-8b --batch 32
