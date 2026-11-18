"""Nemotron-3-Nano-30B-A3B own answers on Cannon (vLLM), thinking OFF (Nov 17). Tinker no longer serves this model.

Same prompts and sampling as the Tinker judges' own answers (T = 0.7, every output may fill the 64K context):
  solve|<qid>                    first own answer, main set (RB2 Math, JudgeBench, BFF)  -> match / differ label
  solve_k|<bench>|<qid>|s<s>     7 more own answers per main-set question                 -> belief
  bbeh|<qid>|s<s>                5 own answers per BBEH question                          -> belief for the directions

  python nano_gen.py --shard 0/2 [--limit 20]
Writes out/generations_<shard>.jsonl in chunks; resumes.
"""
import argparse
import gzip
import json
from pathlib import Path

from vllm import LLM, SamplingParams

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16")
ap.add_argument("--shard", default="0/1")
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--chunk", type=int, default=1024)
ap.add_argument("--jobs", default="nano_jobs.jsonl.gz")
ap.add_argument("--ctx", type=int, default=65536)
ap.add_argument("--tag", default="")
ap.add_argument("--seed-offset", type=int, default=0)
a = ap.parse_args()
i, n = map(int, a.shard.split("/"))
jobs = [j for k, j in enumerate(map(json.loads, gzip.open(a.jobs, "rt"))) if k % n == i]
if a.limit:
    jobs = jobs[: a.limit]
out = Path("out")
out.mkdir(exist_ok=True)
path = out / f"generations_{a.tag}{i}.jsonl"
done = {json.loads(l)["key"] for l in open(path)} if path.exists() else set()
jobs = [j for j in jobs if j["key"] not in done]
print(f"shard {a.shard}: {len(done)} done, {len(jobs)} to generate", flush=True)
llm = LLM(model=a.model, dtype="bfloat16", max_model_len=a.ctx, seed=0, gpu_memory_utilization=0.92,
          enable_prefix_caching=True, trust_remote_code=True)
tok = llm.get_tokenizer()
for start in range(0, len(jobs), a.chunk):
    chunk = jobs[start:start + a.chunk]
    prompts = [tok.apply_chat_template(j["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
               for j in chunk]
    if start == 0:
        print("PROMPT EXAMPLE:", repr(prompts[0][-300:]), flush=True)
    lens = [len(tok(p, add_special_tokens=False).input_ids) for p in prompts]
    params = [SamplingParams(temperature=0.7, max_tokens=max(16, a.ctx - m - 16), seed=j["seed"] + a.seed_offset)
              for j, m in zip(chunk, lens)]
    res = llm.generate(prompts, params, use_tqdm=False)
    with open(path, "a") as f:
        for j, m, r in zip(chunk, lens, res):
            o = r.outputs[0]
            f.write(json.dumps(dict(key=j["key"], bench=j["bench"], qid=j["qid"], sample=j["sample"], text=o.text,
                                    n_in=m, n_out=len(o.token_ids), finish=o.finish_reason, model=a.model)) + "\n")
    print(f"  {min(start + a.chunk, len(jobs))}/{len(jobs)}", flush=True)
print("GEN_DONE", flush=True)
