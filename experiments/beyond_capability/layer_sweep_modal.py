"""Modal H100: stretching Llama-3.1-8B along its judge direction at many layers on MATH (azure/layer_sweep.py).
One container captures hidden states and learns the per-layer directions; then one container per group of layers
steers in parallel. Outputs: volume dynamic-llm-juries-results:/beyond_capability_layers/<tag>/

  .venv/bin/modal run experiments/beyond_capability/layer_sweep_modal.py --phase smoke
  .venv/bin/modal run --detach experiments/beyond_capability/layer_sweep_modal.py --phase run
  .venv/bin/modal run experiments/beyond_capability/layer_sweep_modal.py --phase pull
"""
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
HERE = "/root/bc"
MODEL = "meta-llama/Llama-3.1-8B-Instruct"
ITEMS = "math_full_items.jsonl.gz"
TAG = "math"
GROUPS = ["8,10", "12,14", "16,18", "20,22", "24,26"]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5", "transformers>=4.57,<5", "accelerate>=0.34", "numpy", "huggingface_hub")
    .add_local_file(_here.parent / "azure" / "dir_capture.py", f"{HERE}/dir_capture.py")
    .add_local_file(_here.parent / "azure" / "layer_sweep.py", f"{HERE}/layer_sweep.py")
    .add_local_file(_here.parent / "inputs" / ITEMS, f"{HERE}/inputs/{ITEMS}")
)
app = modal.App("dlj-beyond-capability-layers", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
OUT = f"/vol/beyond_capability_layers/{TAG}"
GPU = dict(gpu="H100", volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
           secrets=[modal.Secret.from_name("huggingface")])


def sweep(*args):
    import threading
    stop = threading.Event()

    def committer():
        while not stop.wait(60):
            vol.commit()
    threading.Thread(target=committer, daemon=True).start()
    try:
        subprocess.run([sys.executable, f"{HERE}/layer_sweep.py", "--model", MODEL, "--items", f"{HERE}/inputs/{ITEMS}",
                        "--out", OUT, "--tag", TAG, *args], check=True, cwd=HERE)
    finally:
        stop.set()
        vol.commit()


@app.function(timeout=3 * 3600, **GPU)
def capture() -> str:
    if not pathlib.Path(f"{OUT}/layers_{TAG}.json").exists():
        sweep("--phase", "capture")
    sweep("--phase", "dirs", "--layers", ",".join(GROUPS))
    return "done: capture + dirs"


@app.function(timeout=3 * 3600, **GPU)
def steer(layers: str) -> str:
    vol.reload()
    sweep("--phase", "steer", "--layers", layers)
    return f"done: steer {layers}"


@app.function(timeout=1800, **GPU)
def smoke() -> str:
    """Cached last-token re-run vs a full re-run (dir_capture.py style), unedited and with an edit at layer 14."""
    sys.path.insert(0, HERE)
    import torch
    from dir_capture import build_ids, load_rows, setup, verdict_ids
    from layer_sweep import last_token, prefix_cache
    tok, model, layers = setup(MODEL)
    t1, t2 = verdict_ids(tok)
    rows = load_rows(f"{HERE}/inputs/{ITEMS}", 0)[:12]
    v = torch.randn(model.config.hidden_size, device="cuda")
    v /= v.norm()
    st = {"on": False}

    def hook(m, i, o):
        if not st["on"]:
            return o
        h = o[0] if isinstance(o, tuple) else o
        h = h.clone()
        h[0, -1] = (h[0, -1].float() + 8.0 * v).to(h.dtype)
        return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
    layers[13].register_forward_hook(hook)
    lines = []
    for r in rows:
        ids = build_ids(tok, r)
        res = []
        for on in (False, True):
            st["on"] = False
            cache = prefix_cache(model, ids)
            st["on"] = on
            lg = last_token(model, cache, ids, len(ids) - 1).logits[0, -1].float()
            c = float(lg[t1] - lg[t2])
            with torch.no_grad():
                lg = model(input_ids=torch.tensor([ids], device="cuda"), logits_to_keep=1).logits[0, -1].float()
            st["on"] = False
            res.append((c, float(lg[t1] - lg[t2])))
        lines.append(f"{len(ids):6d} tok  none: cached {res[0][0]:+.3f} full {res[0][1]:+.3f}   "
                     f"edit: cached {res[1][0]:+.3f} full {res[1][1]:+.3f}")
    return "\n".join(lines)


@app.function(volumes={"/vol": vol}, timeout=1800)
def pull() -> dict:
    vol.reload()
    d = pathlib.Path(OUT)
    keep = ("sweep_", "meta_", "layers_")
    return {p.name: p.read_bytes() for p in d.glob("*") if p.name.startswith(keep)} if d.exists() else {}


@app.local_entrypoint()
def main(phase: str = "run"):
    if phase == "smoke":
        print(smoke.remote())
        return
    if phase == "run":
        print(capture.remote())
        for msg in steer.map(GROUPS):
            print(msg)
    files = pull.remote()
    dest = _here.parent / "out_math" / "layer_sweep"
    dest.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (dest / name).write_bytes(data)
    print(f"pulled {sorted(files)} -> {dest}")
