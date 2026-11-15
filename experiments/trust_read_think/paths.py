"""Shared paths for Trust / Read / Think. One folder per judge; the item lists are shared by all judges.

Pick the judge with the JUDGE environment variable (default: qwen3.5-4b), e.g.
  JUDGE=qwen3.5-9b .venv/bin/python experiments/trust_read_think/step2.py
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGES = {"qwen3.5-4b": "Qwen/Qwen3.5-4B", "qwen3.5-9b": "Qwen/Qwen3.5-9B", "gpt-oss-20b": "openai/gpt-oss-20b",
          "nvidia-nemotron-nano-9b-v2": "nvidia/NVIDIA-Nemotron-Nano-9B-v2"}
JUDGE = os.environ.get("JUDGE", "qwen3.5-4b")
MODEL = JUDGES[JUDGE]
ITEMS = HERE / "results" / "raw" / "step1"          # items.jsonl, items_factuality.jsonl (shared)
RAW = ITEMS / JUDGE                                 # this judge's saved reads
RES = HERE / "results" / JUDGE                      # this judge's result JSONs
RES.mkdir(parents=True, exist_ok=True)


def judge_of(model: str) -> str:
    return {m: j for j, m in JUDGES.items()}[model]
