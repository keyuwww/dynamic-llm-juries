"""The add-on juror gpt-oss-safeguard-20b, run with vLLM on Modal, used only to fill missing rows of the safeguard stage.
As shipped nothing is missing, so nothing here runs: modal is imported inside the functions that call it.

One model load serves every prompt, each with its own sampling settings (gut: 1 token with the top 20 log-probabilities,
reasoned: up to 4,096 tokens), both at temperature 0 with seed 0, on one L40S GPU. Results stream back chunk by chunk, and
each chunk goes to on_chunk at once so it can be saved. A wall-clock deadline, load included, stops the call between chunks.
Cost is wall time times the GPU's hourly price, added to .spend/spend.json under "modal" as it accrues. The call is refused
if the deadline's worst case would take that total past the cap, $4 as in the original run.

It copies the original runner (one vLLM load, per-prompt settings, streamed chunks) with the same image, vLLM settings
(gpu_memory_utilization 0.90, max_model_len 16000, raw prompts, special tokens kept) and log-probability format. It needs the
modal package and a Modal account (`modal token new`). The weights are cached in a Modal volume named "hf-weights".
"""
from __future__ import annotations

import sys
import time

from .tinker_client import BudgetStop, charge, spent

GPU_PRICE = {"T4": 0.59, "L4": 0.80, "A10G": 1.10, "L40S": 1.95, "A100-40GB": 2.10, "A100-80GB": 2.50, "H100": 3.95}   # $ per hour
APP_NAME = "self-agreement-safeguard"
_modal: dict = {}


def _multi(model_id, jobs, deadline_s, chunk, max_model_len=16000, llm_kwargs=None):
    """Runs inside the Modal container: load once, then the fast jobs (max_tokens 1) in one chunk, then the rest in chunks."""
    import time as _t
    t0 = _t.time()
    from vllm import LLM, SamplingParams
    llm = LLM(model=model_id, max_model_len=max_model_len, gpu_memory_utilization=0.90, trust_remote_code=True, **(llm_kwargs or {}))
    yield dict(event="loaded", t=_t.time() - t0)
    nfast = sum(1 for j in jobs if j["sp"].get("max_tokens") == 1)
    bounds = [(0, nfast)] if nfast else []
    s = nfast
    while s < len(jobs):
        bounds.append((s, min(len(jobs), s + chunk))); s += chunk
    for a, b in bounds:
        if _t.time() - t0 > deadline_s:
            yield dict(event="deadline", done=a, t=_t.time() - t0); return
        part = jobs[a:b]
        sps = [SamplingParams(skip_special_tokens=False, **j["sp"]) for j in part]
        outs = llm.generate([j["prompt"] for j in part], sps, use_tqdm=False)
        res = []
        for j, o in zip(part, outs):
            cands = []
            for c in o.outputs:
                d = dict(text=c.text, finish=c.finish_reason, n_out=len(c.token_ids))
                if j["sp"].get("logprobs") and c.logprobs:
                    d["token_logprobs"] = [[lp[t].decoded_token, lp[t].logprob, {v.decoded_token: v.logprob for v in lp.values()}]
                                           for t, lp in zip(c.token_ids, c.logprobs)]
                cands.append(d)
            res.append(dict(key=j["key"], n_prompt=len(o.prompt_token_ids), samples=cands))
        yield dict(event="chunk", a=a, b=b, res=res, t=_t.time() - t0)
    yield dict(event="done", t=_t.time() - t0)


def _app():
    """The Modal app, image and weights volume, built on first use."""
    if not _modal:
        import modal
        from modal._vendor import cloudpickle
        cloudpickle.register_pickle_by_value(sys.modules[__name__])   # ship _multi by value (this file is not in the image)
        image = (modal.Image.debian_slim(python_version="3.12")
                 .pip_install("vllm>=0.10.2", "huggingface_hub[hf_transfer]>=0.34")
                 .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0"}))
        _modal.update(modal=modal, app=modal.App(APP_NAME), image=image, fns={},
                      weights=modal.Volume.from_name("hf-weights", create_if_missing=True))
    return _modal


def _fn(gpu):
    M = _app()
    if gpu not in M["fns"]:
        M["fns"][gpu] = M["app"].function(image=M["image"], gpu=gpu, volumes={"/root/.cache/huggingface": M["weights"]},
                                          timeout=3 * 3600, serialized=True, name=f"multi_{gpu.lower().replace('-', '_')}")(_multi)
    return M["fns"][gpu]


def run(model_id, jobs, on_chunk, gpu="L40S", deadline_s=2400, chunk=200, cap=4.0, llm_kwargs=None, note="safeguard"):
    """jobs: list of dict(key, prompt, sp). on_chunk(list of results) is called as each chunk returns. Each result is
    dict(key, n_prompt, samples=[dict(text, finish, n_out, token_logprobs?)]). Returns the dollars charged."""
    price = GPU_PRICE[gpu]
    worst = price * (deadline_s + 900) / 3600          # the deadline plus the last chunk's tail (up to 15 min)
    if spent("modal") + worst > cap:
        raise BudgetStop(f"modal: spent ${spent('modal'):.2f} + worst case ${worst:.2f} would pass the ${cap:.2f} cap")
    M = _app(); f = _fn(gpu)
    t0 = last = time.time(); total = 0.0

    def bill():
        nonlocal last, total
        now = time.time(); c = price * (now - last) / 3600; last = now; total += c
        charge(c, provider="modal")
    try:
        with M["modal"].enable_output(), M["app"].run():
            for ev in f.remote_gen(model_id, jobs, deadline_s, chunk, 16000, llm_kwargs):
                if ev["event"] == "chunk":
                    on_chunk(ev["res"])
                    print(f"[{time.time() - t0:7.0f}s] chunk {ev['a']}-{ev['b']} of {len(jobs)} (server {ev['t']:.0f}s)", flush=True)
                else:
                    print(f"[{time.time() - t0:7.0f}s] {ev}", flush=True)
                bill()
    finally:
        bill()
        print(f"{note}: charged ${total:.3f} for {model_id} on {gpu} ({time.time() - t0:.0f}s)", flush=True)
    return total
