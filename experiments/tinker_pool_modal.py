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
import threading
import time

import modal

REPO = pathlib.Path(__file__).resolve().parent.parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("tinker>=0.31", "tinker-cookbook>=0.5.7", "typesafe-sdk>=0.7",
                 "datasets>=2.19", "pandas>=2.0", "pyarrow>=14")
    .add_local_dir(REPO / "experiments", "/root/repo/experiments", ignore=["**/*_results/**", "**/__pycache__/**", "**/data_cache/**"])
)

app = modal.App("dynamic-llm-juries-tinker", image=image)

# Durable storage: a Modal Volume persists across container restarts AND survives the local
# client disconnecting mid-run (unlike returning results only at the very end of a function
# call, which loses everything if the client disconnects before the function returns -- this
# bit us once already: ~1250 BBEH answer calls were paid for and then lost).
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
VOL_MOUNT = "/vol"


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


def _link_result_dir(bench):
    """Make the script's hardcoded output dir (tinker_pool/<bench>_results) live ON the volume,
    so every JsonlCache write lands in durable storage immediately -- not just at function return."""
    local_dir = pathlib.Path("/root/repo/experiments/tinker_pool")
    vol_dir = pathlib.Path(VOL_MOUNT) / f"{bench}_results"
    vol_dir.mkdir(parents=True, exist_ok=True)
    link = local_dir / f"{bench}_results"
    if link.is_symlink() or link.exists():
        if link.is_symlink():
            link.unlink()
        else:
            import shutil
            shutil.rmtree(link)
    link.symlink_to(vol_dir)
    return vol_dir


def _run_with_periodic_commit(cmd, cwd, interval=30):
    """Commit the volume every `interval` seconds while the subprocess runs, so a crash mid-run
    (not just a local-client disconnect) loses at most ~interval seconds of progress instead of
    everything since the function started."""
    stop = threading.Event()

    def committer():
        while not stop.wait(interval):
            vol.commit()

    t = threading.Thread(target=committer, daemon=True)
    t.start()
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    finally:
        stop.set()
        vol.commit()


