"""An open model's own answers and judging transcripts (vLLM), for the anchoring experiment. Same prompts and sampling
as the Qwen judges and Llama (T = 0.7, one sample); every output may fill the whole 64K context.

  solve  one answer per question: BBEH (460, the pool's solve prompts), RB2 Math (183), JudgeBench (459)
  judge  one judging transcript per candidate: the 2,199 judge prompts the Qwen judges saw

Thinking models (OLMo-3 Think): the chat template opens <think>, so the text starts inside the thinking.
Resumes from <out>/generations.jsonl. Runs inside open_modal.py's image.

  python gen_vllm.py --model allenai/Olmo-3-7B-Instruct --out /vol/anchoring_open/olmo3-7b-instruct [--limit 3]
"""
import argparse
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CTX = 65536


def build_jobs():
    jobs = []
    for p in map(json.loads, open(REPO / "experiments" / "llama_bbeh" / "prompts.jsonl")):
        if p["kind"] == "solve":
            jobs.append(dict(key=f"solve|bbeh|{p['id']}", messages=p["messages"]))
    seen = set()
    for j in map(json.loads, open(HERE / "inputs" / "solve_jobs.jsonl")):
        if j["qid"] not in seen:
            seen.add(j["qid"])
            jobs.append(dict(key=f"solve|{j['bench']}|{j['qid']}", messages=j["messages"]))
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        for j in map(json.loads, f):
            if j["judge"] == "qwen3.5-4b":  # judge prompts do not depend on the judge
                jobs.append(dict(key=f"judge|{j['bench']}|{j['item_id']}", messages=j["messages"]))
    return jobs


def pilot(jobs, k):
    """k jobs of each (kind, bench)."""
    by, keep = {}, []
    for j in jobs:
        g = tuple(j["key"].split("|")[:2])
        if by.get(g, 0) < k:
            keep.append(j)
            by[g] = by.get(g, 0) + 1
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--shard", type=int, default=0, help="this container's share: jobs[shard::nshards]")
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--chunk", type=int, default=512, help="outputs written (and saved) after each chunk")
    a = ap.parse_args()
    from vllm import LLM, SamplingParams
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / ("generations.jsonl" if a.nshards == 1 else f"generations_s{a.shard}.jsonl")
    jobs = build_jobs()
    if a.limit:
        jobs = pilot(jobs, a.limit)
    jobs = jobs[a.shard::a.nshards]
    done = set()  # anything already generated, by any shard or an earlier run
    for f in out.glob("generations*.jsonl"):
        done |= {json.loads(l)["key"] for l in open(f)}
    jobs = [j for j in jobs if j["key"] not in done]
    print(f"{len(done)} already done, {len(jobs)} to generate", flush=True)
    llm = LLM(model=a.model, dtype="bfloat16", max_model_len=CTX, seed=0, gpu_memory_utilization=0.9)
    tok = llm.get_tokenizer()
    stop_ids = [i for i in {tok.eos_token_id, tok.convert_tokens_to_ids("<|im_end|>")} if isinstance(i, int) and i >= 0]
    for start in range(0, len(jobs), a.chunk):  # chunks, written as they finish (the caller commits the volume)
        chunk = jobs[start:start + a.chunk]
        prompts = [tok.apply_chat_template(j["messages"], tokenize=False, add_generation_prompt=True) for j in chunk]
        lens = [len(tok(p, add_special_tokens=False).input_ids) for p in prompts]
        params = [SamplingParams(temperature=0.7, top_p=1.0, max_tokens=max(16, CTX - n - 16), seed=0,
                                 stop_token_ids=stop_ids) for n in lens]
        res = llm.generate(prompts, params)
        with open(path, "a") as f:
            for j, n, r in zip(chunk, lens, res):
                o = r.outputs[0]
                f.write(json.dumps(dict(key=j["key"], text=o.text, n_in=n, n_out=len(o.token_ids),
                                        finish=o.finish_reason, model=a.model)) + "\n")
        print(f"  {min(start + a.chunk, len(jobs))}/{len(jobs)}", flush=True)
    print(f"done: generated {len(jobs)}", flush=True)


if __name__ == "__main__":
    main()
