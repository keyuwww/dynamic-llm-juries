#!/bin/bash
#SBATCH -p test
#SBATCH -c 4
#SBATCH --mem=32G
#SBATCH -t 0-02:00
#SBATCH -o logs/vllm_setup_%j.out
# Separate Python env with vLLM (it pins its own torch), for fast answer generation.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load python/3.12.11-fasrc01
mkdir -p $PWD/home; export HOME=$PWD/home XDG_CACHE_HOME=/tmp/vs_$SLURM_JOB_ID
python -m venv .venv_vllm && source .venv_vllm/bin/activate
pip install -q --upgrade pip && pip install -q vllm
python -c "import vllm, torch; print('vllm', vllm.__version__, 'torch', torch.__version__)"
echo VLLM_SETUP_DONE
