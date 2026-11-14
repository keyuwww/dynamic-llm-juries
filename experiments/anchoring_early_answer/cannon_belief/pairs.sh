#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 0-04:00
#SBATCH -J pairs
#SBATCH -o logs/pairs_%j.out
# Minimal pairs (JudgeBench, answer-only template, every option letter): verdict margin + hidden states at "VERDICT:".
# Qwen3.5-9B then Qwen3.5-4B. Resumes if resubmitted.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
ENV=/n/netscratch/tambe_lab/Everyone/keyuwang/beyond_capability_steer
LC=/tmp/bpairs_${SLURM_JOB_ID}; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$ENV/hf_cache HF_HUB_OFFLINE=1 XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton \
  TORCHINDUCTOR_CACHE_DIR=$LC/inductor PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source $ENV/.venv/bin/activate
nvidia-smi --query-gpu=name,memory.total --format=csv
python capture.py --judge qwen3.5-9b --model Qwen/Qwen3.5-9B --jobs pair_jobs.jsonl.gz --margins --outdir out_pairs
python capture.py --judge qwen3.5-4b --model Qwen/Qwen3.5-4B --jobs pair_jobs.jsonl.gz --margins --outdir out_pairs
