"""
Shared "System One" backends: TypeSafe Jev (hosted API), and the growing family of open models that
speak the same wire protocol over HTTP (CLM-8B, Laya, jeff): POST {base_url}/v1/systemone with
{"state":..., "questions": {name: {"type": "noul"|"choice"|"score", "instructions":..., "criteria":...}}}
-> {"answers": {name: {...}}, "usage": {"input_tokens":...}, "model": "..."}.

All backends expose the same call shape: client.system_one(state=..., questions={name: Noul(...) | Choice(...)}).
This module hides the small differences so every experiment can run with --backend jev|clm|laya|jeff.

Jev:   needs TYPESAFE_API_KEY.          pip/uv: typesafe-sdk
CLM:   needs a running CLM server (default http://127.0.0.1:8700), which needs an NVIDIA GPU:
         vllm serve Qwen/Qwen3-8B --served-model-name qwen3-8b --runner pooling \
              --enable-prefix-caching --max-model-len 2048 --gpu-memory-utilization 0.35 --port 8090
         clm-serve --port 8700 --emb-url http://127.0.0.1:8090/v1/embeddings
Laya:  needs a running `laya-serve` (default http://127.0.0.1:8000). No pip package needed client-side --
       it's plain HTTP (see HTTPSystemOne below). https://github.com/NandhaKishorM/laya
jeff:  needs a running `jeff-serve` (default http://127.0.0.1:8765). Same deal, plain HTTP.
       https://github.com/firelex/jeff
"""
import os
import sys


class HTTPSystemOne:
    """Minimal client for any server speaking the Jev-style POST /v1/systemone wire protocol
    (CLM, Laya, jeff all do). No vendor SDK needed -- it's plain JSON over HTTP."""

    def __init__(self, base_url, api_key=None, default_model=None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model

    def system_one(self, state, questions, model=None, timeout=60, max_retries=6):
        import time
        import requests
        qd = {k: (q if isinstance(q, dict) else dict(q)) for k, q in questions.items()}
        body = {"state": state, "questions": qd}
        if model or self.default_model:
            body["model"] = model or self.default_model
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        # 529 = server busy (jeff-serve and similar single-worker servers process one request at
        # a time and reject concurrent ones rather than queueing); 503 = still loading. Both are
        # worth a backoff-and-retry rather than failing the call outright.
        for attempt in range(max_retries):
            r = requests.post(f"{self.base_url}/v1/systemone", json=body, headers=headers, timeout=timeout)
            if r.status_code in (529, 503) and attempt < max_retries - 1:
                retry_after = r.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else min(2 ** attempt, 20))
                continue
            r.raise_for_status()
            break
        d = r.json()
        res = type("Response", (), {})()
        res.answers = d.get("answers", {})
        res.usage = type("Usage", (), d.get("usage", {}) or {})()
        res.model = d.get("model", "")
        return res


def _wire_question(type_, instructions, criteria=None):
    q = {"type": type_}
    if instructions is not None:
        q["instructions"] = instructions
    if criteria is not None:
        q["criteria"] = criteria
    return q


class Backend:
    """Thin wrapper: .Noul, .Choice constructors, .ask(state, questions) -> (answers, meta)."""

    HTTP_BACKENDS = {  # name -> (env var for URL, default URL, default model name or None)
        "laya": ("LAYA_URL", "http://127.0.0.1:8000", None),
        "jeff": ("JEFF_URL", "http://127.0.0.1:8765", "jeff-latest"),
    }

    def __init__(self, name="jev", model=None, clm_url=None):
        self.name = name
        if name == "jev":
            if not os.environ.get("TYPESAFE_API_KEY"):
                sys.exit("Set TYPESAFE_API_KEY first (see README), or use --mock.")
            from typesafe_sdk import TypeSafeClient, RetryPolicy, Noul, Choice
            self.client = TypeSafeClient(model=model or "jev-latest",
                                         retry=RetryPolicy(max_retries=4, backoff_initial=0.5, backoff_max=8.0, timeout=60.0))
            self.Noul, self.Choice = Noul, Choice
        elif name == "clm":
            try:
                from clm import CLMClient, Noul, Choice
            except ImportError:
                sys.exit("CLM client not installed: `uv pip install contrastive-lm` "
                         "(or clone https://github.com/Contrastive-LM/CLM and `uv pip install -e .`).")
            url = clm_url or os.environ.get("CLM_URL", "http://127.0.0.1:8700")
            try:
                self.client = CLMClient(base_url=url)
            except TypeError:  # older/newer client signatures
                self.client = CLMClient()
            self.Noul, self.Choice = Noul, Choice
        elif name in self.HTTP_BACKENDS:
            env_var, default_url, default_model = self.HTTP_BACKENDS[name]
            url = clm_url or os.environ.get(env_var, default_url)
            api_key = os.environ.get(f"{name.upper()}_API_KEY")
            self.client = HTTPSystemOne(url, api_key, model or default_model)
            self.Noul = lambda instructions=None, criteria=None: _wire_question("noul", instructions, criteria)
            self.Choice = lambda instructions=None, criteria=None: _wire_question("choice", instructions, criteria)
        else:
            raise ValueError(f"unknown backend {name}")
        # CLM's own model switch (e.g. "clm-raw": ablation, cosine in the raw encoder space,
        # bypassing the trained 20M-param head). Jev's model is fixed at construction instead.
        self.clm_model = model if name == "clm" else None

    def ask(self, state, questions):
        kwargs = dict(model=self.clm_model) if self.clm_model else {}
        res = self.client.system_one(state=state, questions=questions, **kwargs)
        usage = getattr(res, "usage", None)
        meta = dict(in_tok=getattr(usage, "input_tokens", None) if usage is not None else None,
                    backend_model=str(getattr(res, "model", self.name)) or self.name)
        return res, meta


def _answer(res, name):
    for attr in ("answers", "nouls", "choices"):
        d = getattr(res, attr, None)
        if d is not None and name in d:
            return d[name]
    if isinstance(res, dict):
        return res.get("answers", res)[name]
    raise KeyError(name)


def get_noul(res, name):
    a = _answer(res, name)
    return float(a["noul"] if isinstance(a, dict) else a.noul)


def get_choice_probs(res, name):
    a = _answer(res, name)
    probs = a["probabilities"] if isinstance(a, dict) else a.probabilities
    return {str(k): float(v) for k, v in dict(probs).items()}
