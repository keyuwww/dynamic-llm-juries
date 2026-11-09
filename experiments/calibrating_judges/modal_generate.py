"""Run the judge generation and the activation extraction on Modal GPUs.

Credentials: none in this file. `modal token set` stores them in ~/.modal.toml on the laptop; nothing here reads or writes them.

Two ways to generate:
  hf    : generate_judge.py (HF generate; generation and activations in one pass; slow)
  vllm  : vllm_generate.py writes the text fast, then acts_from_gen.py reads the activations with one forward pass (the pipeline we use for the full runs)

  modal run modal_generate.py::hf --model Qwen/Qwen3.5-4B --bench bff --limit 48 --save-acts
  modal run modal_generate.py::fast --model Qwen/Qwen3.5-4B --bench bff --limit 48                      # vLLM generation only
  modal run modal_generate.py::pipeline --model Qwen/Qwen3.5-4B --bench bff --limit 48                  # vLLM generation + activations
  modal run modal_generate.py::fast --model Qwen/Qwen3.5-4B --bench bff --prompt confidence             # verbalized-confidence baseline
  modal run modal_generate.py::fast --model Qwen/Qwen3.5-4B --bench bff --n-samples 10 --temperature 0.7   # consistency / majority baselines

Results land in the Modal volume `cj-results` under <run-name>/ ; download with
  modal volume get cj-results <run-name> ./results/        (the volume is not in the repo; do not commit its contents)
"""
import os
import pathlib
import subprocess
import sys

import modal

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
JB_DIR = HERE / "local_data" / "jb"          # JudgeBench gpt.jsonl + claude.jsonl (data: do not commit)

hf_cache = modal.Volume.from_name("cj-hf-cache", create_if_missing=True)
out_vol = modal.Volume.from_name("cj-results", create_if_missing=True)
VOLS = {"/root/.cache/huggingface": hf_cache, "/out": out_vol}


def with_code_and_data(img):
    return (img.env({"HF_HOME": "/root/.cache/huggingface"})
            .add_local_dir(HERE, "/root/cj", ignore=["**/__pycache__/**", "**/*.npy", "**/*.jsonl", "**/*.csv", "local_data/**"])
            .add_local_file(ROOT / "tinker_pool_8models_judgments.jsonl", "/root/data/rb2_judgments.jsonl")
            .add_local_file(ROOT / "tinker_pool_8models_judgments_bff.jsonl", "/root/data/bff_judgments.jsonl")
            .add_local_file(ROOT / "role_conditioned_panels/data_cache/verdicts.parquet", "/root/data/verdicts.parquet")
            .add_local_file(ROOT / "role_conditioned_panels/data_cache/rb2.parquet", "/root/data/rb2.parquet")
            .add_local_file(JB_DIR / "gpt.jsonl", "/root/data/jb/gpt.jsonl")
            .add_local_file(JB_DIR / "claude.jsonl", "/root/data/jb/claude.jsonl"))


base = modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11").apt_install("git", "ninja-build")
hf_image = with_code_and_data(base.pip_install("torch", "transformers", "accelerate", "pandas", "pyarrow", "numpy", "sentencepiece", "protobuf", "flash-linear-attention")
                              .run_commands("pip install causal-conv1d --no-build-isolation || echo 'causal-conv1d not built, using the fallback conv'"))
vllm_image = with_code_and_data(base.pip_install("vllm", "pandas", "pyarrow", "numpy", "flash-linear-attention"))
app = modal.App("calibrating-judges", image=hf_image)


def data_args(bench):
    return ["--data", "/root/data/bff_judgments.jsonl" if bench == "bff" else "/root/data/rb2_judgments.jsonl", "--verdicts-path", "/root/data/verdicts.parquet",
            "--rb2-path", "/root/data/rb2.parquet", "--jb-dir", "/root/data/jb"]


def run_name_of(model, bench, prompt, n_samples, temperature, limit, name):
    return name or f"{model.split('/')[-1]}__{bench}__{prompt}__n{n_samples}_t{temperature}" + (f"__limit{limit}" if limit else "")


@app.function(gpu="H100", timeout=12 * 3600, volumes=VOLS)
def hf_run(model: str, bench: str, prompt: str = "uncertainty", n_samples: int = 1, temperature: float = 0.0, max_new_tokens: int = 4096, limit: int = 0,
           save_acts: bool = False, batch_size: int = 64, max_batch_tokens: int = 100000, name: str = "") -> str:
    run_name = run_name_of(model, bench, prompt, n_samples, temperature, limit, name)
    cmd = [sys.executable, "generate_judge.py", "--model", model, "--bench", bench, "--prompt", prompt, "--n-samples", str(n_samples), "--temperature", str(temperature),
           "--max-new-tokens", str(max_new_tokens), "--batch-size", str(batch_size), "--max-batch-tokens", str(max_batch_tokens), "--out", f"/out/{run_name}"] + data_args(bench)
    cmd += (["--limit", str(limit)] if limit else []) + (["--save-acts"] if save_acts else [])
    subprocess.run(cmd, check=True, cwd="/root/cj"); hf_cache.commit(); out_vol.commit()
    return run_name


