"""Read the judge direction directly (no stretch): per-answer position along the cross-fit correctness direction,
same split and recipe as azure/pair_pipeline.py, at the given layers. CPU only, reads hidden_<bench>.npy on the volume.
-> out_allpairs/<pair>/direct_<bench>.json  {layer: {aid: projection}}

  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/direct_readout_modal.py
  MODAL_PROFILE=keyuwww .venv/bin/modal run experiments/beyond_capability/direct_readout_modal.py --phase sweeps
"""
import json
import pathlib

import modal

app = modal.App("bc-direct-readout")
vol = modal.Volume.from_name("dynamic-llm-juries-results")
ROOT = "/vol/beyond_capability_allpairs"
N_LAYERS = {"llama3.1-8b": 32, "llama3.2-3b": 28, "qwen3.5-4b": 32, "phi4-mini": 32, "mistral-7b": 32,
            "granite3.3-8b": 40, "llama3.2-1b": 16, "qwen2.5-7b": 28}
img = modal.Image.debian_slim().pip_install("numpy")


@app.function(image=img, volumes={"/vol": vol}, timeout=3600, cpu=8, memory=32768)
def proj(judge: str, bench: str, layers: list, d: str = "") -> dict:
    import numpy as np
    d = pathlib.Path(d or f"{ROOT}/{judge}_{bench}")
    H = np.load(d / f"hidden_{bench}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / f"meta_{bench}.jsonl")]
    nl = N_LAYERS[judge]
    kept = sorted(set(range(0, nl + 1, 2)) | {nl})
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    out = {}
    for L in layers:
        X = np.asarray(H[:, kept.index(L)], np.float32)
        Xc = X.copy()
        for g in uq:
            Xc[q == g] -= X[q == g].mean(0)
        s = np.zeros(len(y))
        for mask in (h1, ~h1):  # learn on one half, score the other
            v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
            s[~mask] = X[~mask] @ (v / (np.linalg.norm(v) + 1e-9))
        out[str(L)] = {m["aid"]: float(x) for m, x in zip(meta, s)}
    return {"judge": judge, "bench": bench, "proj": out}


@app.local_entrypoint()
def main(phase: str = "allpairs"):
    here = pathlib.Path(__file__).resolve().parent / "out_allpairs"
    R = json.load(open(here / "allpairs.json"))
    if phase == "sweeps":  # the two full-sweep pairs (volume of the keyuwww profile)
        for j, b, sub, L, dest in (("llama3.1-8b", "math", "math", [14, 16], "../out_math/layer_sweep"),
                                   ("llama3.2-3b", "mmlu", "mmlu3b", [12], "../out_mmlu/layer_sweep_llama3.2-3b")):
            r = proj.remote(j, b, L, f"/vol/beyond_capability_layers/{sub}")
            f = here / dest / f"direct_{b}.json"
            json.dump(r["proj"], open(f, "w"))
            print(f, list(r["proj"]))
        return
    todo = []
    for k, o in R.items():
        if k.startswith("extra") or "layer" not in o:
            continue
        j, b = k.split("|")
        if not (here / f"{j}_{b}" / f"choice_{b}.json").exists():
            continue  # the two full-sweep pairs live elsewhere
        todo.append((j, b, sorted({o["layer"], o["best_knows_layer"]})))
    for r in proj.starmap(todo, return_exceptions=True):
        if isinstance(r, Exception):
            print("FAILED", r)
            continue
        f = here / f"{r['judge']}_{r['bench']}" / f"direct_{r['bench']}.json"
        json.dump(r["proj"], open(f, "w"))
        print(f, list(r["proj"]))
