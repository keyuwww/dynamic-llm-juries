"""Modal GPU (H100) version of the cluster's cannon_stretch.sh: runs azure/stretch_pipeline.py (capture -> question-centred
judge direction -> shift and stretch steering), then azure/prereg_measure.py (KNOWS / SAYS / RESPONDS from the unedited
and shift columns only). One container per judge, both judges in parallel.
Outputs: volume dynamic-llm-juries-results:/beyond_capability_stretch/<bench>/<key>/

  .venv/bin/modal run --detach experiments/beyond_capability/stretch_modal.py --items rb2safety_items.jsonl.gz --bench rb2safety
  .venv/bin/modal run experiments/beyond_capability/stretch_modal.py --phase pull --bench rb2safety
"""
import json
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
HERE = "/root/bc"
MODELS = {"qwen3.5-9b": "Qwen/Qwen3.5-9B", "llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct", "qwen3.5-4b": "Qwen/Qwen3.5-4B"}
ITEM_FILES = ["rb2safety_items.jsonl.gz"]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5", "transformers>=4.57", "accelerate>=0.34", "numpy", "huggingface_hub", "flash-linear-attention")
    .add_local_file(_here.parent / "azure" / "dir_capture.py", f"{HERE}/dir_capture.py")
    .add_local_file(_here.parent / "azure" / "stretch_pipeline.py", f"{HERE}/stretch_pipeline.py")
    .add_local_file(_here.parent / "azure" / "prereg_measure.py", f"{HERE}/prereg_measure.py")
)
for f in ITEM_FILES:
    image = image.add_local_file(_here.parent / "inputs" / f, f"{HERE}/inputs/{f}")
app = modal.App("dlj-beyond-capability-stretch", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=8 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def run(key: str, items: str, bench: str) -> str:
    import threading
    work = f"/vol/beyond_capability_stretch/{bench}"
    out = f"{work}/{key}"
    stop = threading.Event()

    def committer():  # keep partial outputs safe
        while not stop.wait(60):
            vol.commit()

    threading.Thread(target=committer, daemon=True).start()
    try:
        subprocess.run([sys.executable, f"{HERE}/stretch_pipeline.py", "--model", MODELS[key], "--items",
                        f"{HERE}/inputs/{items}", "--out", out, "--tag", bench], check=True)
        measure_one(key, bench)
    finally:
        stop.set()
        vol.commit()
        hf_cache.commit()
    return f"done: {key} {bench}"


def measure_one(key: str, bench: str):
    """KNOWS / SAYS / RESPONDS from the unedited and shift columns only (azure/prereg_measure.py)."""
    work = f"/vol/beyond_capability_stretch/{bench}"
    sol = f"{work}/{key}/sol_none.json"  # one file per judge: both judges run in parallel
    pathlib.Path(sol).write_text(json.dumps({key: {}}))
    link = pathlib.Path(f"/tmp/w/out_{bench}")
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists():
        link.symlink_to(work)
    r = subprocess.run([sys.executable, f"{HERE}/prereg_measure.py", key, bench, sol], cwd="/tmp/w",
                       env={"PYTHONPATH": HERE, "PATH": "/usr/local/bin:/usr/bin:/bin"}, check=True, capture_output=True,
                       text=True)
    pathlib.Path(f"{work}/{key}/prereg_measure.json").write_text(r.stdout)


@app.function(volumes={"/vol": vol}, timeout=1800)
def measure(key: str, bench: str) -> str:
    vol.reload()
    measure_one(key, bench)
    vol.commit()
    return f"measured {key} {bench}"


@app.function(volumes={"/vol": vol}, timeout=1800)
def pull(bench: str) -> dict:
    vol.reload()
    d = pathlib.Path(f"/vol/beyond_capability_stretch/{bench}")
    keep = ("steer_", "direction_choice_", "prereg_measure", "layers_")
    return {f"{p.parent.name}/{p.name}": p.read_bytes() for p in d.glob("*/*") if p.name.startswith(keep)} if d.exists() else {}


@app.local_entrypoint()
def main(phase: str = "run", items: str = "rb2safety_items.jsonl.gz", bench: str = "rb2safety",
         keys: str = "qwen3.5-9b,llama3.1-8b"):
    if phase == "run":
        for msg in run.starmap([(k, items, bench) for k in keys.split(",")]):
            print(msg)
    if phase == "measure":
        for k in keys.split(","):
            print(measure.remote(k, bench))
    files = pull.remote(bench)
    dest = _here.parent / f"out_{bench}"
    for name, data in files.items():
        p = dest / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    print(f"pulled {sorted(files)} -> {dest}")