@app.function(image=vllm_image, gpu="H100", timeout=12 * 3600, volumes=VOLS)
def vllm_run(model: str, bench: str, prompt: str = "uncertainty", n_samples: int = 1, temperature: float = 0.0, max_new_tokens: int = 4096, limit: int = 0,
             name: str = "", tp: int = 1, max_num_seqs: int = 0, offset: int = 0) -> str:
    run_name = run_name_of(model, bench, prompt, n_samples, temperature, limit, name)
    cmd = [sys.executable, "vllm_generate.py", "--model", model, "--bench", bench, "--prompt", prompt, "--n-samples", str(n_samples), "--temperature", str(temperature),
           "--max-new-tokens", str(max_new_tokens), "--tp", str(tp), "--out", f"/out/{run_name}"] + data_args(bench) + (["--limit", str(limit)] if limit else []) + (["--max-num-seqs", str(max_num_seqs)] if max_num_seqs else []) + (["--offset", str(offset)] if offset else [])
    subprocess.run(cmd, check=True, cwd="/root/cj", env={**os.environ, "VLLM_USE_FLASHINFER_SAMPLER": "0"}); hf_cache.commit(); out_vol.commit()   # FlashInfer's sampler needs a CUDA 13 toolchain to JIT; vLLM's own sampler is equivalent
    return run_name


@app.function(gpu="H100", timeout=12 * 3600, volumes=VOLS)
def acts_run(model: str, bench: str, run_name: str, prompt: str = "uncertainty", n_samples: int = 1, temperature: float = 0.0, layer_step: int = 2, max_batch_tokens: int = 60000) -> str:
    out_vol.reload()
    tag = f"{model.split('/')[-1]}__{bench}__{prompt}__n{n_samples}_t{temperature}"
    cmd = [sys.executable, "acts_from_gen.py", "--model", model, "--bench", bench, "--gen", f"/out/{run_name}/{tag}_gen.jsonl", "--prompt", prompt, "--layer-step", str(layer_step),
           "--max-batch-tokens", str(max_batch_tokens), "--out", f"/out/{run_name}"] + data_args(bench)
    subprocess.run(cmd, check=True, cwd="/root/cj"); hf_cache.commit(); out_vol.commit()
    return run_name


@app.function(gpu="H100", timeout=3 * 3600, volumes=VOLS)
def greedy_check_run(model: str, bench: str, run_name: str, prompt: str = "uncertainty") -> None:
    out_vol.reload()
    tag = f"{model.split('/')[-1]}__{bench}__{prompt}__n1_t0.0"
    subprocess.run([sys.executable, "check_greedy.py", "--model", model, "--bench", bench, "--gen", f"/out/{run_name}/{tag}_gen.jsonl", "--prompt", prompt] + data_args(bench), check=True, cwd="/root/cj")


@app.local_entrypoint()
def greedycheck(model: str, bench: str, run_name: str, prompt: str = "uncertainty"):
    greedy_check_run.remote(model, bench, run_name, prompt)


@app.function(timeout=3600, volumes=VOLS)
def ppe_stats() -> None:
    import sys; sys.path.insert(0, "/root/cj")
    import numpy as np, pandas as pd
    from judge_data import load_items
    for k in ("ppe_correct", "ppe_pref"):
        it = load_items(k); df = pd.DataFrame(it)
        print(f"\n{k}: {len(df)} items, {df.group.nunique()} questions; gold A share {np.mean(df.gold == 'A'):.3f}")
        print(df.source.value_counts().to_dict()); L = (df.input.str.len() + df.response_1.str.len() + df.response_2.str.len()); print("prompt chars mean / 95% / max:", int(L.mean()), int(L.quantile(.95)), int(L.max()))
        print(df.iloc[0][["item_id", "group", "gold"]].to_dict(), "|", df.iloc[0].input[:150].replace("\n", " "))


@app.local_entrypoint()
def ppecheck():
    ppe_stats.remote()


@app.function(gpu="H100", timeout=12 * 3600, volumes=VOLS)
def stats_run(model: str, bench: str, run_name: str, prompt: str = "uncertainty", limit: int = 0) -> str:
    out_vol.reload()
    tag = f"{model.split('/')[-1]}__{bench}__{prompt}__n1_t0.0"
    cmd = [sys.executable, "token_stats.py", "--model", model, "--bench", bench, "--gen", f"/out/{run_name}/{tag}_gen.jsonl", "--prompt", prompt, "--out", f"/out/{run_name}"] + data_args(bench) + (["--limit", str(limit)] if limit else [])
    subprocess.run(cmd, check=True, cwd="/root/cj"); hf_cache.commit(); out_vol.commit()
    return run_name


@app.local_entrypoint()
def tokstats(model: str, benches: str = "bff,rb2safety,judgebench", limit: int = 0):
    """token-probability signals for the probe run of each benchmark (one GPU per benchmark, in parallel)"""
    calls = [(b, stats_run.spawn(model, b, f"{model.split('/')[-1]}__{b}__uncertainty__n1_t0.0", "uncertainty", limit)) for b in benches.split(",")]
    for b, c in calls:
        print(f"[tokstats / {b}] done -> {c.get()}", flush=True)


