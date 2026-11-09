"""A model answers every prompt in a question file with vLLM (continuous batching, so one long answer never holds the
rest back). Thinking off; T = 0.7; one sample. Answers are written chunk by chunk, so a stopped job keeps its work.
By default each answer may fill the whole context; --max-out caps an answer's length instead (used for Llama on MATH,
where a few answers loop forever). Answers that hit the limit are redrawn from scratch up to --redraws times; one that
still hits it is written with capped=true (count it as wrong). -> <out>/esolves_<tag>.jsonl
(qid, text, n_out, clean, capped, tries)

  python vllm_solve.py --model meta-llama/Llama-3.1-8B-Instruct --qfile inputs/mmlu_full.jsonl --out out --tag mmlu_full_llama3.1-8b
  python vllm_solve.py --model meta-llama/Llama-3.1-8B-Instruct --qfile inputs/math_full.jsonl --out out --tag math_full_llama3.1-8b --max-out 32768 --redraws 1
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--qfile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ctx", type=int, default=131072)
    ap.add_argument("--max-out", type=int, default=0, help="cap on an answer's length in tokens (0 = whole context)")
    ap.add_argument("--redraws", type=int, default=3)
    ap.add_argument("--chunk", type=int, default=500, help="prompts per write")
    ap.add_argument("--shard", default="0/1", help="i/n: answer every n-th question starting at i (parallel jobs)")
    a = ap.parse_args()
    from vllm import LLM, SamplingParams
    si, sn = map(int, a.shard.split("/"))
    qs = [json.loads(l) for l in open(a.qfile)][si::sn]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fpath = out / (f"esolves_{a.tag}.jsonl" if sn == 1 else f"esolves_{a.tag}.part{si}of{sn}.jsonl")
    done = {json.loads(l)["qid"] for l in open(fpath)} if fpath.exists() else set()
    todo = [q for q in qs if q["id"] not in done]
    print(f"{len(todo)} to answer ({len(done)} done)", flush=True)
    llm = LLM(model=a.model, max_model_len=a.ctx, gpu_memory_utilization=0.92, enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    prompts = {q["id"]: tok.apply_chat_template([{"role": "user", "content": q["prompt"]}], tokenize=False,
                                                add_generation_prompt=True) for q in todo}

    def budget(k):
        room = a.ctx - len(tok(prompts[k]).input_ids) - 16
        return min(room, a.max_out) if a.max_out else room

    fh = open(fpath, "a")
    keys = list(prompts)
    for c in range(0, len(keys), a.chunk):
        pending, tries = keys[c:c + a.chunk], {}
        while pending:
            res = llm.generate([prompts[k] for k in pending],
                               [SamplingParams(temperature=0.7, max_tokens=budget(k)) for k in pending])
            again = []
            for k, r in zip(pending, res):
                o = r.outputs[0]
                tries[k] = tries.get(k, 0) + 1
                clean = o.finish_reason == "stop"
                if not clean and tries[k] <= a.redraws:
                    again.append(k)  # hit the limit: redraw from scratch
                    continue
                fh.write(json.dumps(dict(qid=k, text=o.text, n_out=len(o.token_ids), clean=clean, capped=not clean,
                                         tries=tries[k])) + "\n")
            fh.flush()
            pending = again
        print(f"  {min(c + a.chunk, len(keys))}/{len(keys)} written", flush=True)
    print("done: vllm_solve", flush=True)


if __name__ == "__main__":
    main()
