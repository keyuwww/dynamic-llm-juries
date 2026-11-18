#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:nvidia_h200:1
#SBATCH -c 8
#SBATCH --mem=128G
#SBATCH -t 0-24:00
#SBATCH -J capture_last
#SBATCH -o logs/capture_%j.out
# Last-token hidden states for an items file (capture_last.py). Usage:
#   MODEL=... ITEMS=... OUTD=... TAG=... [SHARD=0/2] [EXTRA="--limit 2"] sbatch capture.sh
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
BASE=/n/netscratch/tambe_lab/Everyone/keyuwang
LC=/tmp/ncap_${SLURM_JOB_ID}; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$BASE/beyond_capability_steer/hf_cache XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton \
  TORCHINDUCTOR_CACHE_DIR=$LC/inductor PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONDONTWRITEBYTECODE=1
source $BASE/beyond_capability_steer/.venv/bin/activate
nvidia-smi --query-gpu=name,memory.total --format=csv
python -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL')"
python capture_last.py --model $MODEL --items $ITEMS --out $OUTD --tag $TAG --shard ${SHARD:-0/1} ${EXTRA:-}
