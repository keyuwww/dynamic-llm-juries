#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-12:00
#SBATCH --array=0-1
#SBATCH -o logs/llama_gen_%A_%a.out
# Llama-3.1-8B belief samples + BFF answers/judgments (llama_gen.py), one shard per array task. Uses the OLMo run's vLLM
# env and the steering session's HF cache (Llama weights already there). Resumes if resubmitted.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
BASE=/n/netscratch/tambe_lab/Everyone/keyuwang
LC=/tmp/lgen_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$BASE/beyond_capability_steer/hf_cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton \
  TORCHINDUCTOR_CACHE_DIR=$LC/inductor VLLM_CACHE_ROOT=$LC/vllm PYTHONDONTWRITEBYTECODE=1
source $BASE/olmo_think/.venv/bin/activate
nvidia-smi --query-gpu=name,memory.total --format=csv
python llama_gen.py --shard ${SLURM_ARRAY_TASK_ID}/2 ${LIMIT:-}
