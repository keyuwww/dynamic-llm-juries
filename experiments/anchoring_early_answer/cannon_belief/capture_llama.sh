#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-08:00
#SBATCH -J capture_llama
#SBATCH -o logs/capture_llama_%j.out
# Llama-3.1-8B: hidden states + verdict margins at every checkpoint of its RB2 Math + BFF transcripts.
# Reuses the steering session's Python env and HF cache. Resumes if resubmitted.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
ENV=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer
JUDGE=llama3.1-8b; MODEL=meta-llama/Llama-3.1-8B-Instruct
LC=/tmp/bcap_${SLURM_JOB_ID}_0; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$ENV/hf_cache XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton \
  TORCHINDUCTOR_CACHE_DIR=$LC/inductor PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source $ENV/.venv/bin/activate
nvidia-smi --query-gpu=name,memory.total --format=csv
python -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL')"
python capture.py --judge $JUDGE --model $MODEL --jobs ckpt_jobs_llama.jsonl.gz --margins ${LIMIT:-}
