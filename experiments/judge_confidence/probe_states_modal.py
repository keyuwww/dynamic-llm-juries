#!/usr/bin/env python3
"""
Study B of docs/confident_errors_plan.md (B0/B1): hidden states of open judges on the pairwise benchmarks, forced
verdict with no reasoning.

For every pair and both presentation orders the judge sees the confidence-run pairwise prompt with its last line
replaced by 'Answer with exactly one line: "VERDICT: A" or "VERDICT: B".', and the assistant turn is pre-filled
with "VERDICT:". One forward pass gives
  - P(A) vs P(B) from the next-token logits (the model's own forced verdict and confidence), and
  - the residual stream at every layer at three positions:
      q_end    last token of the user's (final) question, before any answer is read
      b_end    last token of answer B (both answers read)
      verdict  last prompt token (where the verdict is produced)

Raw outputs (git-ignored): results/raw/activations_states/<model>/<bench>/
  index.jsonl   one row per prompt: key, pair_id, order, gold, positions, p_a, p_b, n_tokens
  <n>.npy       float16 (n_positions, n_layers + 1, hidden)

  python experiments/judge_confidence/probe_states_modal.py --model qwen3.5-4b --bench alpacafarm --limit 8
  python experiments/judge_confidence/probe_states_modal.py --model qwen3.5-4b --bench all
"""
import argparse, io, json, sys
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
XB = HERE.parent / "cross_benchmark"
MODELS = {
    "qwen3.5-4b": dict(repo="Qwen/Qwen3.5-4B", gpu="L40S", family="qwen"),
    "qwen3.5-9b": dict(repo="Qwen/Qwen3.5-9B", gpu="L40S", family="qwen"),
    "gpt-oss-20b": dict(repo="openai/gpt-oss-20b", gpu="H100", family="gpt-oss"),
    "gpt-oss-120b": dict(repo="openai/gpt-oss-120b", gpu="H100", family="gpt-oss"),
}
BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
DIRECT_TAIL = 'Answer with exactly one line: "VERDICT: A" or "VERDICT: B".'

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("torch==2.14.0", "transformers==5.17.0", "accelerate==1.15.0", "numpy==2.5.3",
                 "huggingface-hub==1.33.0", "safetensors==0.8.0", "pillow==12.3.0", "torchvision==0.29.0",
                 "kernels==0.16.0")
)
weights = modal.Volume.from_name("judge-confidence-weights", create_if_missing=True)
app = modal.App("judge-state-probe", image=image)


@app.cls(gpu="L4", timeout=3600, volumes={"/weights": weights}, max_containers=4, scaledown_window=120)
class Prober:
    model_key: str = modal.parameter()

    @modal.enter()
    def load(self):
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer
        spec = MODELS[self.model_key]
        path = snapshot_download(spec["repo"], cache_dir="/weights")
        weights.commit()
        self.tok = AutoTokenizer.from_pretrained(path)
        if spec["family"] == "qwen":
            self.model = AutoModelForImageTextToText.from_pretrained(path, dtype=torch.bfloat16)
            self.model = self.model.to("cuda").eval()
        else:
            self.model = AutoModelForCausalLM.from_pretrained(path, dtype="auto", device_map="cuda").eval()
        self.cand = {w: self.tok.encode(w, add_special_tokens=False)[-1] for w in (" A", " B")}

    def prompt(self, text):
        msgs = [{"role": "user", "content": text}]
        if MODELS[self.model_key]["family"] == "qwen":
            return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                                enable_thinking=False) + "VERDICT:"
        # gpt-oss (harmony): skip the analysis channel and write the final answer directly
        return (self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                + "<|channel|>final<|message|>VERDICT:")

    @modal.method()
    def run(self, batch):
        import numpy as np
        import torch
        out = []
        for it in batch:
            prompt = self.prompt(it["text"])
            enc = self.tok(prompt, return_offsets_mapping=True, return_tensors="pt", add_special_tokens=False)
            offs = enc.pop("offset_mapping")[0].tolist()

            def tok_at(ch):
                return next((i for i, (x, y) in enumerate(offs) if x <= ch < y), None)
            pos, names = [], []
            q0 = prompt.find(it["q_text"]) if it["q_text"] else -1
            if q0 >= 0 and (ti := tok_at(q0 + len(it["q_text"]) - 1)) is not None:
                pos.append(ti), names.append("q_end")
            b0 = prompt.rfind(it["b_text"]) if it["b_text"] else -1
            if b0 >= 0 and (ti := tok_at(b0 + len(it["b_text"]) - 1)) is not None:
                pos.append(ti), names.append("b_end")
            pos.append(len(offs) - 1), names.append("verdict")
            with torch.no_grad():
                o = self.model(**{k: v.to("cuda") for k, v in enc.items()}, output_hidden_states=True,
                               logits_to_keep=1, use_cache=False)
            hs = torch.stack([h[0, pos, :] for h in o.hidden_states], dim=1).to(torch.float16).cpu().numpy()
            lp = torch.log_softmax(o.logits[0, -1].float(), -1)
            la, lb = lp[self.cand[" A"]].item(), lp[self.cand[" B"]].item()
            buf = io.BytesIO()
            np.save(buf, hs)
            out.append(dict(key=it["key"], positions=dict(zip(names, pos)), n_tokens=len(offs),
                            logp_a=la, logp_b=lb, p_a=float(np.exp(la) / (np.exp(la) + np.exp(lb))),
                            mass_ab=float(np.exp(la) + np.exp(lb)), npy=buf.getvalue()))
        return out


