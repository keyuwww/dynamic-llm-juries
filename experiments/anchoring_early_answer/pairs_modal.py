"""Modal GPU run of the minimal-pair capture (cannon_belief/capture.py on cannon_belief/pair_jobs.jsonl.gz), one H100 per
judge in parallel. Outputs go to the volume dynamic-llm-juries-results:/belief_pairs/<judge>/ (hidden_ckpt.npy +
meta_ckpt.jsonl); pull them with `modal volume get`.

  .venv/bin/modal run experiments/anchoring_early_answer/pairs_modal.py                 # both judges
  .venv/bin/modal run experiments/anchoring_early_answer/pairs_modal.py --limit 20      # pilot
  .venv/bin/modal run experiments/anchoring_early_answer/pairs_modal.py --phase C       # reasoning first (pairs_gen.py)
  .venv/bin/modal volume get dynamic-llm-juries-results belief_pairs/qwen3.5-9b \
      experiments/anchoring_early_answer/cannon_belief/out_pairs/
"""
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
CB = _here.parent / "cannon_belief"
W = "/root/work"
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5", "transformers>=4.57", "accelerate>=0.34", "numpy", "huggingface_hub",
                 "flash-linear-attention")
    .add_local_file(CB / "capture.py", f"{W}/capture.py")
    .add_local_file(CB / "pair_jobs.jsonl.gz", f"{W}/pair_jobs.jsonl.gz")
    .add_local_file(CB / "pairs_gen.py", f"{W}/pairs_gen.py")
)
app = modal.App("dynamic-llm-juries-belief-pairs", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
MODELS = {"qwen3.5-9b": "Qwen/Qwen3.5-9B", "qwen3.5-4b": "Qwen/Qwen3.5-4B"}


@app.function(gpu="H100", timeout=3 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def run(judge: str, limit: int = 0, phase: str = "A") -> str:
    """phase A: margin + state right after "VERDICT:" (no reasoning). phase C: the judge writes its reasoning first
    (pairs_gen.py), then margin + state at its verdict word."""
    outdir = "/vol/belief_pairs" + ("" if phase == "A" else "_C") + ("_pilot" if limit else "")
    script = "capture.py" if phase == "A" else "pairs_gen.py"
    cmd = [sys.executable, script, "--judge", judge, "--model", MODELS[judge], "--outdir", outdir]
    cmd += ["--jobs", "pair_jobs.jsonl.gz", "--margins"] if phase == "A" else []
    cmd += ["--limit", str(limit)] if limit else []
    try:
        subprocess.run(cmd, check=True, cwd=W)
    finally:
        vol.commit()
        hf_cache.commit()
    return f"done {judge}"


@app.local_entrypoint()
def main(limit: int = 0, judges: str = "qwen3.5-9b,qwen3.5-4b", phase: str = "A"):
    for r in run.starmap([(j, limit, phase) for j in judges.split(",")]):
        print(r)
