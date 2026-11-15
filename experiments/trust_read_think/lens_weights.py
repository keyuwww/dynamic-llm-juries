#!/usr/bin/env python3
"""
Logit-lens weights for Qwen3.5-4B: the final norm's per-dimension gain and the CORRECT - INCORRECT unembedding row.

With these, the saved residual states give the verdict "the model would give if it stopped at layer l" on the Mac:
  lens_l = (h_l / rms(h_l)) * gain . (u_CORRECT - u_INCORRECT)
The gain is measured by passing a vector of ones through the norm module (rms = 1), so it does not depend on how the
norm stores its weight (w or 1 + w). CPU only.

  modal run experiments/trust_read_think/lens_weights.py
"""
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
MODEL = "Qwen/Qwen3.5-4B"
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("torch==2.15.0", "transformers==5.22.2", "numpy==2.5.4")
         .env({"HF_HOME": "/root/.cache/huggingface"}))
hf_cache = modal.Volume.from_name("dlj-hf-cache", create_if_missing=True)
app = modal.App("trust-read-think-lens", image=image)


@app.function(memory=65536, timeout=1800, volumes={"/root/.cache/huggingface": hf_cache})
def fetch(model_name: str = MODEL) -> dict:
    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForImageTextToText.from_pretrained(model_name, dtype=torch.float32).eval()
    norm = model.model.language_model.norm
    pos = tok.encode(" CORRECT", add_special_tokens=False)[0]
    neg = tok.encode(" INCORRECT", add_special_tokens=False)[0]
    with torch.no_grad():
        d = model.lm_head.weight.shape[1]
        gain = norm(torch.ones(1, d))[0]
        u = model.lm_head.weight[pos] - model.lm_head.weight[neg]
    eps = float(getattr(norm, "variance_epsilon", getattr(norm, "eps", 1e-6)))
    return dict(gain=gain.tolist(), u=u.tolist(), eps=eps, pos=pos, neg=neg)


@app.local_entrypoint()
def main(model: str = MODEL):
    import json
    r = fetch.remote(model)
    out = HERE / "results" / "raw" / "step1" / model.split("/")[-1].lower() / "lens_weights.json"
    out.write_text(json.dumps(r))
    print("saved", out, "eps", r["eps"], "tokens", r["pos"], r["neg"])
