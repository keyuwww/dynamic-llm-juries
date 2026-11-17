"""Reasoning baseline: let each judge reason before its verdict, as the judge prompt asks ("Reason briefly, then end with
exactly one line VERDICT: ..."), instead of forcing "VERDICT:" right away as in the hidden-state study.
Greedy decoding, thinking off, at most 1536 reasoning tokens, stopping at "VERDICT:"; then one more step after
"<reasoning>VERDICT:" gives the verdict score log P(CORRECT) - log P(INCORRECT) (first tokens, as in the study; a token
missing from the top 20 gets the 20th log-probability minus 1).
Runs on the main answer pools of every stretched pair and on the same-model test sets.
-> out_allpairs/<judge>_<bench>/cot_<set>.jsonl  (aid, qid, gold, src, score, n_reason, reached)

  MODAL_PROFILE=ingridchien .venv/bin/modal run --detach experiments/beyond_capability/cot_modal.py [--sets main,sm,sm2]
"""
import gzip
import json
import pathlib

import modal

_here = pathlib.Path(__file__).resolve()
INP = _here.parent / "inputs"
MODELS = {"llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct", "llama3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
          "llama3.2-1b": "meta-llama/Llama-3.2-1B-Instruct", "phi4-mini": "microsoft/Phi-4-mini-instruct",
          "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3", "granite3.3-8b": "ibm-granite/granite-3.3-8b-instruct",
          "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct", "qwen3.5-4b": "Qwen/Qwen3.5-4B"}
PAIRS = {"llama3.1-8b": "mmlu math bbeh", "llama3.2-3b": "mmlu math bbeh", "phi4-mini": "mmlu math bbeh",
         "llama3.2-1b": "mmlu math bbeh", "mistral-7b": "mmlu math", "granite3.3-8b": "mmlu bbeh",
         "qwen2.5-7b": "mmlu bbeh", "qwen3.5-4b": "bbeh"}
MAIN = {"mmlu": "mmlu_full_items.jsonl.gz", "math": "math_full_items.jsonl.gz", "bbeh": "bbeh_items.jsonl.gz"}
FILES = list(MAIN.values()) + [f"{p}_{b}_items.jsonl.gz" for p in ("sm", "sm2") for b in ("mmlu", "math", "bbeh")]
image = modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.11").pip_install("vllm")
for f in FILES:
    if (INP / f).exists():
        image = image.add_local_file(INP / f, f"/root/inputs/{f}")
app = modal.App("dlj-cot-judge", image=image)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
CTX, REASON = 16384, 1536


@app.function(gpu="H100", timeout=6 * 3600, volumes={"/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def cot(judge: str, jobs: list, limit: int = 0, reason: int = REASON, ctx: int = CTX) -> dict:
    """jobs: [(bench, set_name, file)]; returns {f"{bench}|{set_name}": jsonl text}"""
    import math as _m

    from vllm import LLM, SamplingParams
    llm = LLM(MODELS[judge], max_model_len=ctx, gpu_memory_utilization=0.9, seed=0, enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    t1 = tok.encode(" CORRECT", add_special_tokens=False)[0]
    t2 = tok.encode(" INCORRECT", add_special_tokens=False)[0]
    out = {}
    for bench, sname, fname in jobs:
        rows = [json.loads(l) for l in gzip.open(f"/root/inputs/{fname}", "rt")]
        rows = [r for r in rows if r["mode"] == "J"][: limit or None]
        kw = {"enable_thinking": False} if "qwen3" in judge else {}
        P = [tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True, **kw) for r in rows]
        keep = [i for i, p in enumerate(P) if len(tok(p, add_special_tokens=False).input_ids) < ctx - reason - 16]
        g = llm.generate([P[i] for i in keep], SamplingParams(temperature=0, max_tokens=reason, stop=["VERDICT:"]))
        texts = [o.outputs[0] for o in g]
        P2 = [P[i] + o.text.rstrip() + ("\n" if o.text.strip() else "") + "VERDICT:" for i, o in zip(keep, texts)]
        v = llm.generate(P2, SamplingParams(temperature=0, max_tokens=1, logprobs=20))
        lines = []
        for i, o, vo in zip(keep, texts, v):
            lp = vo.outputs[0].logprobs[0]
            floor = min(x.logprob for x in lp.values()) - 1
            a, b = (lp[t].logprob if t in lp else floor for t in (t1, t2))
            r = rows[i]
            lines.append(json.dumps({k: r[k] for k in ("aid", "qid", "gold", "src")} | dict(
                score=float(a - b) if _m.isfinite(a - b) else 0.0, n_reason=len(o.token_ids),
                reached=o.finish_reason == "stop", both_top20=t1 in lp and t2 in lp)))
        out[f"{bench}|{sname}"] = "\n".join(lines) + "\n"
        print(f"{judge} {bench} {sname}: {len(lines)}/{len(rows)}", flush=True)
    return out


@app.local_entrypoint()
def main(sets: str = "main,sm", judges: str = "", limit: int = 0, smoke: bool = False, benches: str = "", reason: int = REASON,
         window: int = CTX):
    sets_ = sets.split(",")
    todo = []
    for j in (judges.split(",") if judges else MODELS):
        jobs = []
        for b in PAIRS[j].split():
            if benches and f"{j}:{b}" not in benches.split(",") and b not in benches.split(","):
                continue
            if "main" in sets_:
                jobs.append((b, "main", MAIN[b]))
            for s in ("sm", "sm2"):
                has_sm = (_here.parent / "out_allpairs" / f"{j}_{b}" / f"extra_{b}.jsonl").exists()
                if s in sets_ and (INP / f"{s}_{b}_items.jsonl.gz").exists() and has_sm:
                    jobs.append((b, s, f"{s}_{b}_items.jsonl.gz"))
        if jobs:
            todo.append((j, jobs))
    print(todo)
    if smoke:  # a few rows, printed, nothing saved
        for k, t in cot.remote(todo[0][0], todo[0][1][:1], limit or 40).items():
            R = [json.loads(l) for l in t.splitlines()]
            print(k, len(R), "reached", sum(r["reached"] for r in R), "both top20", sum(r["both_top20"] for r in R),
                  "mean reason tok", sum(r["n_reason"] for r in R) / len(R))
            print([(r["gold"], round(r["score"], 2)) for r in R[:20]])
        return
    for (j, _), res in zip(todo, cot.starmap([(j, jb, limit, reason, window) for j, jb in todo], return_exceptions=True)):
        if isinstance(res, Exception):
            print(f"{j}: FAILED {type(res).__name__}: {str(res)[:300]}", flush=True)
            continue
        for key, text in res.items():
            b, s = key.split("|")
            d = _here.parent / "out_allpairs" / f"{j}_{b}"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"cot_{s}.jsonl").write_text(text)
            print(f"saved {j} {b} {s}: {text.count(chr(10))} rows", flush=True)
