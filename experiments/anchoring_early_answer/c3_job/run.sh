#!/bin/bash
# One OLMo-3 Think stage: finish its own answers / judging transcripts (resuming from the saved Modal shards), then
# read the verdict at every checkpoint + hidden states at A / E / C. STAGE file: "<key>" or "smoke:<key>".
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 HF_HOME=/tmp/hf
SPEC=$(cat STAGE); KEY=${SPEC#smoke:}
case $KEY in
  olmo3-7b-think-sft) RES=sft ;;
  olmo3-7b-think-dpo) RES=dpo ;;
  olmo3-7b-think) RES=final ;;
esac
# model weights: C3 data resource mounted read-only at /data/<name> (c3 deploy --data-resource <name>=<id>:ro)
MODEL=$(dirname $(find /data/$RES -name config.json | head -1))
nvidia-smi --query-gpu=name,memory.total --format=csv
python3 -c "import torch, vllm, transformers; print('torch', torch.__version__, 'vllm', vllm.__version__, 'transformers', transformers.__version__)"
ls $MODEL
W=/workspace/experiments/anchoring_early_answer
if [[ $SPEC == smoke:* ]]; then
  OUT=$C3_ARTIFACTS_DIR/smoke-$KEY; mkdir -p $OUT; LIM="--limit 1"
else
  OUT=$C3_ARTIFACTS_DIR/$KEY; mkdir -p $OUT; LIM=""
  cp /workspace/prev/$KEY/generations_s*.jsonl $OUT/
fi
cd $W
python3 gen_vllm.py --model $MODEL --out $OUT --chunk 32 $LIM
python3 - "$OUT" <<'PY'
import json, pathlib, sys
out = pathlib.Path(sys.argv[1]); rows = {}
for f in sorted(out.glob("generations*.jsonl")):
    for line in open(f):
        rows.setdefault(json.loads(line)["key"], line)
(out / "generations.jsonl").write_text("".join(rows.values()))
print(len(rows), "generations merged")
PY
python3 probe_steer.py --phase readout --model $MODEL --judge $KEY --prompts-from qwen3.5-4b --out $OUT \
  --gen $OUT/generations.jsonl --think $LIM
ls -la $OUT