# ----------------------------------------------------------------------------- local side
def build_items(bench):
    sys.path.insert(0, str(XB))
    from run_confidence import OLD_TAIL, load_items
    items, fn = load_items(bench)
    out = []
    for it in items:
        text = fn(it)
        assert OLD_TAIL in text
        text = text.replace(OLD_TAIL, DIRECT_TAIL)
        if bench == "bffpair":
            q, b = it["conv_a"][-2]["content"], it["conv_b"][-1]["content"]
        elif bench == "mtbhuman":
            q, b = it["resp_a"][-2]["content"], it["resp_b"][-1]["content"]
        else:
            q, b = it["question"], it["resp_b"]
        order = it["order"] if isinstance(it["order"], str) else ("ab", "ba")[int(it["order"])]
        out.append(dict(key=it["id"], pair_id=it["pair_id"], order=order, gold=int(it["gold"]), bench=bench,
                        text=text, q_text=q, b_text=b))
    return out


def run(a, bench):
    sys.path.insert(0, str(HERE))
    from jc_common import RAW, modal_env
    if not modal_env():
        raise SystemExit("Modal credentials not found in .env")
    out_dir = RAW / "activations_states" / a.model / bench
    out_dir.mkdir(parents=True, exist_ok=True)
    idx = out_dir / "index.jsonl"
    done = {json.loads(l)["key"] for l in open(idx)} if idx.exists() else set()
    items = [it for it in build_items(bench) if it["key"] not in done]
    if a.limit:
        items = items[: a.limit]
    print(f"{a.model} / {bench}: {len(items)} prompts to run ({len(done)} stored)", flush=True)
    if not items:
        return
    batches = [items[i:i + a.batch] for i in range(0, len(items), a.batch)]
    n = len(done)
    with app.run(), open(idx, "a") as fh:
        p = Prober.with_options(gpu=MODELS[a.model]["gpu"], timeout=3600)(model_key=a.model)
        for res, batch in zip(p.run.map(batches, order_outputs=True), batches):
            meta = {it["key"]: {k: it[k] for k in ("key", "pair_id", "order", "gold", "bench")} for it in batch}
            for r in res:
                fname = f"{n:05d}.npy"
                (out_dir / fname).write_bytes(r.pop("npy"))
                fh.write(json.dumps({**meta[r["key"]], **r, "file": fname, "model": a.model}) + "\n")
                n += 1
            fh.flush()
            print(f"  stored {n}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=list(MODELS), default="qwen3.5-4b")
    ap.add_argument("--bench", default="all")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    for b in (BENCHES if a.bench == "all" else a.bench.split(",")):
        run(a, b)


if __name__ == "__main__":
    main()
