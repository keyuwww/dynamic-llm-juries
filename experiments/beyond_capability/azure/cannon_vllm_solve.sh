#!/bin/bash
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100|h100|h200
#SBATCH --exclude=holygpu8a31105
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-12:00
#SBATCH -o logs/vllm_solve_%x_%j.out
# usage: sbatch ... cannon_vllm_solve.sh <hf model> <question file> <tag> [extra vllm_solve.py args]
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load python/3.12.11-fasrc01 cuda/13.3.1-fasrc01 gcc/15.2.0-fasrc01  # nvcc + compiler for vLLM's JIT kernels
export VLLM_USE_FLASHINFER_SAMPLER=0
LC=/tmp/bc_${SLURM_JOB_ID}; mkdir -p $LC $PWD/home
export HF_HOME=$PWD/hf_cache HF_HUB_OFFLINE=1 HOME=$PWD/home XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton VLLM_CACHE_ROOT=$LC/vllm
source .venv_vllm/bin/activate
python vllm_solve.py --model "$1" --qfile "$2" --out out --tag "$3" "${@:4}"
