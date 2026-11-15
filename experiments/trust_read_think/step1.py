#!/usr/bin/env python3
"""
Step 1 of Trust / Read / Think: three reads of the same judge (Qwen3.5-4B) on every item.

  Trust  the gut verdict: thinking off, "VERDICT:" prefilled, P(CORRECT) from the next token (" COR" vs " INC").
  Read   the hidden state at that same position, every layer (a probe is trained on it later, in Step 2).
  Think  thinking on (Qwen's thinking sampling, at most 4,096 new tokens). Budget forcing: at each budget
         B in 512 / 1,024 / 2,048 / 4,096 we cut the thinking at B tokens (or keep it if it ended sooner), close it
         with "</think>", prefill "VERDICT:" and read P(CORRECT) the same way. So every item gets a reasoned verdict
         at every budget, and nothing is lost to the cap. The model's own written verdict is kept too.

Benchmarks (two "recognize" tasks, two "solve" tasks):
  safety  RewardBench 2 Safety, team safety prompt: 150 prompts x (good, bad)       strata = resp_model|refusal
  focus   RewardBench 2 Focus, generic prompt: 150 prompts x (chosen[0], rejected[0])  strata = prompt
  math    RewardBench 2 Math, generic prompt: 150 prompts x (chosen[0], rejected[0])   strata = prompt
  bff     BFF-Bench, team finance prompt: all 459 graded answers                        strata = examinee

  .venv/bin/python experiments/trust_read_think/step1.py build
  modal run experiments/trust_read_think/step1.py --limit 4        # smoke test
  modal run experiments/trust_read_think/step1.py --model Qwen/Qwen3.5-9B   # another judge (own folder)
  modal run --detach experiments/trust_read_think/step1.py --model ...      # keeps running if the laptop sleeps
  modal run experiments/trust_read_think/step1.py::fetch --model ...        # then download the results
  modal run experiments/trust_read_think/step1.py
  .venv/bin/python experiments/trust_read_think/step1.py analyze
"""
import argparse, json, re, sys
from pathlib import Path

try:
    import modal
except ImportError:
    modal = None

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "raw" / "step1"
WS = HERE.parent / "weight_space"
MODEL = "Qwen/Qwen3.5-4B"           # default judge; pass --model for another
BENCHES = ("safety", "focus", "math", "bff")
N_GROUPS = 150
MAX_PROMPT, MAX_NEW = 8192, 4096
BUDGETS = (512, 1024, 2048, 4096)


def judge(model: str) -> str:
    """Folder name for a judge, e.g. Qwen/Qwen3.5-9B -> qwen3.5-9b (matches paths.JUDGES)."""
    return model.split("/")[-1].lower()


# How each judge family turns thinking off / on and how a thinking run is closed for a forced verdict.
#   gut_sys / think_sys  system message (None: no system message)
#   gut_kw / think_kw    extra chat-template arguments
#   gut_suffix           appended after the generation prompt for the thinking-off verdict
#   end                  marker that ends the thinking; cut = appended when thinking is cut at a budget,
#                        nat = appended after the marker when thinking ended on its own
_QWEN = dict(cls="image", gpu="L40S", gut_sys=None, think_sys=None, gut_kw=dict(enable_thinking=False),
             think_kw=dict(enable_thinking=True), gut_suffix="VERDICT:", end="</think>",
             cut="\n</think>\n\nVERDICT:", nat="\n\nVERDICT:", samp=dict(temperature=0.6, top_p=0.95, top_k=20),
             skip_special=True, llm_kw={})
SPECS = {
    "qwen3.5-4b": _QWEN, "qwen3.5-9b": _QWEN,
    # OpenAI harmony format: hidden "analysis" channel = thinking, "final" channel = answer. Gut: jump straight to final.
    "gpt-oss-20b": dict(cls="causal", gpu="H100", gut_sys=None, think_sys=None, gut_kw={}, think_kw={},
                        gut_suffix="<|channel|>final<|message|>VERDICT:", end="<|end|>",
                        cut="<|end|><|start|>assistant<|channel|>final<|message|>VERDICT:",
                        nat="<|start|>assistant<|channel|>final<|message|>VERDICT:",
                        samp=dict(temperature=1.0, top_p=1.0), skip_special=False, llm_kw={}),
    # NVIDIA Nemotron-H (hybrid Mamba-Transformer): thinking switched by the system message /think or /no_think.
    "nvidia-nemotron-nano-9b-v2": dict(cls="causal", gpu="L40S", gut_sys="/no_think", think_sys="/think", gut_kw={},
                                       think_kw={}, gut_suffix="VERDICT:", end="</think>",
                                       cut="\n</think>\n\nVERDICT:", nat="\n\nVERDICT:",
                                       end_match="</think",   # "</think>" is 3 tokens and can merge with "\n"
                                       samp=dict(temperature=0.6, top_p=0.95), skip_special=False,
                                       llm_kw=dict(trust_remote_code=True, mamba_ssm_cache_dtype="float32")),
}


