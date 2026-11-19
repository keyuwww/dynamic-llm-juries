#!/bin/bash
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 1-00:00
#SBATCH --exclude=holygpu8a31105
#SBATCH -o logs/cot_%x_%j.out
# usage: sbatch -J c_<judge> job_cot.sh <judge> "<bench> ..." [limit]
# reasoning-first verdicts with the exact score (cot_exact.py) on the main pool and the same-model sets
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
source common.sh
J=$1; BENCHES=$2; LIM=${3:-0}
module load python/3.12.11-fasrc01 cuda/13.3.1-fasrc01 gcc/15.2.0-fasrc01
export VLLM_USE_FLASHINFER_SAMPLER=0
source ../.venv_vllm/bin/activate
IN=(); OUTS=(); RS=()
ROOT=outcot; [ "$LIM" -gt 0 ] && ROOT=outcot_smoke
for B in $BENCHES; do
  R=1536; [ $B = bbeh ] && R=8192
  mkdir -p $ROOT/${J}_$B
  IN+=(inputs/${ITEMS[$B]}); OUTS+=($ROOT/${J}_$B/cot_main.jsonl); RS+=($R)
  for S in sm sm2; do
    if [ -f inputs/${S}_${B}_items.jsonl.gz ]; then IN+=(inputs/${S}_${B}_items.jsonl.gz); OUTS+=($ROOT/${J}_$B/cot_$S.jsonl); RS+=($R); fi
  done
done
if [ "$LIM" -gt 0 ]; then
  python cot_exact.py --model ${MODEL[$J]} --window 32768 --items ${IN[0]} --out ${OUTS[0]} --reason ${RS[0]} --limit $LIM --check
else
  python cot_exact.py --model ${MODEL[$J]} --window 32768 --items "${IN[@]}" --out "${OUTS[@]}" --reason "${RS[@]}"
fi
echo COT_DONE $J
