#!/usr/bin/env python3
"""
Step 0 of Trust / Read / Think: can a small Qwen judge finish its thinking, and which model should we use?

Isaac's self-agreement run dropped Qwen3.5-4B and 9B because they looped until the token limit with thinking on.
Before building the full three-read experiment we check, on 50 items from each of four benchmarks:
  cut off   share of thinking runs that hit the token cap without closing </think> and giving a verdict
  parsed    share that end with a readable "VERDICT: CORRECT / INCORRECT"
  accuracy  of the parsed verdicts against the labels (a first look, not the result)
  tokens    how long the thinking runs, so we can budget the full run

Benchmarks (two "recognize" tasks, two "solve" tasks), 25 prompts each with one good and one bad response:
  safety  RewardBench 2 Safety, team safety prompt (same items as the weight-space study)
  focus   RewardBench 2 Focus, generic single-response prompt
  math    RewardBench 2 Math, generic single-response prompt
  bff     BFF-Bench, team finance prompt (25 questions, one correct and one incorrect answer each)
Judges: Qwen3.5-0.8B and Qwen3.5-4B, native thinking on, Qwen's recommended thinking sampling (temperature 0.6,
top-p 0.95, top-k 20), at most 4,096 new tokens; we also report how many finish within 2,048.

  .venv/bin/python experiments/trust_read_think/pilot.py build
  modal run experiments/trust_read_think/pilot.py
  .venv/bin/python experiments/trust_read_think/pilot.py analyze
"""
import argparse, json, re, sys
from pathlib import Path

try:
    import modal
except ImportError:
    modal = None

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "raw" / "pilot"
WS = HERE.parent / "weight_space"
MODELS = ("Qwen/Qwen3.5-0.8B", "Qwen/Qwen3.5-4B")
N_GROUPS, MAX_NEW = 25, 4096


# ----------------------------------------------------------------------------- generation (Modal GPU, vLLM)
def gen_remote(model: str, items: list) -> list:
    from vllm import LLM, SamplingParams
    kw = dict(model=model, dtype="bfloat16", max_model_len=8192 + MAX_NEW, gpu_memory_utilization=0.9,
              enable_prefix_caching=True, seed=0, generation_config="vllm", max_num_seqs=64)
    try:
        llm = LLM(gdn_prefill_backend="triton", **kw)
    except TypeError:
        llm = LLM(**kw)
    tok = llm.get_tokenizer()
    prompts = []
    for it in items:
        p = tok.apply_chat_template([{"role": "user", "content": it["text"]}], tokenize=False,
                                    add_generation_prompt=True, enable_thinking=True)
        prompts.append(dict(prompt_token_ids=tok(p, add_special_tokens=False)["input_ids"][-8192:]))
    sp = SamplingParams(temperature=0.6, top_p=0.95, top_k=20, max_tokens=MAX_NEW, seed=0)
    outs = llm.generate(prompts, sp)
    return [dict(id=it["id"], model=model, text=o.outputs[0].text, n_tokens=len(o.outputs[0].token_ids),
                 finish=o.outputs[0].finish_reason) for it, o in zip(items, outs)]


