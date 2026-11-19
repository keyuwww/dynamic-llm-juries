#!/bin/bash
#SBATCH -p test
#SBATCH -c 8
#SBATCH --mem=32G
#SBATCH -t 0-04:00
#SBATCH -o logs/setup_%j.out
# weights of the small judges into the shared HF cache (the token already stored there is used; never printed)
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
SLURM_JOB_ID=${SLURM_JOB_ID:-setup}; source common.sh
export HF_HUB_OFFLINE=0
module load python/3.12.11-fasrc01
../.venv_pp/bin/python - <<'PY'
from huggingface_hub import snapshot_download
for m in ["meta-llama/Llama-3.1-8B-Instruct", "meta-llama/Llama-3.2-3B-Instruct", "meta-llama/Llama-3.2-1B-Instruct",
          "Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen3.5-4B", "microsoft/Phi-4-mini-instruct",
          "mistralai/Mistral-7B-Instruct-v0.3", "ibm-granite/granite-3.3-8b-instruct"]:
    p = snapshot_download(m, allow_patterns=["*.json", "*.safetensors", "tokenizer*", "*.model", "*.py", "*.tiktoken"])
    print("ok", m, flush=True)
PY
touch setup_done; echo SETUP_DONE
