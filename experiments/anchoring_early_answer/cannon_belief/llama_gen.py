"""Llama-3.1-8B-Instruct for the belief experiment (vLLM on Cannon). Same prompts and sampling as llama_gen_modal.py
(T = 0.7, every output may fill the whole 64K context).

  solve_k|<bench>|<qid>|s<s>   7 more own answers per question (s = 1..7), RB2 Math + JudgeBench + BFF -> belief
  solve|bff|<qid>              Llama's first own answer on BFF (it had none: BFF was added after the Llama run)
  judge|bff|<item_id>          Llama's judging transcript for each BFF candidate (the prompts the Qwens saw)

Jobs come from llama_jobs.jsonl.gz (built locally); --shard i/n splits them across GPUs. Writes
out_llama/generations_<shard>.jsonl in chunks; resumes.

  python llama_gen.py --shard 0/2
"""
import argparse
import gzip
import json
from pathlib import Path

from vllm import LLM, SamplingParams

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
ap.add_argument("--shard", default="0/1")
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--chunk", type=int, default=512)
a = ap.parse_args()
CTX = 65536
i, n = map(int, a.shard.split("/"))
jobs = [j for k, j in enumerate(map(json.loads, gzip.open("llama_jobs.jsonl.gz", "rt"))) if k % n == i]
if a.limit:
    jobs = jobs[: a.limit]
out = Path("out_llama")
out.mkdir(exist_ok=True)
path = out / f"generations_{i}.jsonl"
done = {json.loads(l)["key"] for l in open(path)} if path.exists() else set()
jobs = [j for j in jobs if j["key"] not in done]
print(f"shard {a.shard}: {len(done)} done, {len(jobs)} to generate", flush=True)
llm = LLM(model=a.model, dtype="bfloat16", max_model_len=CTX, seed=0, gpu_memory_utilization=0.92,
          enable_prefix_caching=True)
tok = llm.get_tokenizer()
for start in range(0, len(jobs), a.chunk):
    chunk = jobs[start:start + a.chunk]
    prompts = [tok.apply_chat_template(j["messages"], tokenize=False, add_generation_prompt=True) for j in chunk]
    lens = [len(tok(p, add_special_tokens=False).input_ids) for p in prompts]
    params = [SamplingParams(temperature=0.7, max_tokens=max(16, CTX - m - 16), seed=j["seed"])
              for j, m in zip(chunk, lens)]
    res = llm.generate(prompts, params, use_tqdm=False)
    with open(path, "a") as f:
        for j, m, r in zip(chunk, lens, res):
            o = r.outputs[0]
            f.write(json.dumps(dict(key=j["key"], text=o.text, n_in=m, n_out=len(o.token_ids),
                                    finish=o.finish_reason, model=a.model)) + "\n")
    print(f"  {min(start + a.chunk, len(jobs))}/{len(jobs)}", flush=True)
print("GEN_DONE", flush=True)