def messages(spec, text, mode):
    sys_msg = spec["gut_sys" if mode == "gut" else "think_sys"]
    return ([{"role": "system", "content": sys_msg}] if sys_msg else []) + [{"role": "user", "content": text}]


def find_sub(seq, sub):
    for i in range(len(seq) - len(sub) + 1):
        if seq[i:i + len(sub)] == sub:
            return i
    return None


# ----------------------------------------------------------------------------- Trust + Read (Modal GPU, transformers)
def fast_remote(bench: str, texts: list, tag: str, model_name: str = MODEL) -> str:
    """Thinking-off forced verdict: P(CORRECT) and the residual stream at the verdict position, all layers."""
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer
    spec = SPECS[judge(model_name)]
    tok = AutoTokenizer.from_pretrained(model_name)
    cls = AutoModelForImageTextToText if spec["cls"] == "image" else AutoModelForCausalLM
    model = cls.from_pretrained(model_name, dtype=torch.bfloat16).to("cuda").eval()
    pos, neg = tok.encode(" CORRECT", add_special_tokens=False)[0], tok.encode(" INCORRECT", add_special_tokens=False)[0]
    N = len(texts)
    HS, P, MASS = None, np.zeros(N, np.float32), np.zeros(N, np.float32)
    for k, text in enumerate(texts):
        prompt = tok.apply_chat_template(messages(spec, text, "gut"), tokenize=False, add_generation_prompt=True,
                                         **spec["gut_kw"]) + spec["gut_suffix"]
        ids = tok(prompt, add_special_tokens=False)["input_ids"][-MAX_PROMPT:]
        with torch.no_grad():
            o = model(input_ids=torch.tensor([ids], device="cuda"), output_hidden_states=True, logits_to_keep=1,
                      use_cache=False)
        lp = torch.log_softmax(o.logits[0, -1].float(), -1)
        P[k] = float(torch.sigmoid(lp[pos] - lp[neg]))
        MASS[k] = float(lp[pos].exp() + lp[neg].exp())
        hs = torch.stack([h[0, -1] for h in o.hidden_states]).float().cpu().numpy()
        if HS is None:
            HS = np.zeros((N,) + hs.shape, np.float16)
        HS[k] = hs
        if (k + 1) % 100 == 0:
            print(f"fast {bench}: {k + 1}/{N}", flush=True)
    path = f"/vol/{judge(model_name)}_{tag}{bench}_fast.npz"
    np.savez(path, hs=HS, p=P, mass=MASS)
    vol.commit()
    return path


