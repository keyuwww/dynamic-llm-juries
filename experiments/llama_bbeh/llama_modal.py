"""Run a Llama model through the same BBEH solve + judge prompts as the Tinker pool, on Modal (vLLM).

Llama is not served on Tinker, so it runs here instead. Prompts come from build_prompts.py, so the
model sees exactly what the 8 pool models saw. Sampling matches the pool: temperature 0.7, one sample,
4096 max tokens to solve, 1024 to judge.

Usage (repo root):
  python3 experiments/llama_bbeh/build_prompts.py                         # once, no GPU
  .venv/bin/modal run experiments/llama_bbeh/llama_modal.py --limit 20    # pilot: 20 solve + 20 judge
  .venv/bin/modal run experiments/llama_bbeh/llama_modal.py               # full: 460 solve + 920 judge
  python3 experiments/llama_bbeh/ingest.py                                # grade + write pool-format files

Needs the Modal secret "huggingface" (HF token with the Llama licence accepted on Hugging Face).
Weights are cached in the Modal volume "hf-cache" so the later interpretability runs reuse them.
"""
import json
import pathlib

import modal

HERE = pathlib.Path(__file__).resolve().parent
PROMPTS = HERE / "prompts.jsonl"
DEFAULT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

image = (
    modal.Image.debian_slim(python_version="3.11")
    # vllm 0.6.6 predates transformers 5.x (missing tokenizer attributes), so pin a matching release
    .pip_install("vllm==0.6.6.post1", "transformers==4.47.1", "huggingface_hub>=0.25,<1.0")
    .add_local_file(PROMPTS, "/root/prompts.jsonl")
)
app = modal.App("dynamic-llm-juries-llama-bbeh", image=image)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="L40S", timeout=3 * 3600, secrets=[modal.Secret.from_name("huggingface")],
              volumes={"/root/.cache/huggingface": hf_cache})
def generate(model: str, limit: int, seed: int) -> list:
    from vllm import LLM, SamplingParams

    rows = [json.loads(l) for l in open("/root/prompts.jsonl")]
    solve = [r for r in rows if r["kind"] == "solve"]
    judge = [r for r in rows if r["kind"] == "judge"]
    if limit:
        solve, judge = solve[:limit], judge[:limit]

    llm = LLM(model=model, dtype="bfloat16", max_model_len=32768, seed=seed, gpu_memory_utilization=0.92)
    tok = llm.get_tokenizer()
    out = []
    for batch, max_new in ((solve, 4096), (judge, 1024)):
        prompts = [tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True) for r in batch]
        # skip anything that cannot fit (reported, not silently truncated)
        fits = [len(tok(p, add_special_tokens=False).input_ids) + max_new <= 32768 for p in prompts]
        sp = SamplingParams(temperature=0.7, max_tokens=max_new, seed=seed)
        res = llm.generate([p for p, ok in zip(prompts, fits) if ok], sp)
        it = iter(res)
        for r, ok in zip(batch, fits):
            if not ok:
                out.append(dict(kind=r["kind"], id=r["id"], text=None, n_in=None, n_out=0, finish="too_long"))
                continue
            g = next(it)
            o = g.outputs[0]
            out.append(dict(kind=r["kind"], id=r["id"], text=o.text, n_in=len(g.prompt_token_ids),
                            n_out=len(o.token_ids), finish=o.finish_reason))
    hf_cache.commit()
    return out


@app.local_entrypoint()
def main(model: str = DEFAULT_MODEL, limit: int = 0, seed: int = 0):
    if not PROMPTS.exists():
        raise SystemExit("run build_prompts.py first")
    out = generate.remote(model, limit, seed)
    key = model.split("/")[-1].lower()
    dest = HERE / f"raw_{key}{'_pilot' if limit else ''}.jsonl"
    with open(dest, "w") as f:
        for o in out:
            f.write(json.dumps(dict(o, model=model)) + "\n")
    n_long = sum(o["finish"] == "too_long" for o in out)
    print(f"wrote {dest} ({len(out)} outputs; {n_long} skipped as too long)")
