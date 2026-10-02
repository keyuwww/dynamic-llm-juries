"""
Run the CLM-8B experiments on a Modal GPU with one command.

Spins up a GPU container that:
  1. serves the Qwen3-8B encoder with vLLM (pooling mode) and the CLM API (clm-serve),
  2. runs Exp 2 (router / certifier) and, optionally, Exp 1 (judge) with --backend clm,
  3. sends the result folders back, written to
       experiments/jev_router/clm_router_results/   and   experiments/jev_bff/clm_bff_results/
     so `uv run python experiments/compare_backends.py` can put CLM next to Jev.

One-time setup (on your laptop, repo root):
  uv add modal
  uv run modal token set --token-id <id> --token-secret <secret>     # or: uv run modal setup (browser login)

Run:
  uv run modal run experiments/clm_modal.py                      # router (Exp 2), full
  uv run modal run experiments/clm_modal.py --limit 30           # router pilot
  uv run modal run experiments/clm_modal.py --judge              # also Exp 1 (judge), slower: ~2k requests
  uv run modal run experiments/clm_modal.py --judge --judge-limit 100

Cost: an H100 is roughly $4-5/hour on Modal; first run downloads Qwen3-8B (~16 GB) into a cached Volume
(~5 min), later runs start in ~2 min. The router experiment itself takes a few minutes.
"""
import pathlib
import subprocess
import sys
import time

import modal

REPO = pathlib.Path(__file__).resolve().parent.parent
GPU = "H100"                 # 80 GB; matches what the CLM README benchmarked on
GPU_MEM_UTIL = "0.35"        # CLM README's own setting for an 80 GB card
MAX_MODEL_LEN = "8192"       # README uses 2048; the judge experiment sends whole conversations

hf_cache = modal.Volume.from_name("dlj-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "curl")
    .pip_install("vllm", "datasets>=2.19", "pandas>=2.0", "pyarrow>=14", "matplotlib", "typesafe-sdk>=0.7")
    .run_commands(
        "git clone --depth 1 https://github.com/Contrastive-LM/CLM.git /opt/CLM",
        "pip install -r /opt/CLM/requirements.txt || true",
        "pip install -e /opt/CLM",
    )
    .env({"HF_HOME": "/root/.cache/huggingface"})
    .add_local_dir(REPO / "experiments", "/root/repo/experiments", ignore=["**/*_results/**", "**/__pycache__/**"])
    .add_local_dir(REPO / "analysis", "/root/repo/analysis", ignore=["**/__pycache__/**"])
)

app = modal.App("dynamic-llm-juries-clm", image=image)


def _wait(url, name, proc, timeout=1200):
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f"{name} exited early with code {proc.returncode}")
        try:
            urllib.request.urlopen(url, timeout=5)
            print(f"[ok] {name} is up ({time.time() - t0:.0f}s)")
            return
        except Exception as e:  # 404 still means the server is listening
            if getattr(e, "code", None) is not None:
                print(f"[ok] {name} is up ({time.time() - t0:.0f}s)")
                return
            time.sleep(5)
    raise TimeoutError(f"{name} did not start within {timeout}s")


@app.function(gpu=GPU, timeout=3 * 3600, volumes={"/root/.cache/huggingface": hf_cache})
def run_clm(limit: int = 0, judge: bool = False, judge_limit: int = 0, probe: int = 0, clm_model: str = "",
            safety: bool = False) -> dict:
    vllm = subprocess.Popen(
        ["vllm", "serve", "Qwen/Qwen3-8B", "--served-model-name", "qwen3-8b", "--runner", "pooling",
         "--enable-prefix-caching", "--max-model-len", MAX_MODEL_LEN, "--gpu-memory-utilization", GPU_MEM_UTIL,
         "--port", "8090"])
    _wait("http://127.0.0.1:8090/health", "vLLM encoder", vllm)
    hf_cache.commit()  # keep downloaded weights for next time
    clm = subprocess.Popen(["clm-serve", "--port", "8700", "--emb-url", "http://127.0.0.1:8090/v1/embeddings",
                            "--max-tokens", MAX_MODEL_LEN])
    _wait("http://127.0.0.1:8700/", "CLM API", clm, timeout=600)

    out = pathlib.Path("/tmp/results")
    jobs = [("jev_router/clm_router_results",
             [sys.executable, "/root/repo/experiments/jev_router/run_jev_router.py", "--backend", "clm",
              "--clm-url", "http://127.0.0.1:8700", "--out", str(out / "jev_router/clm_router_results"),
              "--workers", "8", "--samples", "5"]
             + (["--limit", str(limit)] if limit else []))]
    if judge:
        tag = clm_model or "clm"
        jobs.append((f"jev_bff/{tag}_bff_results",
                     [sys.executable, "/root/repo/experiments/jev_bff/run_jev_bff.py", "--backend", "clm",
                      "--clm-url", "http://127.0.0.1:8700", "--out", str(out / f"jev_bff/{tag}_bff_results"), "--workers", "8"]
                     + (["--limit", str(judge_limit)] if judge_limit else [])
                     + (["--model", clm_model] if clm_model else [])))
    if probe:
        jobs.append(("probe/clm_criteria",
                     [sys.executable, "/root/repo/experiments/jev_bff/probe_clm_criteria.py",
                      "--clm-url", "http://127.0.0.1:8700", "--out", str(out / "probe/clm_criteria"),
                      "--limit", str(probe)]))
    if safety:
        jobs.append(("safety_clm_results",
                     [sys.executable, "/root/repo/experiments/safety_judge.py", "--backend", "clm",
                      "--clm-url", "http://127.0.0.1:8700", "--out", str(out / "safety_clm_results"),
                      "--workers", "8"]))
    for name, cmd in jobs:
        print(f"\n=== running {name} ===\n", flush=True)
        subprocess.run(cmd, check=True, cwd="/root/repo", env={**__import__("os").environ, "CLM_URL": "http://127.0.0.1:8700"})

    files = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    clm.terminate(); vllm.terminate()
    return files


@app.local_entrypoint()
def main(limit: int = 0, judge: bool = False, judge_limit: int = 0, probe: int = 0, clm_model: str = "",
         safety: bool = False):
    files = run_clm.remote(limit=limit, judge=judge, judge_limit=judge_limit, probe=probe, clm_model=clm_model,
                            safety=safety)
    for rel, data in files.items():
        dest = REPO / "experiments" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"\nWrote {len(files)} files under experiments/. Next: uv run python experiments/compare_backends.py")
