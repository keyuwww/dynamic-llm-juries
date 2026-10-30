"""Model calls on Tinker (Thinking Machines), used only to fill rows missing from runs/. As shipped nothing is missing, so
nothing here runs: tinker is imported inside the functions that call it, never when this file is imported.

Three calls cover the experiment:
  sample(model, prompts, max_tokens, ...)   one continuation of each raw prompt string at temperature 0 (reasoned reads,
                                             self-solve, the grader). topk_logprobs=1 also returns the sampled token's log-probability.
  gut_oss(model, prompts)                   gpt-oss gut read: one token, its log-probability turned into a margin (prompts.m1_from).
  verdict_margin(model, prefixes)           Qwen and Nemotron gut read: log P(" INCORRECT") minus log P(" CORRECT") right after
                                             "VERDICT:", each the summed log-probability of the word's tokens. Above 0 is a reject.
render(model, messages, **kwargs) applies the model's chat template, for example enable_thinking=False for Qwen. Token
budgets per model live in lib/run_stages.py.

Key: TINKER_API_KEY, from the environment or a .env file in this folder (copy .env.example). An existing variable wins.
Spend: every call is costed from its token counts at Tinker's list prices and added to .spend/spend.json. A chunk of calls
that would take the total past CAP is refused (BudgetStop). CAP is $35, the original run's cap. The original run spent
$15.77 of it, but the file here starts at $0 and counts only calls made from this folder. As in the original run, graders
without a list price are costed at an estimated $1 in and $3 out per million tokens. Delete .spend/ to reset.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from . import prompts as P

ROOT = Path(__file__).resolve().parents[1]
SPEND = ROOT / ".spend" / "spend.json"
CAP = 35.00   # $ of Tinker spend from this folder, across every run
PRICE = {     # $ per million tokens (in, out), Tinker's list prices as used on Oct 24, 2026
    "openai/gpt-oss-20b": (0.18, 0.45), "openai/gpt-oss-120b": (0.33, 0.84),
    "Qwen/Qwen3.5-4B": (0.33, 1.005), "Qwen/Qwen3.5-9B": (0.66, 1.995), "Qwen/Qwen3.6-35B-A3B": (0.54, 1.335),
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16": (0.57, 1.44),
}
DEFAULT = (1.0, 3.0)   # the graders (Qwen3.5-397B-A17B, Kimi-K2.6): an estimate
CHUNK = 40             # requests in flight at once, and spend is checked before each chunk
_lock = threading.RLock()
_clients: dict = {}
_service = None


class BudgetStop(RuntimeError):
    """A call would take this folder's spend past its cap."""


def load_key() -> bool:
    """Put TINKER_API_KEY from this folder's .env into the environment (an existing variable wins). True if a key is set."""
    env = ROOT / ".env"
    for line in (env.read_text().splitlines() if env.exists() else []):
        k, _, v = line.partition("="); k, v = k.strip(), v.split("#")[0].strip()
        if k and not k.startswith("#") and v:
            os.environ.setdefault(k, v)
    return bool(os.environ.get("TINKER_API_KEY"))


def spent(provider: str = "tinker") -> float:
    """Dollars charged so far from this folder, from .spend/spend.json ("tinker" or "modal")."""
    return float(json.loads(SPEND.read_text()).get(provider, 0.0)) if SPEND.exists() else 0.0


def charge(cost_usd: float, provider: str = "tinker") -> None:
    with _lock:
        d = json.loads(SPEND.read_text()) if SPEND.exists() else {}
        d[provider] = float(d.get(provider, 0.0)) + float(cost_usd)
        SPEND.parent.mkdir(exist_ok=True)
        tmp = SPEND.with_suffix(".tmp"); tmp.write_text(json.dumps(d, indent=1)); os.replace(tmp, SPEND)


def check(est: float, provider: str = "tinker", cap: float | None = None) -> None:
    cap = CAP if cap is None else cap
    if spent(provider) + est > cap:
        raise BudgetStop(f"{provider}: ${spent(provider) + est:.2f} would pass the ${cap:.2f} cap (spent ${spent(provider):.2f})")


def cost(model: str, n_in: int, n_out: int) -> float:
    pin, pout = PRICE.get(model, DEFAULT)
    return (n_in * pin + n_out * pout) / 1e6


def _client(model: str):
    global _service
    with _lock:
        if model not in _clients:
            if not load_key():
                raise RuntimeError("TINKER_API_KEY is not set (environment or .env in this folder); it is only needed for missing rows")
            import tinker
            if _service is None:
                _service = tinker.ServiceClient()
            c = _service.create_sampling_client(base_model=model)
            _clients[model] = (c, c.get_tokenizer())
        return _clients[model]


