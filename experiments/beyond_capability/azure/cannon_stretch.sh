#!/bin/bash
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-12:00
#SBATCH --exclude=holygpu8a31105
#SBATCH --constraint=a100|h100|h200
#SBATCH -o logs/stretch_%x_%j.out
# usage: sbatch -p seas_gpu,gpu_requeue --requeue -J <name> cannon_stretch.sh <hf model> <items> <out dir> <tag> [--alphas=.. --betas=..]
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load python/3.12.11-fasrc01
LC=/tmp/bc_${SLURM_JOB_ID}; mkdir -p $LC $PWD/home
export HF_HOME=$PWD/hf_cache HF_HUB_OFFLINE=1 HOME=$PWD/home XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source .venv/bin/activate
python stretch_pipeline.py --model "$1" --items "$2" --out "$3" --tag "$4" "${@:5}"
