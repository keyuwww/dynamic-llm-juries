"""Modal GPU wrapper for probe_steer.py. Outputs go to the volume (dynamic-llm-juries-results/anchoring_probe/).

  .venv/bin/modal run experiments/anchoring_early_answer/probe_modal.py --phase capture --limit 20      # pilot
  .venv/bin/modal run experiments/anchoring_early_answer/probe_modal.py --phase capture
  .venv/bin/modal run experiments/anchoring_early_answer/probe_modal.py --phase steer --directions out_probe/qwen3.5-4b/directions.json
  .venv/bin/modal run experiments/anchoring_early_answer/probe_modal.py --phase pull
"""
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
REPO = _here.parents[2] if len(_here.parents) > 2 else pathlib.Path("/root/repo")
HERE = "/root/repo/experiments/anchoring_early_answer"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5", "transformers>=4.57", "accelerate>=0.34", "numpy", "huggingface_hub", "flash-linear-attention")
    .add_local_dir(REPO / "experiments" / "anchoring_early_answer", HERE,
                   ignore=["out/**", "out_pilot/**", "out_probe/**", "**/__pycache__/**"])
)
app = modal.App("dynamic-llm-juries-anchoring-probe", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=6 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def run(phase: str, model: str, judge: str, limit: int = 0, directions: str = "", alphas: str = "",
        prompts_from: str = "") -> str:
    out = f"/vol/anchoring_probe/{judge}" + ("_pilot" if limit else "")
    cmd = [sys.executable, f"{HERE}/probe_steer.py", "--phase", phase, "--model", model, "--judge", judge, "--out", out]
    if limit:
        cmd += ["--limit", str(limit)]
    if directions:
        cmd += ["--directions", directions]
    if alphas:
        cmd += ["--alphas", alphas]
    if prompts_from:
        cmd += ["--prompts-from", prompts_from]
    try:
        subprocess.run(cmd, check=True, cwd=HERE)
    finally:
        vol.commit()
        hf_cache.commit()
    return f"done: {phase}"


@app.function(volumes={"/vol": vol}, timeout=1800)
def pull(judge: str, pilot: bool = False) -> dict:
    vol.reload()
    d = pathlib.Path(f"/vol/anchoring_probe/{judge}" + ("_pilot" if pilot else ""))
    return {p.name: p.read_bytes() for p in d.iterdir() if p.is_file()} if d.exists() else {}


@app.local_entrypoint()
def main(phase: str = "capture", model: str = "Qwen/Qwen3.5-4B", judge: str = "qwen3.5-4b", limit: int = 0,
         directions: str = "", alphas: str = "", pilot: bool = False, prompts_from: str = ""):
    if phase != "pull":
        remote_dirs = ""
        if directions:  # ship the local directions file inside the call
            remote_dirs = f"/tmp/{pathlib.Path(directions).name}"
            print(run_with_file.remote(phase, model, judge, limit, pathlib.Path(directions).read_text(), alphas,
                                       prompts_from))
        else:
            print(run.remote(phase, model, judge, limit, remote_dirs, alphas, prompts_from))
    dest = _here.parent / "out_probe" / (judge + ("_pilot" if (pilot or limit) else ""))
    dest.mkdir(parents=True, exist_ok=True)
    files = pull.remote(judge, pilot or bool(limit))
    for name, data in files.items():
        (dest / name).write_bytes(data)
    print(f"pulled {sorted(files)} -> {dest}")


@app.function(gpu="H100", timeout=6 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def run_with_file(phase: str, model: str, judge: str, limit: int, directions_text: str, alphas: str,
                  prompts_from: str = "") -> str:
    p = pathlib.Path("/tmp/directions.json")
    p.write_text(directions_text)
    out = f"/vol/anchoring_probe/{judge}" + ("_pilot" if limit else "")
    cmd = [sys.executable, f"{HERE}/probe_steer.py", "--phase", phase, "--model", model, "--judge", judge,
           "--out", out, "--directions", str(p)]
    if alphas:
        cmd += ["--alphas", alphas]
    if prompts_from:
        cmd += ["--prompts-from", prompts_from]
    try:
        subprocess.run(cmd, check=True, cwd=HERE)
    finally:
        vol.commit()
        hf_cache.commit()
    return f"done: {phase}"
