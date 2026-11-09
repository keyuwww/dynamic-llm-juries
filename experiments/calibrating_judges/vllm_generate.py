#!/usr/bin/env python
"""Fast generation of the judge's reasoning + verdict with vLLM (same prompts, same parser as generate_judge.py).

vLLM only produces the text; the judge's activations are read afterwards with acts_from_gen.py, one forward pass over the exact sampled tokens.
Output: <out>/<tag>_gen.jsonl with one row per item and sample (item_id, group, sample, gold, verdict, correct, confidence, n_tokens, truncated, text);
for n-samples 1 the row also carries token_ids (needed by acts_from_gen.py)."""
import argparse, json, os, time
import numpy as np, pandas as pd
from judge_data import load_items
from prompts import build_prompt
from generate_judge import parse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--bench", required=True, choices=["bff", "rb2safety", "judgebench", "ppe_correct", "ppe_pref"])
    ap.add_argument("--data"); ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--jb-dir")
    ap.add_argument("--prompt", default="uncertainty", choices=["uncertainty", "confidence"]); ap.add_argument("--n-samples", type=int, default=1); ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-new-tokens", type=int, default=4096); ap.add_argument("--max-len", type=int, default=8192); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--offset", type=int, default=0, help="start at this item (to shard a long run over several GPUs)")
    ap.add_argument("--gpu-mem", type=float, default=0.9); ap.add_argument("--max-num-seqs", type=int, default=0, help="0 = vLLM default; hybrid Mamba models need a lower cap"); ap.add_argument("--tp", type=int, default=1); ap.add_argument("--out", default="gen"); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    from vllm import LLM, SamplingParams
    items = load_items(a.bench, a.data, a.verdicts_path, a.rb2_path, a.jb_dir)
    items = items[a.offset:a.offset + a.limit] if a.limit else items[a.offset:]
    tag = f"{a.model.split('/')[-1]}__{a.bench}__{a.prompt}__n{a.n_samples}_t{a.temperature}" + (f"__off{a.offset}" if a.offset else ""); os.makedirs(a.out, exist_ok=True)
    kw = dict(model=a.model, trust_remote_code=True, dtype="bfloat16", max_model_len=a.max_len + a.max_new_tokens, gpu_memory_utilization=a.gpu_mem,
              tensor_parallel_size=a.tp, enable_prefix_caching=True, seed=a.seed, generation_config="vllm", **(dict(max_num_seqs=a.max_num_seqs) if a.max_num_seqs else {}))   # "vllm": do not pick up the model's own default top_k / top_p
    try:
        llm = LLM(gdn_prefill_backend="triton", **kw)                                                        # triton kernel instead of a JIT-compiled FlashInfer one
    except TypeError:
        llm = LLM(**kw)
    tok = llm.get_tokenizer()

    def templ(text):
        msgs = [dict(role="user", content=text)]
        if getattr(tok, "chat_template", None) is None:
            return text
        try:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    prompt_ids = []
    for it in items:
        ids = tok(templ(build_prompt(a.bench, a.prompt, it)), add_special_tokens=False)["input_ids"]
        prompt_ids.append(ids[-a.max_len:])                                   # left truncation, as in generate_judge.py
    print(f"[{tag}] {len(items)} items; prompt tokens mean {np.mean([len(p) for p in prompt_ids]):.0f} max {max(len(p) for p in prompt_ids)}", flush=True)
    sp = SamplingParams(n=a.n_samples, temperature=a.temperature, top_p=1.0, top_k=-1, max_tokens=a.max_new_tokens, seed=a.seed)
    t0 = time.time(); outs = llm.generate([dict(prompt_token_ids=p) for p in prompt_ids], sp); dt = time.time() - t0
    rows, n_tok = [], 0
    for it, o in zip(items, outs):
        for s, c in enumerate(o.outputs):
            v, conf = parse(c.text, a.bench); n_tok += len(c.token_ids)
            r = dict(item_id=it["item_id"], group=it["group"], sample=s, gold=it["gold"], verdict=v, correct=int(v == it["gold"]) if v is not None else 0, confidence=conf,
                     n_tokens=len(c.token_ids), truncated=bool(c.finish_reason == "length"), finish_reason=c.finish_reason, text=c.text)
            if a.n_samples == 1:
                r["token_ids"] = list(map(int, c.token_ids))
            rows.append(r)
    df = pd.DataFrame(rows); df.to_json(os.path.join(a.out, f"{tag}_gen.jsonl"), orient="records", lines=True)
    print(f"generated {n_tok} tokens in {dt:.0f}s ({n_tok / dt:.0f} tok/s)  parsed {df.verdict.notna().mean():.3f}  truncated {df.truncated.mean():.3f}  "
          f"verdict accuracy {df.correct.mean():.3f}  mean tokens {df.n_tokens.mean():.0f}\nsaved {tag}", flush=True)


if __name__ == "__main__":
    main()