# ----------------------------------------------------------------------------- Think (Modal GPU, vLLM)
def think_remote(bench: str, texts: list, model_name: str = MODEL, item_ids: list = None, tag: str = "") -> list:
    import math
    from vllm import LLM, SamplingParams
    spec = SPECS[judge(model_name)]
    kw = dict(model=model_name, **spec["llm_kw"], dtype="bfloat16", max_model_len=MAX_PROMPT + MAX_NEW + 64, gpu_memory_utilization=0.9,
              enable_prefix_caching=True, seed=0, generation_config="vllm", max_num_seqs=64)
    try:
        llm = LLM(gdn_prefill_backend="triton", **kw)
    except TypeError:
        llm = LLM(**kw)
    tok = llm.get_tokenizer()
    pos, neg = tok.encode(" CORRECT", add_special_tokens=False)[0], tok.encode(" INCORRECT", add_special_tokens=False)[0]
    end_ids = tok.encode(spec.get("end_match", spec["end"]), add_special_tokens=False)   # marks the end of thinking
    close_cut = tok.encode(spec["cut"], add_special_tokens=False)                # thinking cut at the budget
    close_nat = tok.encode(spec["nat"], add_special_tokens=False)                # thinking ended on its own

    prompts = []
    for text in texts:
        p = tok.apply_chat_template(messages(spec, text, "think"), tokenize=False, add_generation_prompt=True,
                                    **spec["think_kw"])
        prompts.append(tok(p, add_special_tokens=False)["input_ids"][-MAX_PROMPT:])
    sp = SamplingParams(**spec["samp"], max_tokens=MAX_NEW, seed=0, skip_special_tokens=spec["skip_special"])
    outs = llm.generate([dict(prompt_token_ids=p) for p in prompts], sp)

    rows, forced, where = [], [], []
    for i, (p, o) in enumerate(zip(prompts, outs)):
        gen = list(o.outputs[0].token_ids)
        t_end = find_sub(gen, end_ids)                               # thinking length if it closed
        answer = tok.decode(gen[t_end + len(end_ids):], skip_special_tokens=False) if t_end is not None else ""
        rows.append(dict(text=o.outputs[0].text, answer=answer, n_tokens=len(gen), finish=o.outputs[0].finish_reason,
                         think_tokens=t_end if t_end is not None else len(gen), closed=t_end is not None))
        for B in BUDGETS:
            if t_end is not None and t_end < B:
                # ended on its own: keep the thinking (with its own marker), or, for multi-token markers, cut just
                # before the marker and close it ourselves
                ids = p + (gen[:t_end] + close_cut if "end_match" in spec else gen[:t_end + len(end_ids)] + close_nat)
            else:
                ids = p + gen[:B] + close_cut
            forced.append(dict(prompt_token_ids=ids))
            where.append((i, B))
    # one forced next token; top-20 log-probs (a word missing from the top 20 gets the 20th log-prob as a ceiling)
    fo = llm.generate(forced, SamplingParams(max_tokens=1, temperature=0.0, logprobs=20))
    for (i, B), o in zip(where, fo):
        lp = o.outputs[0].logprobs[0]
        floor = min(v.logprob for v in lp.values())
        a, b = (lp[t].logprob if t in lp else floor for t in (pos, neg))
        rows[i].setdefault("p_budget", {})[str(B)] = 1 / (1 + math.exp(b - a))
        rows[i].setdefault("mass_budget", {})[str(B)] = math.exp(a) + math.exp(b)
    if item_ids is not None:      # save on the volume too, so a detached run survives the laptop disconnecting
        import json as _j
        with open(f"/vol/{judge(model_name)}_{tag}{bench}_think.jsonl", "w") as fh:
            for i, r in zip(item_ids, rows):
                fh.write(_j.dumps(dict(id=i, **r)) + "\n")
        vol.commit()
    return rows


def main(limit: int = 0, which: str = "fast,think", benches: str = ",".join(BENCHES) + ",factuality",
         items_file: str = "items.jsonl,items_factuality.jsonl",
         model: str = MODEL):
    tag = "smoke_" if limit else ""
    dest_dir = OUT / judge(model)
    dest_dir.mkdir(parents=True, exist_ok=True)
    print("judge", model, "->", dest_dir, flush=True)
    which = which.split(",")
    items = [json.loads(l) for f in items_file.split(",") for l in open(OUT / f)]
    jobs = []
    for b in benches.split(","):
        sub = [it for it in items if it["bench"] == b]
        sub = sub[:limit] if limit else sub
        texts = [it["text"] for it in sub]
        print(f"{b}: {len(sub)} items -> Modal", flush=True)
        if "fast" in which:
            jobs.append(("fast", b, sub, fast_remote.with_options(gpu=SPECS[judge(model)]["gpu"])
                         .spawn(b, texts, tag, model)))
        if "think" in which:
            jobs.append(("think", b, sub, think_remote.with_options(gpu=SPECS[judge(model)]["gpu"])
                         .spawn(b, texts, model, [it["id"] for it in sub], tag)))
    for kind, b, sub, job in jobs:
        res = job.get()
        if kind == "fast":
            dest = dest_dir / f"{tag}{b}_fast.npz"
            with open(dest, "wb") as fh:
                for chunk in vol.read_file(Path(res).name):
                    fh.write(chunk)
            print(f"{b}: saved {dest.name} ({dest.stat().st_size / 1e6:.0f} MB)", flush=True)
        else:
            with open(dest_dir / f"{tag}{b}_think.jsonl", "w") as fh:
                for it, r in zip(sub, res):
                    fh.write(json.dumps(dict(id=it["id"], **r)) + "\n")
            print(f"{b}: saved {tag}{b}_think.jsonl ({len(res)} rows)", flush=True)


