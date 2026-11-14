#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-08:00
#SBATCH -o logs/solve_steer_%A_%a.out
# Push the belief direction while Qwen3.5-9B solves RB2 Math (solve_steer.py), one condition per array task.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
ENV=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer
LC=/tmp/bst_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$ENV/hf_cache HF_HUB_OFFLINE=1 XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton \
  TORCHINDUCTOR_CACHE_DIR=$LC/inductor PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source $ENV/.venv/bin/activate
read -ra C <<< "${CONDS:-none belief:-8 belief_orth:-8 correct:-8 random:-8 belief:8}"
c=${C[$SLURM_ARRAY_TASK_ID]}
nvidia-smi --query-gpu=name,memory.total --format=csv
python solve_steer.py --cond "$c" ${EXTRA:-}
