#!/bin/bash
#SBATCH -p shared
#SBATCH -c 4
#SBATCH --mem=16G
#SBATCH -t 0-03:00
#SBATCH -J hf_download
#SBATCH -o logs/download_%j.out
# Download model weights into the shared HF cache once, so GPU jobs don't race. Usage: MODELS="a b" sbatch download.sh
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
BASE=/n/netscratch/tambe_lab/Everyone/keyuwang
export HOME=$PWD/home HF_HOME=$BASE/beyond_capability_steer/hf_cache HF_HUB_ENABLE_HF_TRANSFER=0
source $BASE/beyond_capability_steer/.venv/bin/activate
for m in $MODELS; do python -c "from huggingface_hub import snapshot_download; print(snapshot_download('$m'))"; done
echo DOWNLOAD_DONE
