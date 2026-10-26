"""
Run the logit-lens pilot (experiments/interp/logit_lens_pilot.py) on a Modal GPU.

Why Modal: this laptop has no CUDA GPU (Apple M4, unified memory) and the same local PyPI block
that's affected the rest of this project, so torch/transformers can't be installed locally either.
Modal's build environment has full network access and a real GPU.

Usage (repo root):
  uv run modal run experiments/interp_modal.py --limit 20
  uv run modal run experiments/interp_modal.py --limit 20 --model Qwen/Qwen3.5-4B
"""
import pathlib
import subprocess
import sys
import threading

import modal

REPO = pathlib.Path(__file__).resolve().parent.parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.3", "transformers>=4.46", "accelerate>=0.34", "datasets>=2.19",
                 "pandas>=2.0", "pyarrow>=14", "huggingface_hub>=0.25",
                 "kernels>=0.17.2,<0.18.0")  # lets gpt-oss load its native MXFP4 quantization
                 # instead of dequantizing to bf16 (4x the memory, OOMs even a 40GB GPU)
    .add_local_dir(REPO / "experiments", "/root/repo/experiments",
                    ignore=["**/*_results/**", "**/__pycache__/**", "**/data_cache/**"])
)

app = modal.App("dynamic-llm-juries-interp", image=image)

vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
VOL_MOUNT = "/vol"


def _run_with_periodic_commit(cmd, cwd, interval=20):
    """Commit the volume every `interval` seconds while the subprocess runs, so a crash or
    disconnect mid-run loses at most ~interval seconds of progress, not the whole job (this bit
    us once already on the tinker-pool runs)."""
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


def _run_logit_lens_impl(limit, model, rubric, out_name):
    out_name = out_name or model.split("/")[-1].lower()
    if rubric != "rules":
        out_name = f"{out_name}_{rubric}"
    vol_dir = pathlib.Path(VOL_MOUNT) / "logit_lens_results" / out_name
    vol_dir.mkdir(parents=True, exist_ok=True)
    link = pathlib.Path("/root/repo/experiments/interp/logit_lens_results")
    if link.is_symlink() or link.exists():
        import shutil
        if link.is_symlink():
            link.unlink()
        else:
            shutil.rmtree(link)
    link.symlink_to(vol_dir)
    cmd = [sys.executable, "/root/repo/experiments/interp/logit_lens_pilot.py",
           "--limit", str(limit), "--model", model, "--rubric", rubric]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    _run_with_periodic_commit(cmd, "/root/repo/experiments/interp")
    return "done: logit lens pilot"


