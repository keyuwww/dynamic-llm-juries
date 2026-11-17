"""Reasoning baseline on a GPU node (same procedure as cot_modal.py): the judge reasons as its prompt asks (greedy, at
most --reason tokens, stopping at "VERDICT:"), then the verdict score is read after "<reasoning>VERDICT:".

  python cot_vllm.py --model meta-llama/Llama-3.1-70B-Instruct --tp 2 --items inputs/mmlu_full_items.jsonl.gz \
      --out out70b/llama3.1-70b_mmlu/cot_main.jsonl
"""
import argparse
import gzip
import json
import math


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--items", required=True, nargs="+")
    ap.add_argument("--out", required=True, nargs="+", help="one output file per items file")
    ap.add_argument("--tp", type=int, default=1)
    ap.add_argument("--reason", type=int, default=8192)
    ap.add_argument("--window", type=int, default=32768)
    a = ap.parse_args()
    assert len(a.items) == len(a.out)
    from vllm import LLM, SamplingParams
    llm = LLM(a.model, max_model_len=a.window, gpu_memory_utilization=0.92, seed=0, enable_prefix_caching=True,
              tensor_parallel_size=a.tp)
    tok = llm.get_tokenizer()
    t1 = tok.encode(" CORRECT", add_special_tokens=False)[0]
    t2 = tok.encode(" INCORRECT", add_special_tokens=False)[0]
    for fin, fout in zip(a.items, a.out):
        rows = [r for r in map(json.loads, gzip.open(fin, "rt")) if r["mode"] == "J"]
        P = [tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True) for r in rows]
        keep = [i for i, p in enumerate(P) if len(tok(p, add_special_tokens=False).input_ids) < a.window - a.reason - 16]
        g = llm.generate([P[i] for i in keep], SamplingParams(temperature=0, max_tokens=a.reason, stop=["VERDICT:"]))
        texts = [o.outputs[0] for o in g]
        P2 = [P[i] + o.text.rstrip() + ("\n" if o.text.strip() else "") + "VERDICT:" for i, o in zip(keep, texts)]
        v = llm.generate(P2, SamplingParams(temperature=0, max_tokens=1, logprobs=20))
        with open(fout, "w") as fh:
            for i, o, vo in zip(keep, texts, v):
                lp = vo.outputs[0].logprobs[0]
                floor = min(x.logprob for x in lp.values()) - 1
                x1, x2 = (lp[t].logprob if t in lp else floor for t in (t1, t2))
                r = rows[i]
                fh.write(json.dumps({k: r[k] for k in ("aid", "qid", "gold", "src")} | dict(
                    score=float(x1 - x2) if math.isfinite(x1 - x2) else 0.0, n_reason=len(o.token_ids),
                    reached=o.finish_reason == "stop", both_top20=t1 in lp and t2 in lp)) + "\n")
        print(f"{fout}: {len(keep)}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
