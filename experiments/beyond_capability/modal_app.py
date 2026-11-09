"""Run bc_jobs.py in a CPU-only Modal container (tinker is not installable on this laptop).
Outputs live on the Modal volume (dynamic-llm-juries-results:/beyond_capability), so a disconnect loses
nothing; `--phase pull` copies them back to experiments/beyond_capability/out/.

  .venv/bin/modal run experiments/beyond_capability/modal_app.py --phase models --args "GLM,Qwen,DeepSeek,Kimi"
  .venv/bin/modal run --detach experiments/beyond_capability/modal_app.py --phase solve --args "--models qwen3.5-9b"
  .venv/bin/modal run experiments/beyond_capability/modal_app.py --phase pull
"""
import pathlib
import shlex
import subprocess
import sys
import threading

import modal

_here = pathlib.Path(__file__).resolve()
REPO = _here.parents[2] if len(_here.parents) > 2 else pathlib.Path("/root/repo")
HERE = "/root/repo/experiments/beyond_capability"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("tinker>=0.31", "tinker-cookbook>=0.5.7", "datasets>=2.19", "pandas>=2.0", "pyarrow>=14")
    .add_local_dir(REPO / "experiments" / "tinker_pool", "/root/repo/experiments/tinker_pool",
                   ignore=["**/*_results/**", "**/__pycache__/**"])
    .add_local_dir(REPO / "experiments" / "jev_bff", "/root/repo/experiments/jev_bff",
                   ignore=["**/*_results/**", "**/__pycache__/**"])
    .add_local_dir(_here.parent, HERE, ignore=["out/**", "**/__pycache__/**", "**/*.npy"])
)
app = modal.App("dlj-beyond-capability", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
VOL_OUT = "/vol/beyond_capability"


def _env():
    env = {}
    p = REPO / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return {k: v for k, v in env.items() if k == "TINKER_API_KEY"}


@app.function(timeout=24 * 3600, secrets=[modal.Secret.from_dict(_env())], volumes={"/vol": vol})
def run(phase: str, args: str = "") -> str:
    if phase == "models":
        subprocess.run([sys.executable, f"{HERE}/list_models.py", *args.split(",")], check=True, cwd=HERE)
        return "done: models"
    pathlib.Path(VOL_OUT).mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, f"{HERE}/bc_jobs.py", "--phase", phase, "--out", VOL_OUT, *shlex.split(args)]
    stop = threading.Event()

    def committer():
        while not stop.wait(30):
            vol.commit()

    threading.Thread(target=committer, daemon=True).start()
    try:
        # "y" answers transformers' one-time "run this model's custom tokenizer code?" prompt (Kimi)
        subprocess.run(cmd, check=True, cwd=HERE, input=b"y\n" * 50)
    finally:
        stop.set()
        vol.commit()
    return f"done: {phase} {args}"


@app.function(volumes={"/vol": vol}, timeout=1800)
def pull() -> dict:
    vol.reload()
    d = pathlib.Path(VOL_OUT)
    return {p.name: p.read_bytes() for p in d.glob("*.jsonl")} if d.exists() else {}


@app.local_entrypoint()
def main(phase: str = "pull", args: str = ""):
    if phase != "pull":
        print(run.remote(phase, args))
    if phase == "models":
        return
    files = pull.remote()
    dest = _here.parent / "out"
    dest.mkdir(exist_ok=True)
    for name, data in files.items():
        (dest / name).write_bytes(data)
    print(f"pulled {sorted(files)} -> {dest}")
