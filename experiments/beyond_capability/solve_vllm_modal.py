"""Modal H100 + vLLM: judges answer benchmark questions themselves (thinking off, T = 0.7, one sample, at most 8192 new
tokens, one redraw; hitting the cap = wrong), for the all-pairs solve labels that the batched HF pass could not finish
(out of memory on long answers). -> out_allpairs/<judge>_<bench>/esolves_<bench>_<judge>.jsonl

  .venv/bin/modal run experiments/beyond_capability/solve_vllm_modal.py --jobs llama3.2-3b:math,phi4-mini:bbeh
"""
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
MODELS = {"llama3.2-3b": "meta-llama/Llama-3.2-3B-Instruct", "phi4-mini": "microsoft/Phi-4-mini-instruct",
          "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3", "granite3.3-8b": "ibm-granite/granite-3.3-8b-instruct",
          "llama3.2-1b": "meta-llama/Llama-3.2-1B-Instruct", "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct"}
image = (modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.11").pip_install("vllm")
         .add_local_file(_here.parent / "azure" / "vllm_solve.py", "/root/vllm_solve.py"))
for b in ("math", "bbeh", "mmlu"):
    image = image.add_local_file(_here.parent / "inputs" / f"solveq_{b}.jsonl", f"/root/solveq_{b}.jsonl")
app = modal.App("dlj-solve-vllm", image=image)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=4 * 3600, volumes={"/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def run(judge: str, bench: str) -> bytes:
    tag = f"{bench}_{judge}"
    subprocess.run([sys.executable, "/root/vllm_solve.py", "--model", MODELS[judge], "--qfile", f"/root/solveq_{bench}.jsonl",
                    "--out", "/tmp/o", "--tag", tag, "--ctx", "32768", "--max-out", "8192", "--redraws", "1"], check=True)
    return pathlib.Path(f"/tmp/o/esolves_{tag}.jsonl").read_bytes()


@app.local_entrypoint()
def main(jobs: str):
    todo = [x.split(":") for x in jobs.split(",")]
    calls = [run.spawn(j, b) for j, b in todo]
    for (j, b), c in zip(todo, calls):
        try:
            data = c.get()
            d = _here.parent / "out_allpairs" / f"{j}_{b}"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"esolves_{b}_{j}.jsonl").write_bytes(data)
            n = data.count(b"\n")
            print(f"saved {j} {b}: {n} answers", flush=True)
        except Exception as e:
            print(f"{j} {b}: FAILED {type(e).__name__}: {str(e)[:300]}", flush=True)
