#!/bin/bash
#SBATCH -p test
#SBATCH -c 8
#SBATCH --mem=32G
#SBATCH -t 0-08:00
#SBATCH -o logs/setup70b_%j.out
# One-time: a transformers<5 env for the hidden-state pipeline (KV-cache crop path) and the Llama-3.1-70B-Instruct
# weights (safetensors only) in the shared HF cache one level up.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile; set -u  # module command (non-interactive submissions do not load it)
module load python/3.12.11-fasrc01
mkdir -p ../home
export HF_HOME=$PWD/../hf_cache HOME=$PWD/../home XDG_CACHE_HOME=/tmp/s70_$SLURM_JOB_ID
if [ ! -x ../.venv_pp/bin/python ]; then
  python -m venv ../.venv_pp
  ../.venv_pp/bin/pip install -q --upgrade pip
  ../.venv_pp/bin/pip install -q "torch>=2.5" "transformers>=4.57,<5" "accelerate>=0.34" numpy huggingface_hub sentencepiece protobuf
fi
../.venv_pp/bin/python -c "
from huggingface_hub import snapshot_download
snapshot_download('meta-llama/Llama-3.1-70B-Instruct', allow_patterns=['*.json', '*.safetensors', 'tokenizer*'])
import torch, transformers; print('torch', torch.__version__, 'transformers', transformers.__version__)"
echo SETUP70B_DONE
