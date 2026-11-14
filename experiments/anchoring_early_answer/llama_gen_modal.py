"""Llama-3.1-8B-Instruct's own answers and judging transcripts for the anchoring experiment (vLLM on Modal;
Llama is not on Tinker). Same prompts the Qwen judges got, same sampling (T = 0.7, one sample), and every
output may fill the whole 64K context so nothing is cut off by a small token limit.

  solve  one answer per question: BBEH (460, the pool's solve prompts), RB2 Math (183), JudgeBench (459)
  judge  one judging transcript per candidate: the 2,199 judge prompts the Qwen judges saw

Writes /vol/anchoring_llama/<model>/generations.jsonl (also pulled to out_llama/).

  .venv/bin/modal run --detach experiments/anchoring_early_answer/llama_gen_modal.py [--limit 10]
"""
import gzip
import json
import pathlib

import modal

_here = pathlib.Path(__file__).resolve()
LOCAL = _here.parent
REPO = _here.parents[2] if len(_here.parents) > 2 else pathlib.Path("/root/repo")
CTX = 65536


def build_jobs():
    jobs = []
    for p in map(json.loads, open(REPO / "experiments" / "llama_bbeh" / "prompts.jsonl")):
        if p["kind"] == "solve":
            jobs.append(dict(key=f"solve|bbeh|{p['id']}", messages=p["messages"]))
    seen = set()
    for j in map(json.loads, open(LOCAL / "inputs" / "solve_jobs.jsonl")):
        if j["qid"] not in seen:
            seen.add(j["qid"])
            jobs.append(dict(key=f"solve|{j['bench']}|{j['qid']}", messages=j["messages"]))
    with gzip.open(LOCAL / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        for j in map(json.loads, f):
            if j["judge"] == "qwen3.5-4b":  # judge prompts do not depend on the judge
                jobs.append(dict(key=f"judge|{j['bench']}|{j['item_id']}", messages=j["messages"]))
    return jobs


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("vllm==0.6.6.post1", "transformers==4.47.1", "huggingface_hub>=0.25,<1.0")
)
app = modal.App("dynamic-llm-juries-llama-gen", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=12 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def generate(model: str, jobs: list) -> str:
    from vllm import LLM, SamplingParams
    out_dir = pathlib.Path(f"/vol/anchoring_llama/{model.split('/')[-1].lower()}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "generations.jsonl"
    done = {json.loads(l)["key"] for l in open(path)} if path.exists() else set()
    jobs = [j for j in jobs if j["key"] not in done]
    print(f"{len(done)} already done, {len(jobs)} to generate", flush=True)
    llm = LLM(model=model, dtype="bfloat16", max_model_len=CTX, seed=0, gpu_memory_utilization=0.92)
    tok = llm.get_tokenizer()
    for start in range(0, len(jobs), 256):  # chunks, committed to the volume as they finish
        chunk = jobs[start:start + 256]
        prompts = [tok.apply_chat_template(j["messages"], tokenize=False, add_generation_prompt=True) for j in chunk]
        lens = [len(tok(p, add_special_tokens=False).input_ids) for p in prompts]
        params = [SamplingParams(temperature=0.7, max_tokens=max(16, CTX - n - 16), seed=0) for n in lens]
        res = llm.generate(prompts, params)
        with open(path, "a") as f:
            for j, n, r in zip(chunk, lens, res):
                o = r.outputs[0]
                f.write(json.dumps(dict(key=j["key"], text=o.text, n_in=n, n_out=len(o.token_ids),
                                        finish=o.finish_reason, model=model)) + "\n")
        vol.commit()
        print(f"  {min(start + 256, len(jobs))}/{len(jobs)}", flush=True)
    hf_cache.commit()
    return f"done: {len(jobs)} generated"


@app.function(volumes={"/vol": vol})
def pull(model: str) -> bytes:
    vol.reload()
    p = pathlib.Path(f"/vol/anchoring_llama/{model.split('/')[-1].lower()}/generations.jsonl")
    return p.read_bytes() if p.exists() else b""


@app.local_entrypoint()
def main(model: str = "meta-llama/Llama-3.1-8B-Instruct", limit: int = 0, pull_only: bool = False):
    if not pull_only:
        jobs = build_jobs()
        if limit:  # pilot: a few of each kind
            by = {}
            jobs = [j for j in jobs if by.setdefault(j["key"].split("|")[1] + j["key"][:5], []).append(1) or
                    len(by[j["key"].split("|")[1] + j["key"][:5]]) <= limit]
        print(f"{len(jobs)} jobs")
        print(generate.remote(model, jobs))
    data = pull.remote(model)
    dest = LOCAL / "out_llama"
    dest.mkdir(exist_ok=True)
    (dest / f"generations_{model.split('/')[-1].lower()}.jsonl").write_bytes(data)
    n_rows = data.count(b"\n")
    print(f"pulled {n_rows} rows -> {dest}")