@app.local_entrypoint()
def hf(model: str, bench: str, prompt: str = "uncertainty", n_samples: int = 1, temperature: float = 0.0, max_new_tokens: int = 4096, limit: int = 0,
       save_acts: bool = False, batch_size: int = 64, max_batch_tokens: int = 100000, name: str = ""):
    r = hf_run.remote(model, bench, prompt, n_samples, temperature, max_new_tokens, limit, save_acts, batch_size, max_batch_tokens, name)
    print(f"\ndone. modal volume get cj-results {r} ./results/")


@app.local_entrypoint()
def fast(model: str, bench: str, prompt: str = "uncertainty", n_samples: int = 1, temperature: float = 0.0, max_new_tokens: int = 4096, limit: int = 0, name: str = "", tp: int = 1):
    r = vllm_run.remote(model, bench, prompt, n_samples, temperature, max_new_tokens, limit, name, tp)
    print(f"\ndone. modal volume get cj-results {r} ./results/")


@app.local_entrypoint()
def sweep(model: str, benches: str = "bff,rb2safety,judgebench", max_new_tokens: int = 4096, baselines: bool = True, n_samples: int = 10, temperature: float = 0.7,
          layer_step: int = 2, tp: int = 1, max_num_seqs: int = 0, acts_batch_tokens: int = 60000):
    """Everything for one judge, one GPU per job, in parallel: the probe run (greedy, uncertainty prompt) + its activations, and (baselines) the stated-confidence run
    (greedy, confidence prompt) and the N-sample run (temperature 0.7) that give the consistency / majority / semantic-entropy baselines."""
    jobs = []
    for b in benches.split(","):
        jobs.append(("probe", b, vllm_run.spawn(model, b, "uncertainty", 1, 0.0, max_new_tokens, 0, "", tp, max_num_seqs)))
        if baselines:
            jobs.append(("verbalized", b, vllm_run.spawn(model, b, "confidence", 1, 0.0, max_new_tokens, 0, "", tp, max_num_seqs)))
            jobs.append(("samples", b, vllm_run.spawn(model, b, "uncertainty", n_samples, temperature, max_new_tokens, 0, "", tp, max_num_seqs)))
    acts = []
    for kind, b, call in jobs:
        r = call.get(); print(f"[{kind} / {b}] generation done -> {r}", flush=True)
        if kind == "probe":
            acts.append((b, acts_run.spawn(model, b, r, "uncertainty", 1, 0.0, layer_step, acts_batch_tokens)))
    for b, call in acts:
        print(f"[activations / {b}] done -> {call.get()}", flush=True)
    print("\nall done. modal volume ls cj-results")


@app.local_entrypoint()
def sweep_ppe(model: str, max_new_tokens: int = 4096, baselines: bool = True, n_samples: int = 10, temperature: float = 0.7, baseline_items: int = 2000, layer_step: int = 2,
              tp: int = 1, max_num_seqs: int = 0, acts_batch_tokens: int = 60000):
    """The paper's own training data (PPE, 7,000 correctness pairs + 7,000 human-preference pairs): the probe run on all items (+ activations), the stated-confidence run on all items,
    and the N-sample run on the first `baseline_items` items of each kind (a random subset; the full 10-sample run costs ~5 GPU-hours per judge and kind)."""
    kinds = ("ppe_correct", "ppe_pref"); probes = {b: vllm_run.spawn(model, b, "uncertainty", 1, 0.0, max_new_tokens, 0, "", tp, max_num_seqs) for b in kinds}; rest = []
    if baselines:
        for b in kinds:
            rest.append(("verbalized", b, vllm_run.spawn(model, b, "confidence", 1, 0.0, max_new_tokens, 0, "", tp, max_num_seqs)))
            rest.append(("samples", b, vllm_run.spawn(model, b, "uncertainty", n_samples, temperature, max_new_tokens, baseline_items, "", tp, max_num_seqs)))
    acts = []
    for b, call in probes.items():
        r = call.get(); print(f"[probe / {b}] generation done -> {r}", flush=True); acts.append((b, acts_run.spawn(model, b, r, "uncertainty", 1, 0.0, layer_step, acts_batch_tokens)))
    for kind, b, call in rest:
        print(f"[{kind} / {b}] generation done -> {call.get()}", flush=True)
    for b, call in acts:
        print(f"[activations / {b}] done -> {call.get()}", flush=True)
    print("\nall done. modal volume ls cj-results")


@app.local_entrypoint()
def pipeline(model: str, bench: str, prompt: str = "uncertainty", max_new_tokens: int = 4096, limit: int = 0, name: str = "", layer_step: int = 2, tp: int = 1,
             max_num_seqs: int = 0, acts_batch_tokens: int = 60000):
    r = vllm_run.remote(model, bench, prompt, 1, 0.0, max_new_tokens, limit, name, tp, max_num_seqs)
    r = acts_run.remote(model, bench, r, prompt, 1, 0.0, layer_step, acts_batch_tokens)
    print(f"\ndone. modal volume get cj-results {r} ./results/")