@app.function(timeout=3 * 3600, secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_judges(bench: str, models: str = "all", conditions: str = "", limit: int = 0,
               samples: int = 1, concurrency: int = 32, per_item: int = 2, max_tokens: int = 0) -> str:
    _link_result_dir(bench)
    cmd = [sys.executable, "/root/repo/experiments/tinker_pool/run_judges.py",
           "--bench", bench, "--models", models, "--concurrency", str(concurrency), "--samples", str(samples),
           "--per-item", str(per_item)]
    if conditions:
        cmd += ["--conditions", conditions]
    if limit:
        cmd += ["--limit", str(limit)]
    if max_tokens:
        cmd += ["--max-tokens", str(max_tokens)]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    _run_with_periodic_commit(cmd, "/root/repo/experiments/tinker_pool")
    return f"done: {bench} judges"


@app.function(timeout=3 * 3600, secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_answers(bench: str, models: str = "all", limit: int = 0,
                samples: int = 1, concurrency: int = 32,
                thinking: str = "off", max_tokens: int = 0) -> str:
    _link_result_dir(bench)
    cmd = [sys.executable, "/root/repo/experiments/tinker_pool/run_answers.py",
           "--bench", bench, "--models", models, "--concurrency", str(concurrency), "--samples", str(samples),
           "--thinking", thinking]
    if limit:
        cmd += ["--limit", str(limit)]
    if max_tokens:
        cmd += ["--max-tokens", str(max_tokens)]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    _run_with_periodic_commit(cmd, "/root/repo/experiments/tinker_pool")
    return f"done: {bench} answers"


@app.function(timeout=3 * 3600, secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_debate(limit: int = 40, seed: int = 0, inputs: dict = None) -> str:
    vol_dir = pathlib.Path(VOL_MOUNT) / "debate_pilot_results"
    vol_dir.mkdir(parents=True, exist_ok=True)
    local_dir = pathlib.Path("/root/repo/experiments/debate")
    link = local_dir / "debate_pilot_results"
    if link.is_symlink() or link.exists():
        if link.is_symlink():
            link.unlink()
        else:
            import shutil
            shutil.rmtree(link)
    link.symlink_to(vol_dir)
    # round-1 result files (jev_bff_results/items.csv, bff_results/judgments.jsonl) live under
    # */_results/ paths the image intentionally excludes (those are run OUTPUTS, not inputs) --
    # this script needs them as INPUT, so the caller uploads them explicitly.
    for rel, data in (inputs or {}).items():
        dest = pathlib.Path("/root/repo/experiments") / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    cmd = [sys.executable, "/root/repo/experiments/debate/run_debate_pilot.py",
           "--limit", str(limit), "--seed", str(seed)]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    _run_with_periodic_commit(cmd, "/root/repo/experiments/debate")
    return "done: debate pilot"


@app.function(volumes={VOL_MOUNT: vol})
def list_volume_debate() -> dict:
    vol.reload()
    d = pathlib.Path(VOL_MOUNT) / "debate_pilot_results"
    if not d.exists():
        return {}
    return {str(p.relative_to(d)): p.stat().st_size for p in d.rglob("*") if p.is_file()}


@app.function(volumes={VOL_MOUNT: vol})
def pull_volume_debate() -> dict:
    vol.reload()
    d = pathlib.Path(VOL_MOUNT) / "debate_pilot_results"
    if not d.exists():
        return {}
    return {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*") if p.is_file()}


@app.function(volumes={VOL_MOUNT: vol})
def list_volume(bench: str) -> dict:
    vol.reload()
    d = pathlib.Path(VOL_MOUNT) / f"{bench}_results"
    if not d.exists():
        return {}
    return {str(p.relative_to(d)): p.stat().st_size for p in d.rglob("*") if p.is_file()}


@app.function(volumes={VOL_MOUNT: vol})
def pull_volume(bench: str) -> dict:
    vol.reload()
    d = pathlib.Path(VOL_MOUNT) / f"{bench}_results"
    if not d.exists():
        return {}
    return {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*") if p.is_file()}


def _write_local(bench, files):
    dest_dir = REPO / "experiments" / "tinker_pool" / f"{bench}_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"\nWrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def main(phase: str = "judges", bench: str = "bff", models: str = "all", conditions: str = "",
         limit: int = 0, samples: int = 1, concurrency: int = 32, per_item: int = 2,
         thinking: str = "off", max_tokens: int = 0):
    """Run with --detach so the job survives a local disconnect: results live on a Modal Volume,
    not in this function's return value -- use the `pull` / `status` entrypoints to fetch/check
    progress any time, independent of whether this invocation is still connected."""
    if phase == "answers":
        msg = run_answers.remote(bench=bench, models=models, limit=limit, samples=samples,
                                  concurrency=concurrency, thinking=thinking, max_tokens=max_tokens)
    else:
        msg = run_judges.remote(bench=bench, models=models, conditions=conditions, limit=limit,
                                 samples=samples, concurrency=concurrency, per_item=per_item, max_tokens=max_tokens)
    print(msg)
    _write_local(bench, pull_volume.remote(bench))


@app.local_entrypoint()
def pull(bench: str = "bbeh"):
    """Fetch whatever's on the volume right now, regardless of whether a run is still going."""
    _write_local(bench, pull_volume.remote(bench))


@app.local_entrypoint()
def status(bench: str = "bbeh"):
    """List files + sizes on the volume for this bench, without downloading them."""
    for rel, size in sorted(list_volume.remote(bench).items()):
        print(f"{size:>10}  {rel}")


def _debate_inputs():
    files = {
        "jev_bff/jev_bff_results/items.csv": REPO / "experiments/jev_bff/jev_bff_results/items.csv",
        "tinker_pool/bff_results/judgments.jsonl": REPO / "experiments/tinker_pool/bff_results/judgments.jsonl",
    }
    return {rel: p.read_bytes() for rel, p in files.items() if p.exists()}


@app.local_entrypoint()
def debate(limit: int = 40, seed: int = 0):
    msg = run_debate.remote(limit=limit, seed=seed, inputs=_debate_inputs())
    print(msg)
    files = pull_volume_debate.remote()
    dest_dir = REPO / "experiments" / "debate" / "debate_pilot_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def debate_pull():
    files = pull_volume_debate.remote()
    dest_dir = REPO / "experiments" / "debate" / "debate_pilot_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def debate_status():
    for rel, size in sorted(list_volume_debate.remote().items()):
        print(f"{size:>10}  {rel}")
