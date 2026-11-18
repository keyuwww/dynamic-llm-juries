#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:nvidia_h200:1
#SBATCH -c 8
#SBATCH --mem=128G
#SBATCH -t 0-12:00
#SBATCH --array=0-1
#SBATCH -J nano_gen
#SBATCH -o logs/nano_gen_%A_%a.out
# Nemotron-3-Nano own answers (nano_gen.py), one shard per array task, vLLM 0.33 env. Resumes if resubmitted.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01 cuda/13.3.1-fasrc01 gcc/15.2.0-fasrc01  # nvcc + compiler for vLLM JIT kernels
export VLLM_USE_FLASHINFER_SAMPLER=0
BASE=/n/netscratch/tambe_lab/Everyone/keyuwang
LC=/tmp/ngen_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$BASE/beyond_capability_steer/hf_cache VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 \
  XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton TORCHINDUCTOR_CACHE_DIR=$LC/inductor VLLM_CACHE_ROOT=$LC/vllm \
  PYTHONDONTWRITEBYTECODE=1
source $BASE/beyond_capability_steer/.venv_vllm/bin/activate
nvidia-smi --query-gpu=name,memory.total --format=csv
python -c "from huggingface_hub import snapshot_download; snapshot_download('nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16')"
python nano_gen.py --shard ${SLURM_ARRAY_TASK_ID}/2 ${LIMIT:-}
