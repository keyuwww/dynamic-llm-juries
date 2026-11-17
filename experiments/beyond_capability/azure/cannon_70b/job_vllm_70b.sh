#!/bin/bash
#SBATCH --gres=gpu:2
#SBATCH -c 16
#SBATCH --mem=200G
#SBATCH -t 1-00:00
#SBATCH --exclude=holygpu8a31105
#SBATCH -o logs/vllm70b_%x_%j.out
# usage: sbatch -J v70 job_vllm_70b.sh
# Llama-3.1-70B with vLLM (tensor parallel 2): (1) its own answers to every question (solve labels; thinking-free,
# T = 0.7, up to 8192 new tokens, one redraw), (2) the reasoning-first verdicts on every answer set.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile; set -u  # module command (non-interactive submissions do not load it)
J=llama3.1-70b; M=meta-llama/Llama-3.1-70B-Instruct
module load python/3.12.11-fasrc01 cuda/13.3.1-fasrc01 gcc/15.2.0-fasrc01
export VLLM_USE_FLASHINFER_SAMPLER=0
LC=/tmp/bc_${SLURM_JOB_ID}; mkdir -p $LC
export HF_HOME=$PWD/../hf_cache HF_HUB_OFFLINE=1 HOME=$PWD/../home XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton VLLM_CACHE_ROOT=$LC/vllm
source ../.venv_vllm/bin/activate
for B in mmlu math bbeh; do
  mkdir -p out70b/${J}_$B
  python vllm_solve.py --model $M --qfile inputs/solveq_$B.jsonl --out out70b/${J}_$B --tag ${B}_$J \
      --ctx 32768 --max-out 8192 --redraws 1 --tp 2
done
declare -A MAIN=([mmlu]=mmlu_full_items.jsonl.gz [math]=math_full_items.jsonl.gz [bbeh]=bbeh_items.jsonl.gz)
IN=(); OUTS=()
for B in mmlu math bbeh; do
  IN+=(inputs/${MAIN[$B]}); OUTS+=(out70b/${J}_$B/cot_main.jsonl)
  IN+=(inputs/sm_${B}_items.jsonl.gz); OUTS+=(out70b/${J}_$B/cot_sm.jsonl)
  if [ -f inputs/sm2_${B}_items.jsonl.gz ]; then IN+=(inputs/sm2_${B}_items.jsonl.gz); OUTS+=(out70b/${J}_$B/cot_sm2.jsonl); fi
done
python cot_vllm.py --model $M --tp 2 --items "${IN[@]}" --out "${OUTS[@]}"
echo VLLM70B_DONE
