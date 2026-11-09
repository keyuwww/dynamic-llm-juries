"""Modal GPU wrapper for dir_capture.py. Outputs: volume dynamic-llm-juries-results:/beyond_capability_dirs/<key>/.

  .venv/bin/modal run experiments/beyond_capability/dir_modal.py --phase capture --key qwen3.5-9b --items dir_items.jsonl.gz --tag main --limit 3
  .venv/bin/modal run --detach experiments/beyond_capability/dir_modal.py --phase capture --key qwen3.5-9b --items dir_items.jsonl.gz --tag main
  .venv/bin/modal run experiments/beyond_capability/dir_modal.py --phase pull --key qwen3.5-9b
"""
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
HERE = "/root/bc"
MODELS = {"qwen3.5-9b": "Qwen/Qwen3.5-9B", "llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct"}

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5", "transformers>=4.57", "accelerate>=0.34", "numpy", "huggingface_hub", "flash-linear-attention")
    .add_local_file(_here.parent / "dir_capture.py", f"{HERE}/dir_capture.py")
    .add_local_dir(_here.parent / "inputs", f"{HERE}/inputs")
)
app = modal.App("dlj-beyond-capability-dirs", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=12 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def run(phase: str, key: str, items: str, tag: str, limit: int = 0, extra: dict | None = None, flags: str = "") -> str:
    out = f"/vol/beyond_capability_dirs/{key}" + ("_pilot" if limit else "")
    cmd = [sys.executable, f"{HERE}/dir_capture.py", "--phase", phase, "--model", MODELS[key],
           "--items", f"{HERE}/inputs/{items}", "--out", out, "--tag", tag]
    if limit:
        cmd += ["--limit", str(limit)]
    cmd += flags.split() if flags else []
    for name, text in (extra or {}).items():  # small files shipped with the call (directions, steer ids)
        p = pathlib.Path(f"/tmp/{name}")
        p.write_text(text)
        cmd += [f"--{name.split('.')[0].replace('_', '-')}", str(p)]
    import threading
    stop = threading.Event()

    def committer():  # save partial outputs every 60 s (long generation runs)
        while not stop.wait(60):
            vol.commit()

    threading.Thread(target=committer, daemon=True).start()
    try:
        subprocess.run(cmd, check=True)
    finally:
        stop.set()
        vol.commit()
        hf_cache.commit()
    return f"done: {phase} {key} {tag}"


@app.function(volumes={"/vol": vol}, timeout=3600)
def listing(key: str) -> list:
    vol.reload()
    d = pathlib.Path(f"/vol/beyond_capability_dirs/{key}")
    return [p.name for p in d.iterdir()] if d.exists() else []


@app.local_entrypoint()
def main(phase: str = "capture", key: str = "qwen3.5-9b", items: str = "dir_items.jsonl.gz", tag: str = "main",
         limit: int = 0, directions: str = "", steer_ids: str = "", alphas: str = "", betas: str = "", flags: str = ""):
    if phase == "pull":
        print(listing.remote(key))
        return
    extra = {}
    if directions:
        extra["directions.json"] = pathlib.Path(directions).read_text()
    if steer_ids:
        extra["steer_ids.json"] = pathlib.Path(steer_ids).read_text()
    print(run.remote(phase, key, items, tag, limit, extra, flags))
