"""Modal H100 + vLLM: Llama-3.1-8B answers each MATH question it was labelled as not solving 8 more times (thinking
off, T = 0.7, as azure/vllm_solve.py; answers capped at 8192 new tokens, one redraw), so "can't solve" can be made strict
(0 of 8 right) for the same-model test. -> out/esolves_sm_math_q8_llama3.1-8b.jsonl (ids "<qid>#<k>")

  .venv/bin/modal run experiments/beyond_capability/llama_resolve_modal.py
"""
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
image = (modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.11").pip_install("vllm")
         .add_local_file(_here.parent / "azure" / "vllm_solve.py", "/root/vllm_solve.py")
         .add_local_file(_here.parent / "inputs" / "sm_math_q8.jsonl", "/root/sm_math_q8.jsonl"))
app = modal.App("dlj-llama-resolve", image=image)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=3 * 3600, volumes={"/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def run() -> bytes:
    subprocess.run([sys.executable, "/root/vllm_solve.py", "--model", "meta-llama/Llama-3.1-8B-Instruct", "--qfile",
                    "/root/sm_math_q8.jsonl", "--out", "/tmp/o", "--tag", "sm_math_q8_llama3.1-8b", "--ctx", "16384",
                    "--max-out", "8192", "--redraws", "1"], check=True)
    return pathlib.Path("/tmp/o/esolves_sm_math_q8_llama3.1-8b.jsonl").read_bytes()


@app.local_entrypoint()
def main():
    data = run.remote()
    (_here.parent / "out" / "esolves_sm_math_q8_llama3.1-8b.jsonl").write_bytes(data)
    print("saved", len(data))
