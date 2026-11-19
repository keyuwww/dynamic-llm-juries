#!/bin/bash
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 1-00:00
#SBATCH --exclude=holygpu8a31105
#SBATCH -o logs/outer_%x_%j.out
# usage: sbatch -J o_<judge>_<bench> job_outer.sh <judge> <bench> [limit]   (limit > 0: smoke run in a separate folder)
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
source common.sh
J=$1; B=$2; LIM=${3:-0}
O=out/${J}_${B}; EXTRA=""
if [ "$LIM" -gt 0 ]; then O=out_smoke/${J}_${B}; EXTRA="--limit $LIM"; fi
mkdir -p $O
module load python/3.12.11-fasrc01
PY=../.venv_pp/bin/python
nvidia-smi --query-gpu=name,memory.total --format=csv
[ -f $O/captured_$B ] || $PY pair_pipeline.py --phase pair --capture-only --model ${MODEL[$J]} --items inputs/${ITEMS[$B]} \
    --out $O --tag $B $EXTRA
[ -f $O/outer_$B.jsonl ] || $PY outer_pipeline.py --model ${MODEL[$J]} --items inputs/${ITEMS[$B]} --out $O --tag $B \
    $([ "$LIM" -gt 0 ] && echo "--n-push 20 --limit 10")
echo OUTER_DONE $J $B