def fetch(model: str = MODEL, smoke: bool = False, benches: str = ",".join(BENCHES) + ",factuality"):
    """Download a judge's saved reads from the Modal volume (after a detached run)."""
    tag = "smoke_" if smoke else ""
    dest_dir = OUT / judge(model)
    dest_dir.mkdir(parents=True, exist_ok=True)
    have = {e.path for e in vol.listdir("/")}
    for b in benches.split(","):
        for kind in ("fast.npz", "think.jsonl"):
            name = f"{judge(model)}_{tag}{b}_{kind}"
            if name not in have:
                print(f"missing {name} (not finished yet?)", flush=True)
                continue
            with open(dest_dir / f"{tag}{b}_{kind}", "wb") as fh:
                for chunk in vol.read_file(name):
                    fh.write(chunk)
            print(f"saved {dest_dir.name}/{tag}{b}_{kind}", flush=True)


if modal is not None:
    hf_cache = modal.Volume.from_name("dlj-hf-cache", create_if_missing=True)
    vol = modal.Volume.from_name("trust-read-think", create_if_missing=True)
    app = modal.App("trust-read-think-step1")
    hf_image = (modal.Image.debian_slim(python_version="3.12")
                .pip_install("torch==2.15.0", "transformers==5.22.2", "numpy==2.5.4", "accelerate")
                .env({"HF_HOME": "/root/.cache/huggingface"}))
    vllm_image = (modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
                  .apt_install("git", "ninja-build")
                  .pip_install("vllm", "flash-linear-attention")
                  .env({"HF_HOME": "/root/.cache/huggingface", "VLLM_USE_FLASHINFER_SAMPLER": "0"}))
    fast_remote = app.function(image=hf_image, gpu=["L40S", "A100-40GB"], timeout=3 * 3600,
                               volumes={"/root/.cache/huggingface": hf_cache, "/vol": vol})(fast_remote)
    think_remote = app.function(image=vllm_image, gpu=["L40S", "A100-40GB"], timeout=3 * 3600,
                                volumes={"/root/.cache/huggingface": hf_cache, "/vol": vol})(think_remote)
    main = app.local_entrypoint()(main)
    fetch = app.local_entrypoint()(fetch)


