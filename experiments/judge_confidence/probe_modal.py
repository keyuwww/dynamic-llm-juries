#!/usr/bin/env python3
"""
Hidden-state probes on a Modal GPU (steps 1.5, 1.6, 2.3, 2.4 of docs/judge_confidence_and_error_injection_plan.md).

Same measurement as probe_local.py, at scale and for more models. For each text the open judge sees the BFF grading
prompt with the assistant turn pre-filled with "VERDICT:" (no reasoning), and we keep, for every layer, the
residual stream at:
  end      last token of the answer being graded
  verdict  last prompt token (where the verdict is produced)
  target:* last token of an edited span (planted-error texts only)
plus P(CORRECT) from the next-token logits. Task "question" instead shows only the conversation up to the user's
final question (no answer to grade) and keeps the last prompt token: a "can I solve this" read-out before any
answer is seen.

Tasks
  real      all 960 real BFF answers; no reference, and with the expert reference where one exists
  question  one question-only prompt per real BFF answer (its own conversation history)
  planted   ORIG + passing planted-error variants (variants.jsonl)

Models: qwen3.5-4b, qwen3.5-9b, qwen3.5-0.8b (Jeff's base), jeff (mstrasser/Jeff-Qwen3.5-0.8B v1.2, full fine-tune).

Raw outputs (git-ignored, kept for reuse): results/raw/activations_modal/<model>/<task>/
  index.jsonl   one row per text: key, labels, positions and their tokens, P(CORRECT), top-10 next tokens
  <n>.npy       float16 (n_positions, n_layers + 1, hidden)

  python experiments/judge_confidence/probe_modal.py --model qwen3.5-4b --task real
  python experiments/judge_confidence/probe_modal.py --model jeff --task planted
"""
import argparse, io, json, re, sys
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
MODELS = {
    "qwen3.5-4b": dict(repo="Qwen/Qwen3.5-4B", rev="main", gpu="L4"),
    "qwen3.5-9b": dict(repo="Qwen/Qwen3.5-9B", rev="main", gpu="L40S"),
    "qwen3.5-0.8b": dict(repo="Qwen/Qwen3.5-0.8B", rev="main", gpu="L4"),
    "jeff": dict(repo="mstrasser/Jeff-Qwen3.5-0.8B", rev="v1.2", gpu="L4", template_from="Qwen/Qwen3.5-0.8B"),
}

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("torch==2.14.0", "transformers==5.17.0", "accelerate==1.15.0", "numpy==2.5.3",
                 "huggingface-hub==1.31.0", "safetensors==0.8.0", "pillow==12.3.0", "torchvision==0.29.0")
)
weights = modal.Volume.from_name("judge-confidence-weights", create_if_missing=True)
app = modal.App("judge-confidence-probe", image=image)


@app.cls(gpu="L4", timeout=3600, volumes={"/weights": weights}, max_containers=4, scaledown_window=120)
class Prober:
    model_key: str = modal.parameter()

    @modal.enter()
    def load(self):
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForImageTextToText, AutoModelForCausalLM, AutoTokenizer
        spec = MODELS[self.model_key]
        path = snapshot_download(spec["repo"], revision=spec["rev"], cache_dir="/weights")
        weights.commit()
        self.tok = AutoTokenizer.from_pretrained(path)
        if not getattr(self.tok, "chat_template", None) and spec.get("template_from"):
            base = snapshot_download(spec["template_from"], cache_dir="/weights",
                                     allow_patterns=["*.json", "*.jinja", "*.txt"])
            self.tok.chat_template = AutoTokenizer.from_pretrained(base).chat_template
        try:
            self.model = AutoModelForImageTextToText.from_pretrained(path, dtype=torch.bfloat16)
        except Exception:  # noqa: BLE001 -- text-only checkpoints
            self.model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16)
        self.model = self.model.to("cuda").eval()
        self.cand = {w: self.tok.encode(w, add_special_tokens=False)[0] for w in (" CORRECT", " INCORRECT")}

    @modal.method()
    def run(self, batch):
        import numpy as np
        import torch
        out = []
        for it in batch:
            prompt = self.tok.apply_chat_template(it["messages"], tokenize=False, add_generation_prompt=True,
                                                  enable_thinking=False) + it.get("prefill", "")
            enc = self.tok(prompt, return_offsets_mapping=True, return_tensors="pt", truncation=True,
                           max_length=12000)
            offs = enc.pop("offset_mapping")[0].tolist()
            pos, names = [], []
            ans = it.get("answer")
            a0 = prompt.rfind(ans) if ans else -1
            for nm, (s, e) in (it.get("spans") or {}).items():
                if a0 < 0 or s < 0:
                    continue
                ce = a0 + e - 1
                ti = next((i for i, (x, y) in enumerate(offs) if x <= ce < y), None)
                if ti is not None:
                    pos.append(ti), names.append(f"target:{nm}")
            if a0 >= 0:
                ce = a0 + len(ans) - 1
                ti = next((i for i, (x, y) in enumerate(offs) if x <= ce < y), None)
                if ti is not None:
                    pos.append(ti), names.append("end")
            pos.append(len(offs) - 1), names.append("verdict" if it.get("prefill") else "last")
            with torch.no_grad():
                o = self.model(**{k: v.to("cuda") for k, v in enc.items()}, output_hidden_states=True,
                               logits_to_keep=1, use_cache=False)
            hs = torch.stack([h[0, pos, :] for h in o.hidden_states], dim=1).to(torch.float16).cpu().numpy()
            lp = torch.log_softmax(o.logits[0, -1].float(), -1)
            top = torch.topk(lp, 10)
            buf = io.BytesIO()
            np.save(buf, hs)
            lc, li = lp[self.cand[" CORRECT"]].item(), lp[self.cand[" INCORRECT"]].item()
            out.append(dict(key=it["key"], positions=dict(zip(names, pos)), n_tokens=len(offs),
                            tokens={nm: self.tok.decode(enc["input_ids"][0, p]) for nm, p in zip(names, pos)},
                            logp_correct=lc, logp_incorrect=li,
                            p_correct=float(np.exp(lc) / (np.exp(lc) + np.exp(li))),
                            top10=[(self.tok.decode([i]), float(v)) for v, i in zip(top.values.tolist(),
                                                                                   top.indices.tolist())],
                            npy=buf.getvalue()))
        return out


