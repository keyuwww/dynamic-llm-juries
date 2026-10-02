"""
Run the Tinker-pool judging experiments (Phase 2) in a CPU-only Modal container.

Why Modal here at all: Tinker itself is a remote API (no local GPU/model needed), but
`tinker`/`tinker-cookbook` (which pulls torch) can't be pip-installed on this laptop --
PyPI's wheel host is network-blocked here. Modal's image build happens in Modal's own
cloud, with normal network access, so the install just works there. No GPU is requested
(cpu-only function) since nothing runs locally except HTTP calls to Tinker's API.

Usage (repo root):
  uv run modal run experiments/tinker_pool_modal.py --bench bff
  uv run modal run experiments/tinker_pool_modal.py --bench safety
  uv run modal run experiments/tinker_pool_modal.py --bench bff --limit 60   # pilot
  uv run modal run experiments/tinker_pool_modal.py --bench bff --models routing,strong --conditions none,human
"""
import pathlib
import subprocess
import sys

import modal

REPO = pathlib.Path(__file__).resolve().parent.parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("tinker>=0.31", "tinker-cookbook>=0.5.7", "typesafe-sdk>=0.7",
                 "datasets>=2.19", "pandas>=2.0", "pyarrow>=14")
    .add_local_dir(REPO / "experiments", "/root/repo/experiments", ignore=["**/*_results/**", "**/__pycache__/**", "**/data_cache/**"])
)

app = modal.App("dynamic-llm-juries-tinker", image=image)


def _env():
    env = {}
    p = REPO / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


@app.function(timeout=3 * 3600, secrets=[modal.Secret.from_dict(_env())])
def run_judges(bench: str, models: str = "all", conditions: str = "", limit: int = 0,
               samples: int = 1, concurrency: int = 32) -> dict:
    cmd = [sys.executable, "/root/repo/experiments/tinker_pool/run_judges.py",
           "--bench", bench, "--models", models, "--concurrency", str(concurrency), "--samples", str(samples)]
    if conditions:
        cmd += ["--conditions", conditions]
    if limit:
        cmd += ["--limit", str(limit)]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    subprocess.run(cmd, check=True, cwd="/root/repo/experiments/tinker_pool")
    result_dir = pathlib.Path("/root/repo/experiments/tinker_pool") / f"{bench}_results"
    files = {str(p.relative_to(result_dir)): p.read_bytes() for p in result_dir.rglob("*") if p.is_file()}
    return files


@app.local_entrypoint()
def main(bench: str, models: str = "all", conditions: str = "", limit: int = 0,
         samples: int = 1, concurrency: int = 32):
    files = run_judges.remote(bench=bench, models=models, conditions=conditions,
                               limit=limit, samples=samples, concurrency=concurrency)
    dest_dir = REPO / "experiments" / "tinker_pool" / f"{bench}_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"\nWrote {len(files)} files to {dest_dir}")
