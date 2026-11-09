#!/bin/bash
#SBATCH -p test
#SBATCH -c 4
#SBATCH --mem=32G
#SBATCH -t 0-02:00
#SBATCH -o logs/setup_%j.out
# One-time setup on Cannon: Python env + Qwen3.5-9B weights in the lab scratch HF cache.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load python/3.12.11-fasrc01
export HF_HOME=$PWD/hf_cache
python -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q "torch>=2.5" "transformers>=4.57" "accelerate>=0.34" numpy huggingface_hub flash-linear-attention
pip install -q causal-conv1d --no-build-isolation || echo "causal-conv1d did not install: generation works, slower"
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3.5-9B')"
python -c "import torch, transformers; print('torch', torch.__version__, 'transformers', transformers.__version__)"
echo SETUP_DONE
