#!/bin/bash
#SBATCH -p test
#SBATCH -c 8
#SBATCH --mem=48G
#SBATCH -t 0-03:00
#SBATCH -o logs/setup_%j.out
# One-time: Python env (the versions used on Modal) + the three OLMo-3 Think checkpoints in a scratch HF cache.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
mkdir -p home; export HOME=$PWD/home HF_HOME=$PWD/hf_cache PIP_CACHE_DIR=/tmp/pip_$SLURM_JOB_ID
python -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q "vllm==0.11.0" "transformers==4.57.1" "accelerate>=0.34" numpy huggingface_hub
python -c "import torch, vllm, transformers; print('torch', torch.__version__, 'vllm', vllm.__version__, 'transformers', transformers.__version__)"
for m in allenai/Olmo-3-7B-Think-SFT allenai/Olmo-3-7B-Think-DPO allenai/Olmo-3-7B-Think; do
  python -c "from huggingface_hub import snapshot_download; print(snapshot_download('$m'))"
done
echo SETUP_DONE