# ----------------------------------------------------------------------------- items (local)
def build(a):
    import random
    from datasets import load_dataset
    sys.path.insert(0, str(WS))
    import smoke
    rng = random.Random(1)

    def pairs(items, n):
        by = {}
        for it in items:
            by.setdefault(it["group"], {})[it["gold"]] = it
        groups = sorted(g for g, d in by.items() if 0 in d and 1 in d)
        return [by[g][y] for g in rng.sample(groups, min(n, len(groups))) for y in (1, 0)]

    out = []
    ws = lambda c: [json.loads(l) for l in open(WS / "results" / "raw" / "module_map" / c / "items.jsonl")]
    for it in pairs(ws("safety"), N_GROUPS):
        out.append(dict(id=f"safety|{it['id']}", bench="safety", group=f"safety|{it['group']}", gold=it["gold"],
                        strata=f"{it['resp_model']}|{it['refusal']}", text=it["text"]))
    rb2 = load_dataset("allenai/reward-bench-2", split="test")
    for c, sub in (("focus", "Focus"), ("math", "Math")):
        items = [dict(id=f"{r['id']}|{g}", group=str(r["id"]), gold=g,
                      text=smoke.SINGLE_JUDGE.format(prompt=str(r["prompt"]), response=str(resp)))
                 for r in rb2 if r["subset"] == sub for g, resp in ((1, r["chosen"][0]), (0, r["rejected"][0]))]
        for it in pairs(items, N_GROUPS):
            out.append(dict(id=f"{c}|{it['id']}", bench=c, group=f"{c}|{it['group']}", gold=it["gold"],
                            strata=f"{c}|{it['group']}", text=it["text"]))
    for it in ws("bff"):
        out.append(dict(id=f"bff|{it['id']}", bench="bff", group=f"bff|{it['group']}", gold=it["gold"],
                        strata=it["examinee"], text=it["text"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "items.jsonl", "w") as fh:
        for it in out:
            fh.write(json.dumps(it) + "\n")
    print(len(out), "items", {c: sum(it["bench"] == c for it in out) for c in BENCHES})


def build_heldout(a):
    """Held-out benchmark, never used to design anything: RewardBench 2 Factuality, 150 prompts x (chosen[0], rejected[0])."""
    import random
    from datasets import load_dataset
    sys.path.insert(0, str(WS))
    import smoke
    rng = random.Random(2)
    rb2 = load_dataset("allenai/reward-bench-2", split="test")
    rows = [r for r in rb2 if r["subset"] == "Factuality"]
    out = []
    for r in rng.sample(rows, N_GROUPS):
        for g, resp in ((1, r["chosen"][0]), (0, r["rejected"][0])):
            out.append(dict(id=f"factuality|{r['id']}|{g}", bench="factuality", group=f"factuality|{r['id']}", gold=g,
                            strata=f"factuality|{r['id']}",
                            text=smoke.SINGLE_JUDGE.format(prompt=str(r["prompt"]), response=str(resp))))
    with open(OUT / "items_factuality.jsonl", "w") as fh:
        for it in out:
            fh.write(json.dumps(it) + "\n")
    print(len(out), "factuality items")


# ----------------------------------------------------------------------------- analysis (local)
VERDICT = re.compile(r"VERDICT\s*:\s*\**\s*(CORRECT|INCORRECT)", re.I)


def written_verdict(text, answer=None):
    if answer is not None:
        m = VERDICT.findall(answer)
        return int(m[-1].upper() == "CORRECT") if m else None
    if "</think>" not in text:
        return None
    m = VERDICT.findall(text.split("</think>", 1)[1])
    return int(m[-1].upper() == "CORRECT") if m else None


def strata_auc(score, gold, strata):
    """Mean AUROC within strata that contain both labels, weighted by pairs (same-source AUROC)."""
    import numpy as np
    num = den = 0.0
    for s in set(strata):
        m = np.array([x == s for x in strata])
        pos, neg = score[m & (gold == 1)], score[m & (gold == 0)]
        if len(pos) and len(neg):
            w = len(pos) * len(neg)
            num += w * ((pos[:, None] > neg[None]).mean() + 0.5 * (pos[:, None] == neg[None]).mean())
            den += w
    return num / den if den else float("nan")


def analyze(a):
    import numpy as np
    tag = "smoke_" if a.smoke else ""
    import os
    jd = OUT / os.environ.get("JUDGE", "qwen3.5-4b")
    items = [json.loads(l) for l in open(OUT / "items.jsonl")]
    summary = {}
    for b in BENCHES:
        th = {json.loads(l)["id"]: json.loads(l) for l in open(jd / f"{tag}{b}_think.jsonl")}
        sub = [it for it in items if it["id"] in th]
        fast = np.load(jd / f"{tag}{b}_fast.npz")
        n = len(sub)
        gold = np.array([it["gold"] for it in sub])
        strata = [it["strata"] for it in sub]
        gut = fast["p"][:n]
        T = [th[it["id"]] for it in sub]
        s = dict(n=n, says_correct_rate=round(float(gut.mean()), 3),
                 gut_auc=round(strata_auc(gut, gold, strata), 3),
                 gut_acc=round(float(((gut > 0.5) == gold).mean()), 3),
                 gut_mass=round(float(fast["mass"][:n].mean()), 3),
                 closed=round(float(np.mean([t["closed"] for t in T])), 3),
                 think_tokens_median=int(np.median([t["think_tokens"] for t in T])))
        for B in BUDGETS:
            pb = np.array([t["p_budget"][str(B)] for t in T])
            s[f"think_auc_{B}"] = round(strata_auc(pb, gold, strata), 3)
            s[f"think_acc_{B}"] = round(float(((pb > 0.5) == gold).mean()), 3)
            s[f"agree_{B}"] = round(float(((pb > 0.5) == (gut > 0.5)).mean()), 3)
            s[f"mass_{B}"] = round(float(np.mean([t["mass_budget"][str(B)] for t in T])), 3)
        wv = [written_verdict(t["text"], t.get("answer")) for t in T]
        ok = np.array([v is not None for v in wv])
        s["written_parsed"] = round(float(ok.mean()), 3)
        pf = np.array([t["p_budget"]["4096"] > 0.5 for t in T])
        s["written_vs_forced_agree"] = round(float(np.mean([v == f for v, f, o in zip(wv, pf, ok) if o])), 3) \
            if ok.any() else None
        summary[b] = s
        print(b, json.dumps(s))
    (HERE / "results" / jd.name).mkdir(parents=True, exist_ok=True)
    (HERE / "results" / jd.name / f"{tag}step1.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("build_heldout")
    an = sub.add_parser("analyze")
    an.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    {"build": build, "build_heldout": build_heldout, "analyze": analyze}[a.cmd](a)