# ----------------------------------------------------------------------------- local side
def build_items(task):
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parents[1] / "experiments" / "tinker_pool"))
    from jc_common import RAW, load_bff_all, load_bff_correct
    from probe_local import DIRECT
    from run_judges import REF_BLOCK, render_conv

    def judge_msgs(conv, answer, ref):
        c = conv[:-1] + [{"role": "assistant", "content": answer}]
        r = "" if ref is None else REF_BLOCK.format(note=" (written by an expert)", ref=ref)
        return [{"role": "user", "content": DIRECT.format(conversation=render_conv(c), reference=r)}]

    items = []
    if task in ("real", "question"):
        for it in load_bff_all():
            lab = dict(item_id=it["id"], examinee=it["examinee"], qid=it["qid"], turn=it["turn"], labels=it["labels"],
                       gold_unanimous=it["gold_unanimous"], gold_majority=it["gold_majority"])
            ans = it["conv"][-1]["content"]
            if task == "real":
                for cond in ("none", "human"):
                    if cond == "human" and not it["ref"]:
                        continue
                    items.append(dict(key=f"{it['id']}|{cond}", condition=cond, prefill="VERDICT:", answer=ans,
                                      messages=judge_msgs(it["conv"], ans, None if cond == "none" else it["ref"]), **lab))
            else:
                items.append(dict(key=f"{it['id']}|question", condition="question",
                                  messages=[{"role": m["role"], "content": m["content"]} for m in it["conv"][:-1]], **lab))
    else:
        by = {it["id"]: it for it in load_bff_correct()}
        texts = {}
        for v in (json.loads(l) for l in open(RAW / "variants.jsonl")):
            if not v.get("ok"):
                continue
            it = by[v["item_id"]]
            e = (v["proposal"].get("edits") or [{}])[0]
            na = v["new"].find(e.get("new", "")) if e.get("new") else -1
            oa = v["original"].find(e.get("old", "")) if e.get("old") else -1
            texts[f"{it['id']}|{v['vtype']}"] = dict(it=it, vtype=v["vtype"], answer=v["new"],
                                                     spans={v["vtype"]: (na, na + len(e.get("new", "")))})
            o = texts.setdefault(f"{it['id']}|ORIG", dict(it=it, vtype="ORIG", answer=v["original"], spans={}))
            o["spans"][v["vtype"]] = (oa, oa + len(e.get("old", "")))
        for tid, t in texts.items():
            for cond in ("none", "human"):
                items.append(dict(key=f"{tid}|{cond}", condition=cond, prefill="VERDICT:", answer=t["answer"],
                                  spans=t["spans"], vtype=t["vtype"], item_id=t["it"]["id"],
                                  gold=1 if t["vtype"] in ("ORIG", "C1", "C2") else 0,
                                  messages=judge_msgs(t["it"]["conv"], t["answer"], None if cond == "none" else t["it"]["ref"])))
    return items


def run(a):
    sys.path.insert(0, str(HERE))
    from jc_common import RAW, modal_env
    if not modal_env():
        raise SystemExit("Modal credentials not found in .env")
    out_dir = RAW / "activations_modal" / a.model / a.task
    out_dir.mkdir(parents=True, exist_ok=True)
    idx = out_dir / "index.jsonl"
    done = {json.loads(l)["key"] for l in open(idx)} if idx.exists() else set()
    items = [it for it in build_items(a.task) if it["key"] not in done]
    if a.limit:
        items = items[: a.limit]
    print(f"{a.model} / {a.task}: {len(items)} texts to run ({len(done)} already stored)", flush=True)
    if not items:
        return
    meta_keys = [k for k in items[0] if k not in ("messages", "answer", "prefill", "spans")]
    batches = [items[i:i + a.batch] for i in range(0, len(items), a.batch)]
    n = len(done)
    with app.run(), open(idx, "a") as fh:
        p = Prober.with_options(gpu=MODELS[a.model]["gpu"])(model_key=a.model)
        for res, batch in zip(p.run.map(batches, order_outputs=True), batches):
            meta = {it["key"]: {k: it.get(k) for k in meta_keys} for it in batch}
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
    ap.add_argument("--task", choices=["real", "question", "planted"], default="real")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    run(a)


if __name__ == "__main__":
    main()
