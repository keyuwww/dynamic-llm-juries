"""
Shared pieces for the Tinker model-pool experiments.

- POOL: the judge/answer-writer pool (model ids, tier, family, size, Tinker list prices).
- load_env(): reads the repo-root .env into os.environ (never prints values).
- TinkerChat: async chat sampling for one Tinker base model, using tinker-cookbook renderers
  (correct chat template, stop tokens and thinking on/off per model family).
- MockChat: offline stand-in with the same interface, for dry runs without an API key.
- JsonlCache: append-only cache so every run resumes and nothing is paid for twice.
- small metric helpers (kappa, auroc) and cost accounting.

Install once (from the repo root):  uv sync      # pyproject lists tinker + tinker-cookbook
Key:  TINKER_API_KEY in .env (git-ignored) or exported in your shell.
"""
import asyncio, json, os, random, re, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Tinker list prices, USD per 1M tokens (prefill, sample), from
# https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/ (Oct 2026).
POOL = [
    # --- routing pool: comparable judges from different families -------------------
    dict(key="qwen3.5-4b", model="Qwen/Qwen3.5-4B", tier="small", family="qwen",
         params="4B", active="4B", price_in=0.33, price_out=1.005),
    dict(key="gpt-oss-20b", model="openai/gpt-oss-20b", tier="small", family="openai",
         params="21B", active="3.6B", price_in=0.18, price_out=0.45),
    dict(key="nemotron3-nano-30b", model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16", tier="small",
         family="nvidia", params="30B", active="3.5B", price_in=0.195, price_out=0.495),
    dict(key="qwen3.5-9b", model="Qwen/Qwen3.5-9B", tier="mid", family="qwen",
         params="9B", active="9B", price_in=0.66, price_out=1.995),
    dict(key="qwen3.6-35b-a3b", model="Qwen/Qwen3.6-35B-A3B", tier="mid", family="qwen",
         params="35B", active="3B", price_in=0.54, price_out=1.335),
    dict(key="nemotron3-super-120b", model="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16", tier="mid",
         family="nvidia", params="120B", active="12B", price_in=0.57, price_out=1.44),
    # --- escalation tier: strong judges (kept out of the routing pool by default) ----
    dict(key="gpt-oss-120b", model="openai/gpt-oss-120b", tier="strong", family="openai",
         params="117B", active="5B", price_in=0.33, price_out=0.84),
    dict(key="deepseek-v3.1", model="deepseek-ai/DeepSeek-V3.1", tier="strong", family="deepseek",
         params="671B", active="37B", price_in=1.695, price_out=4.215),
]
POOL_BY_KEY = {m["key"]: m for m in POOL}


def select_models(arg):
    """'all' | 'routing' (small+mid) | 'strong' | comma-separated keys."""
    if arg in (None, "", "all"):
        return list(POOL)
    if arg == "routing":
        return [m for m in POOL if m["tier"] in ("small", "mid")]
    if arg == "strong":
        return [m for m in POOL if m["tier"] == "strong"]
    keys = [k.strip() for k in arg.split(",") if k.strip()]
    bad = [k for k in keys if k not in POOL_BY_KEY]
    if bad:
        raise SystemExit(f"unknown model key(s) {bad}; choose from {list(POOL_BY_KEY)}")
    return [POOL_BY_KEY[k] for k in keys]


def call_cost(spec, n_in, n_out):
    return (n_in or 0) / 1e6 * spec["price_in"] + (n_out or 0) / 1e6 * spec["price_out"]


def load_env(path=REPO / ".env"):
    """Minimal .env reader: KEY=VALUE lines; existing env vars win. Never prints values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ----------------------------------------------------------------------------- sampling
def pick_renderer(model, thinking):
    """thinking='off': the family's no-thinking renderer where one exists (GPT-OSS always reasons).
    thinking='on': the family's recommended (thinking) renderer."""
    from tinker_cookbook import model_info
    names = list(model_info.get_recommended_renderer_names(model))
    if thinking == "on":
        return "deepseekv3_thinking" if "deepseekv3_thinking" in names else names[0]
    for n in names:
        if "disable_thinking" in n:
            return n
    for n in names:
        if "thinking" not in n and "reasoning" not in n:
            return n
    return names[0]


