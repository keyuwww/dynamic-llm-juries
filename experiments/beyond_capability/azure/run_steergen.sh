#!/bin/bash
# Steering during thinking-on reasoning, on a plain GPU VM (Azure), no Modal.
# Copy this folder to the VM (see README in this folder), then:
#   bash run_steergen.sh setup            # once: Python env with torch, transformers, fast Qwen3.5 kernels
#   bash run_steergen.sh pilot            # 8 items, no edit: checks speed and that verdicts parse
#   bash run_steergen.sh all              # every condition, one after another; resumes if restarted
# Outputs: out/gen_<condition>.jsonl (copy back to experiments/beyond_capability/out_dirs/qwen3.5-9b/)
set -euo pipefail
cd "$(dirname "$0")"
MODEL=Qwen/Qwen3.5-9B
CONDS=(none "shift:Jt:4" "shift:Jt:-4" "stretch:Jt:10" "shift:Rt:4")

if [ "${1:-}" = setup ]; then
  python3 -m venv .venv && source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q "torch>=2.5" "transformers>=4.57" "accelerate>=0.34" numpy huggingface_hub flash-linear-attention
  pip install -q causal-conv1d --no-build-isolation || echo "causal-conv1d failed to build: generation still works, slower"
  python -c "import torch; print('GPU:', torch.cuda.get_device_name(0))"
  exit 0
fi
source .venv/bin/activate
mkdir -p out
if [ "${1:-}" = pilot ]; then
  python dir_capture.py --phase steergen --model $MODEL --items inputs/dir_items.jsonl.gz --out out --tag pilot_none \
    --edit none --batch 8 --limit 8 --steer-ids inputs/steer_think_ids.json
  exit 0
fi
for c in "${CONDS[@]}"; do
  tag=$(echo "$c" | tr ':' '_')
  python dir_capture.py --phase steergen --model $MODEL --items inputs/dir_items.jsonl.gz --out out --tag "$tag" \
    --edit "$c" --batch 16 --directions inputs/steer_think_dirs.json --steer-ids inputs/steer_think_ids.json
done
