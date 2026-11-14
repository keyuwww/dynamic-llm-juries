#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-08:00
#SBATCH --array=0-1
#SBATCH -o logs/capture_%A_%a.out
# Hidden states at every checkpoint of the Qwen judges' transcripts (RB2 Math + BFF). Reuses the steering session's
# Python env and HF cache. Resumes if resubmitted.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
ENV=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer
JUDGES=(qwen3.5-9b qwen3.5-4b); MODELS=(Qwen/Qwen3.5-9B Qwen/Qwen3.5-4B)
LC=/tmp/bcap_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$ENV/hf_cache XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton \
  TORCHINDUCTOR_CACHE_DIR=$LC/inductor PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source $ENV/.venv/bin/activate
nvidia-smi --query-gpu=name,memory.total --format=csv
python -c "from huggingface_hub import snapshot_download; snapshot_download('${MODELS[$SLURM_ARRAY_TASK_ID]}')"
python capture.py --judge ${JUDGES[$SLURM_ARRAY_TASK_ID]} --model ${MODELS[$SLURM_ARRAY_TASK_ID]} ${LIMIT:-}