class TinkerChat:
    """One Tinker base model behind an async .chat(messages) call."""

    def __init__(self, spec, service, thinking="off"):
        from tinker_cookbook import renderers
        self.spec, self._renderers = spec, renderers
        self.client = service.create_sampling_client(base_model=spec["model"])
        tok = self.client.get_tokenizer()
        self.renderer_name = pick_renderer(spec["model"], thinking)
        self.renderer = renderers.get_renderer(self.renderer_name, tok, model_name=spec["model"])
        self.stop = self.renderer.get_stop_sequences()

    async def chat(self, messages, max_tokens=2048, temperature=0.7, n=1, seed=None):
        from tinker import types
        prompt = self.renderer.build_generation_prompt(messages)
        params = types.SamplingParams(max_tokens=max_tokens, temperature=temperature, stop=self.stop, seed=seed)
        t0 = time.time()
        res = await self.client.sample_async(prompt=prompt, num_samples=n, sampling_params=params)
        n_in = prompt.length() if callable(prompt.length) else prompt.length
        outs = []
        for seq in res.sequences:
            toks = list(seq.tokens)
            msg, term = self.renderer.parse_response(toks)
            outs.append(dict(text=self._renderers.get_text_content(msg), n_out=len(toks),
                             clean=bool(term.is_clean), termination=str(term)))
        return dict(outputs=outs, n_in=n_in, n_out=sum(o["n_out"] for o in outs),
                    latency=time.time() - t0, renderer=self.renderer_name)


class MockChat:
    """Offline stand-in: returns plausible-looking text, verdicts and BBEH-style answers."""

    def __init__(self, spec, seed=0):
        self.spec, self.rng = spec, random.Random(hash(spec["key"]) % 10_000 + seed)
        self.renderer_name = "mock"
        self.skill = {"small": 0.45, "mid": 0.6, "strong": 0.75}[spec["tier"]]

    async def chat(self, messages, max_tokens=2048, temperature=0.7, n=1, seed=None):
        await asyncio.sleep(0.001)
        last = messages[-1]["content"]
        outs = []
        for _ in range(n):
            if "VERDICT:" in last:
                v = "CORRECT" if self.rng.random() < 0.55 else "INCORRECT"
                text = f"Checking the numbers... looks {'fine' if v == 'CORRECT' else 'off'}.\nVERDICT: {v}"
            elif "The answer is:" in last:
                text = "Reasoning...\nThe answer is: " + self.rng.choice(["(A)", "(B)", "1", "2", "yes", "no"])
            else:
                text = f"[mock {self.spec['key']} answer] " + last[:80]
            outs.append(dict(text=text, n_out=len(text) // 4, clean=True, termination="mock"))
        n_in = sum(len(m["content"]) for m in messages) // 4
        return dict(outputs=outs, n_in=n_in, n_out=sum(o["n_out"] for o in outs), latency=0.0, renderer="mock")


def make_chats(models, thinking="off", mock=False):
    if mock:
        return {m["key"]: MockChat(m) for m in models}
    load_env()
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("Set TINKER_API_KEY in .env or your shell (or use --mock).")
    import tinker
    service = tinker.ServiceClient()
    return {m["key"]: TinkerChat(m, service, thinking) for m in models}


# ----------------------------------------------------------------------------- caching / running
class JsonlCache:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.rows[r["cache_key"]] = r
        self._fh = open(self.path, "a")

    def __contains__(self, k):
        return k in self.rows

    def get(self, k):
        return self.rows.get(k)

    def put(self, row):
        self.rows[row["cache_key"]] = row
        self._fh.write(json.dumps(row) + "\n")
        self._fh.flush()


async def run_jobs(jobs, concurrency=32, label="jobs"):
    """jobs: list of zero-arg coroutine functions. Runs them with bounded concurrency,
    reports progress, and keeps going on individual failures (rerun to retry)."""
    sem = asyncio.Semaphore(concurrency)
    done, errors = 0, 0

    async def wrap(job):
        nonlocal done, errors
        async with sem:
            try:
                await job()
            except Exception as e:  # noqa: BLE001 -- keep the batch alive, rerun resumes
                errors += 1
                print(f"[error] {type(e).__name__}: {str(e)[:300]}", flush=True)
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f"  {label}: {done}/{len(jobs)} ({errors} errors)", flush=True)

    await asyncio.gather(*[wrap(j) for j in jobs])
    if errors:
        print(f"{errors} {label} failed; rerun the same command to retry only those.", flush=True)
    return errors


# ----------------------------------------------------------------------------- metrics
def kappa(y, yhat):
    n = len(y)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in zip(y, yhat)) / n
    p1, q1 = sum(y) / n, sum(yhat) / n
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def auroc(y, s):
    pos = [a for a, t in zip(s, y) if t == 1]
    neg = [a for a, t in zip(s, y) if t == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def fmt(x, nd=3):
    return "n/a" if x is None or x != x else f"{x:.{nd}f}"


VERDICT_RE = re.compile(r"VERDICT:\s*\**\s*(CORRECT|INCORRECT)", re.I)


def parse_verdict(text):
    """1 = CORRECT, 0 = INCORRECT, None = unparseable. Uses the LAST verdict line."""
    m = VERDICT_RE.findall(text or "")
    if not m:
        return None
    return 1 if m[-1].upper() == "CORRECT" else 0