def main():
    items = [json.loads(l) for l in open(OUT / "items.jsonl")]
    calls = [gen_remote.spawn(m, items) for m in MODELS]
    rows = []
    for m, c in zip(MODELS, calls):
        r = c.get()
        print(m, "done", len(r), flush=True)
        rows += r
    with open(OUT / "gen.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("saved", len(rows))


if modal is not None:
    image = (modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
             .apt_install("git", "ninja-build")
             .pip_install("vllm", "flash-linear-attention")
             .env({"HF_HOME": "/root/.cache/huggingface", "VLLM_USE_FLASHINFER_SAMPLER": "0"}))
    hf_cache = modal.Volume.from_name("dlj-hf-cache", create_if_missing=True)
    app = modal.App("trust-read-think-pilot", image=image)
    gen_remote = app.function(gpu=["L40S", "A100-40GB", "A10G"], timeout=3600,
                              volumes={"/root/.cache/huggingface": hf_cache})(gen_remote)
    main = app.local_entrypoint()(main)


# ----------------------------------------------------------------------------- items (local)
def build(a):
    import random
    from datasets import load_dataset
    sys.path.insert(0, str(WS))
    import smoke
    rng = random.Random(0)

    def pairs(items):
        by = {}
        for it in items:
            by.setdefault(it["group"], {})[it["gold"]] = it
        groups = sorted(g for g, d in by.items() if 0 in d and 1 in d)
        pick = rng.sample(groups, N_GROUPS)
        return [by[g][y] for g in pick for y in (1, 0)]

    out = []
    for c in ("safety", "bff"):
        items = [json.loads(l) for l in open(WS / "results" / "raw" / "module_map" / c / "items.jsonl")]
        for it in pairs(items):
            out.append(dict(id=f"{c}|{it['id']}", bench=c, group=f"{c}|{it['group']}", gold=it["gold"], text=it["text"]))
    rb2 = load_dataset("allenai/reward-bench-2", split="test")
    for c, sub in (("focus", "Focus"), ("math", "Math")):
        items = []
        for r in rb2:
            if r["subset"] != sub:
                continue
            for g, resp in ((1, r["chosen"][0]), (0, r["rejected"][0])):
                items.append(dict(id=f"{r['id']}|{g}", group=str(r["id"]), gold=g,
                                  text=smoke.SINGLE_JUDGE.format(prompt=str(r["prompt"]), response=str(resp))))
        for it in pairs(items):
            out.append(dict(id=f"{c}|{it['id']}", bench=c, group=f"{c}|{it['group']}", gold=it["gold"], text=it["text"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "items.jsonl", "w") as fh:
        for it in out:
            fh.write(json.dumps(it) + "\n")
    print(len(out), "items", {c: sum(it["bench"] == c for it in out) for c in ("safety", "focus", "math", "bff")})


# ----------------------------------------------------------------------------- analysis (local)
VERDICT = re.compile(r"VERDICT\s*:\s*\**\s*(CORRECT|INCORRECT)", re.I)


def parse(text):
    """Verdict from the answer after </think>; None if thinking never closed or no verdict line."""
    if "</think>" not in text:
        return None, False
    ans = text.split("</think>", 1)[1]
    m = VERDICT.findall(ans)
    return (int(m[-1].upper() == "CORRECT") if m else None), True


def analyze(a):
    import numpy as np
    items = {json.loads(l)["id"]: json.loads(l) for l in open(OUT / "items.jsonl")}
    rows = [json.loads(l) for l in open(OUT / "gen.jsonl")]
    summary = {}
    for m in MODELS:
        for c in ("safety", "focus", "math", "bff"):
            R = [r for r in rows if r["model"] == m and items[r["id"]]["bench"] == c]
            v = [parse(r["text"]) for r in R]
            closed = np.array([cl for _, cl in v])
            verd = [x for x, _ in v]
            ok = np.array([x is not None for x in verd])
            gold = np.array([items[r["id"]]["gold"] for r in R])
            pred = np.array([x if x is not None else -1 for x in verd])
            ntok = np.array([r["n_tokens"] for r in R])
            s = dict(n=len(R), cut_off=round(float((~closed).mean()), 3), parsed=round(float(ok.mean()), 3),
                     acc_parsed=round(float((pred[ok] == gold[ok]).mean()), 3) if ok.any() else None,
                     says_correct=round(float((pred[ok] == 1).mean()), 3) if ok.any() else None,
                     within_2048=round(float((closed & (ntok <= 2048)).mean()), 3),
                     tokens_median=int(np.median(ntok)), tokens_p90=int(np.percentile(ntok, 90)))
            summary[f"{m.split('/')[-1]}|{c}"] = s
            print(f"{m.split('/')[-1]:12s} {c:7s} cut_off {s['cut_off']:.2f} parsed {s['parsed']:.2f} "
                  f"acc {s['acc_parsed']} saysC {s['says_correct']} <=2048 {s['within_2048']:.2f} "
                  f"tokens med {s['tokens_median']} p90 {s['tokens_p90']}")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "pilot.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("analyze")
    a = ap.parse_args()
    {"build": build, "analyze": analyze}[a.cmd](a)
