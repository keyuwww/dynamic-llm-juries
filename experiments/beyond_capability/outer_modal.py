"""Modal fallback for the outer evaluation and the repaired reasoning score (the main runs go to Cannon:
azure/cannon_outer/). Reuses the hidden states already on the volume (beyond_capability_allpairs/<judge>_<bench>/).

  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/outer_modal.py --smoke
"""
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
HERE = "/root/bc"
MODELS = {"llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct", "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
          "phi4-mini": "microsoft/Phi-4-mini-instruct", "granite3.3-8b": "ibm-granite/granite-3.3-8b-instruct",
          "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3"}
ITEMS = {"mmlu": "mmlu_full_items.jsonl.gz", "math": "math_full_items.jsonl.gz", "bbeh": "bbeh_items.jsonl.gz"}
img = (modal.Image.debian_slim(python_version="3.11")
       .pip_install("torch>=2.5", "transformers>=4.57,<5", "accelerate>=0.34", "numpy", "huggingface_hub", "sentencepiece", "protobuf")
       .add_local_file(_here.parent / "azure" / "dir_capture.py", f"{HERE}/dir_capture.py")
       .add_local_file(_here.parent / "azure" / "pair_pipeline.py", f"{HERE}/pair_pipeline.py")
       .add_local_file(_here.parent / "azure" / "outer_pipeline.py", f"{HERE}/outer_pipeline.py"))
for f in ITEMS.values():
    img = img.add_local_file(_here.parent / "inputs" / f, f"{HERE}/inputs/{f}")
vimg = (modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.11").pip_install("vllm")
        .add_local_file(_here.parent / "azure" / "cot_exact.py", f"{HERE}/cot_exact.py"))
for f in list(ITEMS.values()) + ["sm_math_items.jsonl.gz", "sm2_math_items.jsonl.gz"]:
    vimg = vimg.add_local_file(_here.parent / "inputs" / f, f"{HERE}/inputs/{f}")
app = modal.App("bc-outer", image=img)
vol = modal.Volume.from_name("dynamic-llm-juries-results")
hf = modal.Volume.from_name("hf-cache")
GPU = dict(gpu=["H100", "A100-80GB"], timeout=4 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf},
           secrets=[modal.Secret.from_name("huggingface")])


LEGACY = {("llama3.1-8b", "math"): "/vol/beyond_capability_layers/math"}  # keyuwww volume


@app.function(**GPU)
def outer(judge: str, bench: str, smoke: bool = False) -> str:
    out = LEGACY.get((judge, bench), f"/vol/beyond_capability_allpairs/{judge}_{bench}")
    extra = ["--n-push", "20", "--limit", "10", "--name", "outer_smoke"] if smoke else []
    p = subprocess.run([sys.executable, f"{HERE}/outer_pipeline.py", "--model", MODELS[judge], "--items",
                        f"{HERE}/inputs/{ITEMS[bench]}", "--out", out, "--tag", bench, *extra], cwd=HERE,
                       capture_output=True, text=True)
    vol.commit()
    return p.stdout[-3000:] + p.stderr[-3000:]


@app.function(image=vimg, **GPU)
def cot(judge: str, bench: str, limit: int = 20) -> str:
    p = subprocess.run([sys.executable, f"{HERE}/cot_exact.py", "--model", MODELS[judge], "--items",
                        f"{HERE}/inputs/{ITEMS[bench]}", "--out", "/tmp/cot.jsonl", "--reason", "1536", "--limit",
                        str(limit), "--check"], cwd=HERE, capture_output=True, text=True)
    return p.stdout[-5000:] + p.stderr[-3000:]


@app.function(image=vimg, **GPU)
def cot_full(judge: str, jobs: list) -> dict:
    """jobs: [(bench, set_name, items file, reason tokens)] -> {f"{bench}|{set}": jsonl text}"""
    import pathlib as P
    out = {}
    for bench, sname, fname, reason in jobs:
        f = f"/tmp/{bench}_{sname}.jsonl"
        p = subprocess.run([sys.executable, f"{HERE}/cot_exact.py", "--model", MODELS[judge], "--window", "32768", "--items",
                            f"{HERE}/inputs/{fname}", "--out", f, "--reason", str(reason)], cwd=HERE, capture_output=True, text=True)
        print(p.stdout[-1500:], p.stderr[-1500:], flush=True)
        out[f"{bench}|{sname}"] = P.Path(f).read_text() if P.Path(f).exists() else ""
    return out


@app.local_entrypoint()
def full(pairs: str = "", cot_mistral: bool = False):
    """outer on the given pairs (judge:bench,...); optionally Mistral's reasoning rerun (exact score)."""
    import concurrent.futures as cf
    import pathlib as P
    todo = [tuple(x.split(":")) for x in pairs.split(",") if x]
    with cf.ThreadPoolExecutor(16) as ex:
        futs = {ex.submit(outer.remote, j, b): f"outer {j} {b}" for j, b in todo}
        if cot_mistral:
            jobs = [("mmlu", "main", ITEMS["mmlu"], 1536), ("math", "main", ITEMS["math"], 1536),
                    ("math", "sm", "sm_math_items.jsonl.gz", 1536), ("math", "sm2", "sm2_math_items.jsonl.gz", 1536)]
            futs[ex.submit(cot_full.remote, "mistral-7b", jobs)] = "cot mistral-7b"
        for f in cf.as_completed(futs):
            name = futs[f]
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                print(f"===== {name} FAILED: {str(e)[:500]}", flush=True)
                continue
            if name.startswith("cot"):
                for key, text in r.items():
                    b, s = key.split("|")
                    d = _here.parent / "out_cot_exact" / f"mistral-7b_{b}"
                    d.mkdir(parents=True, exist_ok=True)
                    (d / f"cot_{s}.jsonl").write_text(text)
                    print(f"saved {d}/cot_{s}.jsonl: {text.count(chr(10))} rows", flush=True)
            else:
                print(f"===== {name} =====\n{r[-1500:]}", flush=True)


@app.local_entrypoint()
def main(smoke: bool = True):
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(2) as ex:
        futs = {ex.submit(outer.remote, "llama3.1-8b", "mmlu", True): "outer", ex.submit(cot.remote, "mistral-7b", "mmlu", 20): "cot"}
        for f in cf.as_completed(futs):
            print(f"===== {futs[f]} =====", flush=True)
            print(f.result(), flush=True)


@app.local_entrypoint()
def check(judge: str = "mistral-7b", bench: str = "math", limit: int = 20):
    """exact-logit parity of the repaired reasoning score (vLLM vs a Transformers forward pass) on a few rows."""
    print(cot.remote(judge, bench, limit), flush=True)
