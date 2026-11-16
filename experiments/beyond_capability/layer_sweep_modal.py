"""Modal H100: stretching a judge along its judge direction at many layers (azure/layer_sweep.py).
One container captures hidden states and learns the per-layer directions (and, if the judge's own solve labels are
not available locally, answers the benchmark's questions itself); then one container per group of layers steers in
parallel. Outputs: volume dynamic-llm-juries-results:/beyond_capability_layers/<run>/ -> pulled to <local dir>.

  runs:  math      Llama-3.1-8B on MATH         -> out_math/layer_sweep/
         mmlu3b    Llama-3.2-3B on MMLU-Redux   -> out_mmlu/layer_sweep_llama3.2-3b/ (solve labels copied from Cannon)

  .venv/bin/modal run experiments/beyond_capability/layer_sweep_modal.py --phase smoke
  .venv/bin/modal run --detach experiments/beyond_capability/layer_sweep_modal.py --phase run --run mmlu3b
  .venv/bin/modal run experiments/beyond_capability/layer_sweep_modal.py --phase pull --run mmlu3b
"""
import json
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
HERE = "/root/bc"
RUNS = {
    "math": dict(model="meta-llama/Llama-3.1-8B-Instruct", items="math_full_items.jsonl.gz", tag="math",
                 groups=["8,10", "12,14", "16,18", "20,22", "24,26"], dest="out_math/layer_sweep"),
    "mmlu3b": dict(model="meta-llama/Llama-3.2-3B-Instruct", items="mmlu_full_items.jsonl.gz", tag="mmlu",
                   groups=["4,6,8,10", "12,14,16,18", "20,22,24,26"], dest="out_mmlu/layer_sweep_llama3.2-3b"),
    # solve labels: the preregistered test's own (Cannon out/esolves_mmlu_full_llama3.2-3b.jsonl, copied to out_mmlu/)
}

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5", "transformers>=4.57,<5", "accelerate>=0.34", "numpy", "huggingface_hub")
    .add_local_file(_here.parent / "azure" / "dir_capture.py", f"{HERE}/dir_capture.py")
    .add_local_file(_here.parent / "azure" / "layer_sweep.py", f"{HERE}/layer_sweep.py")
)
for f in ("math_full_items.jsonl.gz", "mmlu_full_items.jsonl.gz", "mmlu_full.jsonl"):
    image = image.add_local_file(_here.parent / "inputs" / f, f"{HERE}/inputs/{f}")
app = modal.App("dlj-beyond-capability-layers", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
GPU = dict(gpu="H100", volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
           secrets=[modal.Secret.from_name("huggingface")])


def out_dir(run):
    return f"/vol/beyond_capability_layers/{run}" if run != "math" else "/vol/beyond_capability_layers/math"


def sweep(run, *args):
    import threading
    c = RUNS[run]
    stop = threading.Event()

    def committer():
        while not stop.wait(60):
            vol.commit()
    threading.Thread(target=committer, daemon=True).start()
    try:
        subprocess.run([sys.executable, f"{HERE}/layer_sweep.py", "--model", c["model"], "--items",
                        f"{HERE}/inputs/{c['items']}", "--out", out_dir(run), "--tag", c["tag"], *args], check=True, cwd=HERE)
    finally:
        stop.set()
        vol.commit()


@app.function(timeout=3 * 3600, **GPU)
def capture(run: str) -> str:
    import gzip
    c = RUNS[run]
    out = out_dir(run)
    if not pathlib.Path(f"{out}/layers_{c['tag']}.json").exists():
        sweep(run, "--phase", "capture")
    sweep(run, "--phase", "dirs", "--layers", ",".join(c["groups"]))
    if "solve" in c:  # the judge answers the questions in the items file itself (thinking off, T = 0.7, one sample)
        s = c["solve"]
        qids = {json.loads(l)["qid"] for l in gzip.open(f"{HERE}/inputs/{c['items']}", "rt")}
        qf = f"/tmp/{s['qfile']}"
        with open(qf, "w") as fh:
            for l in open(f"{HERE}/inputs/{s['qfile']}"):
                if json.loads(l)["id"] in qids:
                    fh.write(l)
        tag = s["file"][len("esolves_"):-len(".jsonl")]
        subprocess.run([sys.executable, f"{HERE}/dir_capture.py", "--phase", "solvegen", "--model", c["model"], "--qfile", qf,
                        "--out", out, "--tag", tag, "--batch", "64"], check=True, cwd=HERE)
        vol.commit()
    return f"done: capture + dirs {run}"


@app.function(timeout=3 * 3600, **GPU)
def steer(run: str, layers: str) -> str:
    vol.reload()
    sweep(run, "--phase", "steer", "--layers", layers)
    return f"done: steer {run} {layers}"


@app.function(timeout=1800, **GPU)
def smoke() -> str:
    """Cached last-token re-run vs a full re-run (dir_capture.py style), unedited and with an edit at layer 14."""
    sys.path.insert(0, HERE)
    import torch
    from dir_capture import build_ids, load_rows, setup, verdict_ids
    from layer_sweep import last_token, prefix_cache
    c = RUNS["math"]
    tok, model, layers = setup(c["model"])
    t1, t2 = verdict_ids(tok)
    rows = load_rows(f"{HERE}/inputs/{c['items']}", 0)[:12]
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
            cm = float(lg[t1] - lg[t2])
            with torch.no_grad():
                lg = model(input_ids=torch.tensor([ids], device="cuda"), logits_to_keep=1).logits[0, -1].float()
            st["on"] = False
            res.append((cm, float(lg[t1] - lg[t2])))
        lines.append(f"{len(ids):6d} tok  none: cached {res[0][0]:+.3f} full {res[0][1]:+.3f}   "
                     f"edit: cached {res[1][0]:+.3f} full {res[1][1]:+.3f}")
    return "\n".join(lines)


@app.function(volumes={"/vol": vol}, timeout=1800)
def pull(run: str) -> dict:
    vol.reload()
    d = pathlib.Path(out_dir(run))
    keep = ("sweep_", "meta_", "layers_", "esolves_")
    return {p.name: p.read_bytes() for p in d.glob("*") if p.name.startswith(keep)} if d.exists() else {}


@app.local_entrypoint()
def main(phase: str = "run", run: str = "math"):
    if phase == "smoke":
        print(smoke.remote())
        return
    c = RUNS[run]
    if phase == "run":
        print(capture.remote(run))
        for msg in steer.starmap([(run, g) for g in c["groups"]]):
            print(msg)
    files = pull.remote(run)
    dest = _here.parent / c["dest"]
    dest.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = (_here.parent / c["solve"]["dest"] / name) if name.startswith("esolves_") and "solve" in c else dest / name
        p.write_bytes(data)
    print(f"pulled {sorted(files)} -> {dest}")
