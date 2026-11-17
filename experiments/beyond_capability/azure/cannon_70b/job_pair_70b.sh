#!/bin/bash
#SBATCH --gres=gpu:2
#SBATCH -c 16
#SBATCH --mem=200G
#SBATCH -t 1-12:00
#SBATCH --exclude=holygpu8a31105
#SBATCH -o logs/pair70b_%x_%j.out
# usage: sbatch -J p70_<bench> job_pair_70b.sh <bench>
# Llama-3.1-70B as judge on one benchmark: gap -> push test -> layer (score rule, RULE_v2) -> stretch, the direction
# position of every answer, and the same-model test sets (stretch + direction position in one pass).
# Every stage is skipped when its output exists, so a requeued job continues where it stopped.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile; set -u  # module command (non-interactive submissions do not load it)
B=$1; J=llama3.1-70b; M=meta-llama/Llama-3.1-70B-Instruct; N=80; O=out70b/${J}_${B}
declare -A ITEMS=([mmlu]=mmlu_full_items.jsonl.gz [math]=math_full_items.jsonl.gz [bbeh]=bbeh_items.jsonl.gz)
module load python/3.12.11-fasrc01
LC=/tmp/bc_${SLURM_JOB_ID}; mkdir -p $LC $O
export HF_HOME=$PWD/../hf_cache HF_HUB_OFFLINE=1 HOME=$PWD/../home XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton \
       PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=../.venv_pp/bin/python
nvidia-smi --query-gpu=name,memory.total --format=csv
[ -f $O/done_pair_$B ] || { $PY pair_pipeline.py --phase pair --rule v2 --force --model $M --items inputs/${ITEMS[$B]} --out $O --tag $B && touch $O/done_pair_$B; }
[ -f $O/direct_$B.json ] || $PY direct_local.py --out $O --tag $B --n-layers $N
L=$($PY -c "import json; print(json.load(open('$O/choice_$B.json'))['chosen_layer'])")
echo "chosen layer $L"
[ -f $O/done_extra_$B ] || { $PY pair_pipeline.py --phase extra --with-proj --model $M --out $O --tag $B --layer $L --n-layers $N \
    --extra-items inputs/sm_${B}_items.jsonl.gz && touch $O/done_extra_$B; }
if [ -f inputs/sm2_${B}_items.jsonl.gz ] && [ ! -f $O/done_sm2_$B ]; then
  $PY pair_pipeline.py --phase extra --with-proj --prefix sm2extra --model $M --out $O --tag $B --layer $L --n-layers $N \
      --extra-items inputs/sm2_${B}_items.jsonl.gz && touch $O/done_sm2_$B
fi
echo PAIR70B_DONE $B
