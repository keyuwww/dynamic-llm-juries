#!/bin/bash
#SBATCH -p seas_gpu
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=128G
#SBATCH -t 0-16:00
#SBATCH --array=0-2
#SBATCH -o logs/stage_%A_%a.out
# One OLMo-3 Think stage per array task: finish its own answers / judging transcripts (resuming from the saved Modal
# shards in prev/), then read the verdict at every checkpoint + hidden states at A / E / C. Resumes if resubmitted.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
set +u; source /etc/profile.d/lmod.sh; set -u
module load python/3.12.11-fasrc01
KEYS=(olmo3-7b-think-sft olmo3-7b-think-dpo olmo3-7b-think)
MODELS=(allenai/Olmo-3-7B-Think-SFT allenai/Olmo-3-7B-Think-DPO allenai/Olmo-3-7B-Think)
KEY=${KEYS[$SLURM_ARRAY_TASK_ID]}; MODEL=${MODELS[$SLURM_ARRAY_TASK_ID]}
LC=/tmp/olmo_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}; mkdir -p $LC home
export HOME=$PWD/home HF_HOME=$PWD/hf_cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 \
  XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton TORCHINDUCTOR_CACHE_DIR=$LC/inductor VLLM_CACHE_ROOT=$LC/vllm \
  PYTHONDONTWRITEBYTECODE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source .venv/bin/activate
nvidia-smi --query-gpu=name,memory.total --format=csv
OUT=$PWD/out/$KEY; mkdir -p $OUT
for f in prev/$KEY/generations_s*.jsonl; do [ -e $OUT/$(basename $f) ] || cp $f $OUT/; done
cd experiments/anchoring_early_answer
python gen_vllm.py --model $MODEL --out $OUT --chunk 32
python - "$OUT" <<'PY'
import json, pathlib, sys
out = pathlib.Path(sys.argv[1]); rows = {}
for f in sorted(out.glob("generations*.jsonl")):
    for line in open(f):
        rows.setdefault(json.loads(line)["key"], line)
(out / "generations.jsonl").write_text("".join(rows.values()))
print(len(rows), "generations merged", flush=True)
PY
python probe_steer.py --phase readout --model $MODEL --judge $KEY --prompts-from qwen3.5-4b --out $OUT \
  --gen $OUT/generations.jsonl --think
ls -la $OUT
echo STAGE_DONE