@app.function(timeout=3600, gpu="A10G", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_logit_lens(limit: int = 20, model: str = "Qwen/Qwen3.5-4B", rubric: str = "rules", out_name: str = "") -> str:
    return _run_logit_lens_impl(limit, model, rubric, out_name)


@app.function(timeout=5400, gpu="H100:2", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_logit_lens_big(limit: int = 20, model: str = "openai/gpt-oss-120b", rubric: str = "rules", out_name: str = "") -> str:
    # gpt-oss-120b: ~120B total params, needs more than a single A10G (24GB) even natively MXFP4-quantized.
    return _run_logit_lens_impl(limit, model, rubric, out_name)


@app.function(timeout=7200, gpu="H100:4", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_logit_lens_xl(limit: int = 20, model: str = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16",
                       rubric: str = "rules", out_name: str = "") -> str:
    # Plain-BF16 ~120B models (not natively quantized like gpt-oss) need ~240GB+ for weights alone --
    # H100:2 (160GB) silently OOM-kills with no Python traceback; H100:4 (320GB) has headroom.
    return _run_logit_lens_impl(limit, model, rubric, out_name)


def _run_activation_patching_impl(model, flip, window, max_items, rubric):
    link = pathlib.Path("/root/repo/experiments/interp/logit_lens_results")
    vol_dir = pathlib.Path(VOL_MOUNT) / "logit_lens_results"
    if link.is_symlink() or link.exists():
        import shutil
        if link.is_symlink():
            link.unlink()
        else:
            shutil.rmtree(link)
    link.symlink_to(vol_dir)
    cmd = [sys.executable, "/root/repo/experiments/interp/activation_patching.py",
           "--model", model, "--flip", flip, "--window", str(window), "--rubric", rubric]
    if max_items:
        cmd += ["--max-items", str(max_items)]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    subprocess.run(cmd, check=True, cwd="/root/repo/experiments/interp")
    out_name = model.split("/")[-1].lower()
    results_dirname = out_name if rubric == "rules" else f"{out_name}_{rubric}"
    fname = f"activation_patching_{results_dirname}_{flip}_w{window}.json"
    src = pathlib.Path("/root/repo/experiments/interp") / fname
    dest = vol_dir / fname
    dest.write_bytes(src.read_bytes())
    vol.commit()
    return f"done: activation patching ({fname})"


@app.function(timeout=3600, gpu="A10G", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_activation_patching(model: str = "openai/gpt-oss-20b", flip: str = "std_to_incorrect",
                             window: int = 1, max_items: int = 0, rubric: str = "rules") -> str:
    return _run_activation_patching_impl(model, flip, window, max_items, rubric)


@app.function(timeout=5400, gpu="H100:2", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_activation_patching_big(model: str = "openai/gpt-oss-120b", flip: str = "std_to_incorrect",
                                 window: int = 1, max_items: int = 0, rubric: str = "rules") -> str:
    return _run_activation_patching_impl(model, flip, window, max_items, rubric)


def _run_judgebench_impl(limit, model):
    out_name = f"judgebench_{model.split('/')[-1].lower()}"
    vol_dir = pathlib.Path(VOL_MOUNT) / "logit_lens_results" / out_name
    vol_dir.mkdir(parents=True, exist_ok=True)
    link = pathlib.Path("/root/repo/experiments/interp/logit_lens_results") / out_name
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        import shutil
        if link.is_symlink():
            link.unlink()
        else:
            shutil.rmtree(link)
    link.symlink_to(vol_dir)
    cmd = [sys.executable, "/root/repo/experiments/interp/layer_vs_human_judgebench.py",
           "--limit", str(limit), "--model", model]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    _run_with_periodic_commit(cmd, "/root/repo/experiments/interp")
    return f"done: judgebench logit lens ({out_name})"


@app.function(timeout=3600, gpu="A10G", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_judgebench(limit: int = 20, model: str = "Qwen/Qwen3.5-9B") -> str:
    return _run_judgebench_impl(limit, model)


@app.function(timeout=5400, gpu="H100:2", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_judgebench_big(limit: int = 20, model: str = "openai/gpt-oss-120b") -> str:
    return _run_judgebench_impl(limit, model)


@app.function(timeout=7200, gpu="H100:4", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_judgebench_xl(limit: int = 20, model: str = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16") -> str:
    return _run_judgebench_impl(limit, model)


@app.local_entrypoint()
def judgebench(limit: int = 459, model: str = "Qwen/Qwen3.5-9B"):
    msg = run_judgebench.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def judgebench_big(limit: int = 459, model: str = "openai/gpt-oss-120b"):
    msg = run_judgebench_big.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def judgebench_xl(limit: int = 459, model: str = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16"):
    msg = run_judgebench_xl.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


def _run_rb2safety_impl(limit, model):
    out_name = f"rb2safety_{model.split('/')[-1].lower()}"
    vol_dir = pathlib.Path(VOL_MOUNT) / "logit_lens_results" / out_name
    vol_dir.mkdir(parents=True, exist_ok=True)
    link = pathlib.Path("/root/repo/experiments/interp/logit_lens_results") / out_name
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        import shutil
        if link.is_symlink():
            link.unlink()
        else:
            shutil.rmtree(link)
    link.symlink_to(vol_dir)
    cmd = [sys.executable, "/root/repo/experiments/interp/layer_vs_human_rb2safety.py",
           "--limit", str(limit), "--model", model]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    _run_with_periodic_commit(cmd, "/root/repo/experiments/interp")
    return f"done: rb2safety logit lens ({out_name})"


@app.function(timeout=3600, gpu="A10G", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_rb2safety(limit: int = 20, model: str = "Qwen/Qwen3.5-9B") -> str:
    return _run_rb2safety_impl(limit, model)


@app.function(timeout=5400, gpu="H100:2", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_rb2safety_big(limit: int = 20, model: str = "openai/gpt-oss-120b") -> str:
    return _run_rb2safety_impl(limit, model)


@app.function(timeout=7200, gpu="H100:4", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_rb2safety_xl(limit: int = 20, model: str = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16") -> str:
    return _run_rb2safety_impl(limit, model)


def _run_rb2safety_rubric_impl(limit, model):
    out_name = f"rb2safety_rubric_{model.split('/')[-1].lower()}"
    vol_dir = pathlib.Path(VOL_MOUNT) / "logit_lens_results" / out_name
    vol_dir.mkdir(parents=True, exist_ok=True)
    link = pathlib.Path("/root/repo/experiments/interp/logit_lens_results") / out_name
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        import shutil
        if link.is_symlink():
            link.unlink()
        else:
            shutil.rmtree(link)
    link.symlink_to(vol_dir)
    cmd = [sys.executable, "/root/repo/experiments/interp/layer_vs_human_rb2safety_rubric.py",
           "--limit", str(limit), "--model", model]
    print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
    _run_with_periodic_commit(cmd, "/root/repo/experiments/interp")
    return f"done: rb2safety rubric logit lens ({out_name})"


@app.function(timeout=3600, gpu="A10G", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_rb2safety_rubric(limit: int = 20, model: str = "Qwen/Qwen3.5-9B") -> str:
    return _run_rb2safety_rubric_impl(limit, model)


@app.function(timeout=5400, gpu="H100:2", secrets=[modal.Secret.from_dict(_env())], volumes={VOL_MOUNT: vol})
def run_rb2safety_rubric_big(limit: int = 20, model: str = "openai/gpt-oss-120b") -> str:
    return _run_rb2safety_rubric_impl(limit, model)


@app.local_entrypoint()
def rb2safety_rubric(limit: int = 459, model: str = "Qwen/Qwen3.5-9B"):
    msg = run_rb2safety_rubric.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def rb2safety_rubric_big(limit: int = 459, model: str = "openai/gpt-oss-120b"):
    msg = run_rb2safety_rubric_big.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def rb2safety(limit: int = 459, model: str = "Qwen/Qwen3.5-9B"):
    msg = run_rb2safety.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def rb2safety_big(limit: int = 459, model: str = "openai/gpt-oss-120b"):
    msg = run_rb2safety_big.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def rb2safety_xl(limit: int = 459, model: str = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16"):
    msg = run_rb2safety_xl.remote(limit=limit, model=model)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.function(volumes={VOL_MOUNT: vol})
def clear_logit_lens_dir(out_name: str) -> str:
    import shutil
    vol.reload()
    d = pathlib.Path(VOL_MOUNT) / "logit_lens_results" / out_name
    if d.exists():
        shutil.rmtree(d)
        vol.commit()
        return f"cleared {d}"
    return f"not found: {d}"


@app.local_entrypoint()
def clear(out_name: str):
    print(clear_logit_lens_dir.remote(out_name))


@app.function(volumes={VOL_MOUNT: vol})
def pull_results() -> dict:
    vol.reload()
    d = pathlib.Path(VOL_MOUNT) / "logit_lens_results"
    if not d.exists():
        return {}
    return {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*") if p.is_file()}


@app.local_entrypoint()
def main(limit: int = 20, model: str = "Qwen/Qwen3.5-4B", rubric: str = "rules"):
    msg = run_logit_lens.remote(limit=limit, model=model, rubric=rubric)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def main_big(limit: int = 20, model: str = "openai/gpt-oss-120b", rubric: str = "rules"):
    msg = run_logit_lens_big.remote(limit=limit, model=model, rubric=rubric)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def main_xl(limit: int = 20, model: str = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16", rubric: str = "rules"):
    msg = run_logit_lens_xl.remote(limit=limit, model=model, rubric=rubric)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def patch(model: str = "openai/gpt-oss-20b", flip: str = "std_to_incorrect", window: int = 1, max_items: int = 0,
          rubric: str = "rules"):
    msg = run_activation_patching.remote(model=model, flip=flip, window=window, max_items=max_items, rubric=rubric)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")


@app.local_entrypoint()
def patch_big(model: str = "openai/gpt-oss-120b", flip: str = "std_to_incorrect", window: int = 1, max_items: int = 0,
              rubric: str = "rules"):
    msg = run_activation_patching_big.remote(model=model, flip=flip, window=window, max_items=max_items, rubric=rubric)
    print(msg)
    files = pull_results.remote()
    dest_dir = REPO / "experiments" / "interp" / "logit_lens_results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"Wrote {len(files)} files to {dest_dir}")
