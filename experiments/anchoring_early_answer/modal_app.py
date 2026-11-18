"""Run tinker_jobs.py in a CPU-only Modal container (tinker cannot be installed on this laptop).
Outputs live on the Modal volume, so a disconnect loses nothing; --pull copies them back here.

  .venv/bin/modal run experiments/anchoring_early_answer/modal_app.py --phase readout --limit 3   # pilot
  .venv/bin/modal run experiments/anchoring_early_answer/modal_app.py --phase solve
  .venv/bin/modal run experiments/anchoring_early_answer/modal_app.py --phase match
  .venv/bin/modal run experiments/anchoring_early_answer/modal_app.py --phase readout
  .venv/bin/modal run experiments/anchoring_early_answer/modal_app.py --phase pull
"""
import pathlib
import subprocess
import sys
import threading

import modal

_here = pathlib.Path(__file__).resolve()
REPO = _here.parents[2] if len(_here.parents) > 2 else pathlib.Path("/root/repo")  # local vs. inside the container
HERE = "/root/repo/experiments/anchoring_early_answer"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("tinker>=0.31", "tinker-cookbook>=0.5.7", "datasets>=2.19", "pandas>=2.0", "pyarrow>=14")
    .add_local_dir(REPO / "experiments" / "tinker_pool", "/root/repo/experiments/tinker_pool",
                   ignore=["**/*_results/**", "**/__pycache__/**", "**/data_cache/**"])
    .add_local_dir(REPO / "experiments" / "llama_bbeh", "/root/repo/experiments/llama_bbeh",
                   ignore=["**/*results*/**", "**/__pycache__/**"])
    .add_local_file(REPO / "experiments" / "jev_bff" / "run_jev_bff.py", "/root/repo/experiments/jev_bff/run_jev_bff.py")
    .add_local_dir(REPO / "experiments" / "anchoring_early_answer", HERE,
                   ignore=["out/**", "out_pilot/**", "out_nemotron/**", "out_probe/**", "out_deepseek/**", "out_kimi/**", "out_nano/**", "out_llama/**", "**/*.npy", "**/generations*.jsonl", "**/__pycache__/**"])
)
app = modal.App("dynamic-llm-juries-anchoring", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
VOL_OUT = "/vol/anchoring_early_answer"


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
def run(phase: str, limit: int = 0, models: str = "", benches: str = "", concurrency: int = 48,
        ckpts: str = "", matcher: str = "", extended: bool = False, kinds: str = "",
        open_key: str = "", redo_cut: int = 0, pairs: str = "", jobset: str = "") -> str:
    if phase == "models":
        subprocess.run([sys.executable, f"{HERE}/list_models.py", *benches.split(",")], check=True, cwd=HERE)
        return "done: models"
    if phase == "pooljudge":  # a new judge's pool verdicts (tinker_pool/run_judges.py, condition none) for the main set;
        # results live on the volume under pool_<bench>_results/judgments.jsonl (Nov 16: extra judge families)
        pool = pathlib.Path("/root/repo/experiments/tinker_pool")
        for b in benches.split(","):
            vd = pathlib.Path(f"/vol/pool_{b}_results")
            vd.mkdir(parents=True, exist_ok=True)
            link = pool / f"{b}_results"
            if link.is_symlink() or link.exists():
                link.unlink() if link.is_symlink() else __import__("shutil").rmtree(link)
            link.symlink_to(vd)
            cmd = [sys.executable, str(pool / "run_judges.py"), "--bench", b, "--models", models, "--conditions", "none",
                   "--concurrency", str(concurrency), "--max-tokens", "8192"] + (["--rb2-domains", "Math"] if b == "rb2" else []) \
                + (["--limit", str(limit)] if limit else [])
            try:
                subprocess.run(cmd, check=False, cwd=str(pool))  # the summary step may lack Phase 1 files
            finally:
                vol.commit()
        return "done: pooljudge"
    out = VOL_OUT + (f"_{jobset}" if jobset else "") + ("_pilot" if limit else "")
    cmd = [sys.executable, f"{HERE}/tinker_jobs.py", "--phase", phase, "--out", out,
           "--concurrency", str(concurrency)]
    if limit:
        cmd += ["--limit", str(limit)]
    if models:
        cmd += ["--models", models]
    if benches:
        cmd += ["--benches", benches]
    if ckpts:
        cmd += ["--ckpts", ckpts]
    if matcher:
        cmd += ["--matcher", matcher]
    if extended:
        cmd += ["--extended"]
    if kinds:
        cmd += ["--kinds", kinds]
    if open_key:
        cmd += ["--open", open_key]
    if redo_cut:
        cmd += ["--redo-cut", str(redo_cut)]
    if jobset:
        cmd += ["--set", jobset]
    if pairs:
        cmd += ["--pairs", pairs]
    stop = threading.Event()

    def committer():
        while not stop.wait(30):
            vol.commit()

    threading.Thread(target=committer, daemon=True).start()
    try:
        subprocess.run(cmd, check=True, cwd=HERE, input=b"y\n" * 50)  # "y": Kimi's custom tokenizer prompt
    finally:
        stop.set()
        vol.commit()
    return f"done: {phase}"


@app.function(volumes={"/vol": vol})
def pull(pilot: bool = False) -> dict:
    vol.reload()
    d = pathlib.Path(VOL_OUT + ("_pilot" if pilot else ""))
    return {p.name: p.read_bytes() for p in d.glob("*.jsonl")} if d.exists() else {}


@app.local_entrypoint()
def main(phase: str = "readout", limit: int = 0, models: str = "", benches: str = "", concurrency: int = 48,
         pilot: bool = False, ckpts: str = "", matcher: str = "", extended: bool = False,
         kinds: str = "", open_key: str = "", redo_cut: int = 0, pairs: str = ""):
    if phase != "pull":
        print(run.remote(phase, limit, models, benches, concurrency, ckpts, matcher, extended, kinds, open_key,
                         redo_cut, pairs))
    if phase == "models":
        return
    files = pull.remote(pilot or bool(limit))
    dest = pathlib.Path(__file__).resolve().parent / ("out_pilot" if (pilot or limit) else "out")
    dest.mkdir(exist_ok=True)
    for name, data in files.items():
        (dest / name).write_bytes(data)
    print(f"pulled {sorted(files)} -> {dest}")