def tokenizer(model: str):
    """The model's tokenizer, from its Tinker sampling client."""
    return _client(model)[1]


def render(model: str, messages: list[dict], **template_kwargs) -> str:
    """Chat messages to the exact prompt text the model sees, from its tokenizer's chat template."""
    return tokenizer(model).apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **template_kwargs)


def sample(model: str, prompts: list[str], max_tokens: int, temperature: float = 0.0, seed: int | None = None,
           topk_logprobs: int = 0, est_out: int | None = None, on_result=None) -> list[dict]:
    """One continuation of each raw prompt string. Each result: text (special tokens kept), final (gpt-oss final channel),
    n_out, finish ("stop" or "length"), n_in, cost, model, and logprobs when topk_logprobs > 0.
    on_result(i, result) is called as each result arrives, so the caller can save it at once."""
    from tinker import types
    c, tok = _client(model)
    sp = types.SamplingParams(max_tokens=max_tokens, temperature=temperature, seed=seed)
    out = [None] * len(prompts)
    for c0 in range(0, len(prompts), CHUNK):
        idx = list(range(c0, min(c0 + CHUNK, len(prompts))))
        toks = {i: tok.encode(prompts[i], add_special_tokens=False) for i in idx}
        check(sum(cost(model, len(toks[i]), est_out or max_tokens // 4) for i in idx))
        futs = {i: c.sample(prompt=types.ModelInput.from_ints(toks[i]), num_samples=1, sampling_params=sp,
                            topk_sample_logprobs=topk_logprobs) for i in idx}
        for i in idx:
            s = futs[i].result().sequences[0]; ids = list(s.tokens); text = tok.decode(ids, skip_special_tokens=False)
            r = dict(text=text, final=P.final_channel(text), n_out=len(ids), finish=str(getattr(s, "stop_reason", "")))
            if topk_logprobs and getattr(s, "logprobs", None) is not None:
                r["logprobs"] = list(s.logprobs)
            r.update(n_in=len(toks[i]), cost=cost(model, len(toks[i]), len(ids)), model=model)
            charge(r["cost"]); out[i] = r
            if on_result:
                on_result(i, r)
    return out


def gut_oss(model: str, prompts: list[str], on_result=None) -> list[dict]:
    """gpt-oss gut read: one token at temperature 0 with its log-probability. Each result: margin (nan if the token is
    neither CORRECT nor INCORRECT), plus the sample fields."""
    def wrap(i, r):
        r["margin"] = P.m1_from(r)
        if on_result:
            on_result(i, r)
    out = sample(model, prompts, max_tokens=1, temperature=0.0, topk_logprobs=1, est_out=1, on_result=wrap)
    return out


def verdict_margin(model: str, prefixes: list[str], pos: str = " CORRECT", neg: str = " INCORRECT", on_result=None) -> list[dict]:
    """The gut verdict after each prefix (which ends with 'VERDICT:'): margin = log P(neg) - log P(pos), each the summed
    log-probability of the continuation's tokens, teacher-forced. Each result: margin, lp_correct, lp_incorrect, n_in, cost."""
    from tinker import types
    c, tok = _client(model)
    out = [None] * len(prefixes)
    for c0 in range(0, len(prefixes), CHUNK):
        idx = list(range(c0, min(c0 + CHUNK, len(prefixes))))
        enc, futs = {}, {}
        for i in idx:
            a = tok.encode(prefixes[i], add_special_tokens=False)
            for name, cont in (("lp_correct", pos), ("lp_incorrect", neg)):
                b = tok.encode(prefixes[i] + cont, add_special_tokens=False); k = len(b) - len(a)
                assert b[:len(a)] == a and k > 0, "the verdict word does not tokenize cleanly after the prompt"
                enc[(i, name)] = (b, k)
        check(sum(cost(model, len(b), 0) for b, _ in enc.values()))
        for (i, name), (b, k) in enc.items():
            futs[(i, name)] = c.compute_logprobs(types.ModelInput.from_ints(b), prompt_logprobs_last_n=k)
        for i in idx:
            r = {}
            for name in ("lp_correct", "lp_incorrect"):
                b, k = enc[(i, name)]; lps = futs[(i, name)].result()
                r[name] = float(sum(x for x in lps[-k:] if x is not None))
            n_in = len(enc[(i, "lp_correct")][0]) + len(enc[(i, "lp_incorrect")][0])
            r.update(margin=r["lp_incorrect"] - r["lp_correct"], n_in=n_in, cost=cost(model, n_in, 0))
            charge(r["cost"]); out[i] = r
            if on_result:
                on_result(i, r)
    return out
