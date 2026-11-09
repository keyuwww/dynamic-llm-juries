#!/usr/bin/env python
"""Single-pass token-probability signals of a judge's own output (the selective-classification baselines of arXiv 2512.22245, Table 4 / appendix A.1), computed with one forward
pass of the judge over prompt + the exact sampled tokens (n-samples 1 file from vllm_generate.py). Per item, over the generated tokens (reasoning + verdict):
  mean_logprob   mean log-probability of the sampled tokens   (perplexity = exp(-mean_logprob); a confidence signal is mean_logprob)
  mean_entropy   mean entropy of the next-token distribution  (signal = -mean_entropy)
  mean_maxprob   mean of the largest next-token probability   (MaxProb averaged over the output)
  mean_lse       mean log-sum-exp of the logits               (energy score, Liu et al. 2020: higher = more confident)
  verdict_prob   probability the model gave to the first token of its verdict word (MaxProb at the answer) and verdict_entropy: entropy there
Not computed: temperature-scaled MaxProb, Chain-of-Embedding, CoT-kinetics (they need a calibration step or the hidden-state trajectory; see the README)."""
import argparse, os, re, time
import numpy as np, pandas as pd, torch
from judge_data import load_items
from prompts import build_prompt, PAIRWISE


def verdict_pos(tok, ids, bench):
    """index (into ids) of the first token of the verdict word inside the final <answer> ... </answer>, or None."""
    tail0 = max(0, len(ids) - 120); pieces = [tok.decode([t]) for t in ids[tail0:]]; s = "".join(pieces)
    pat = r"<answer>\s*(\[\[[AB]\]\])" if bench in PAIRWISE else r"<answer>\s*(INCORRECT|CORRECT)"
    m = list(re.finditer(pat, s))
    if not m:
        return None
    start = m[-1].start(1); c = 0
    for k, p in enumerate(pieces):
        if c + len(p) > start:
            return tail0 + k
        c += len(p)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--bench", required=True, choices=["bff", "rb2safety", "judgebench", "ppe_correct", "ppe_pref"]); ap.add_argument("--gen", required=True)
    ap.add_argument("--data"); ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--jb-dir"); ap.add_argument("--prompt", default="uncertainty", choices=["uncertainty", "confidence"])
    ap.add_argument("--max-len", type=int, default=8192); ap.add_argument("--block", type=int, default=512); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    gen = pd.read_json(a.gen, lines=True, dtype={"item_id": str}); assert "token_ids" in gen, "need an n-samples 1 file from vllm_generate.py"
    if a.limit:
        gen = gen.iloc[:a.limit]
    items = {it["item_id"]: it for it in load_items(a.bench, a.data, a.verdicts_path, a.rb2_path, a.jb_dir)}; tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)

    def templ(text):
        msgs = [dict(role="user", content=text)]
        try:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    try:
        model = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, dtype=torch.bfloat16)
    except (TypeError, ValueError):
        model = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = model.cuda().eval(); rows, t0 = [], time.time()
    for n, r in enumerate(gen.itertuples()):
        p = tok(templ(build_prompt(a.bench, a.prompt, items[r.item_id])), add_special_tokens=False)["input_ids"][-a.max_len:]; g = list(r.token_ids); G = len(g)
        if G == 0:
            rows.append(dict(item_id=r.item_id, n_gen=0)); continue
        with torch.no_grad():
            lg = model(input_ids=torch.tensor([p + g], device="cuda"), use_cache=False, logits_to_keep=G + 1).logits[0, :G]              # lg[k] predicts generated token k
        gt = torch.tensor(g, device="cuda"); lp, ent, mp, lse = [], [], [], []
        for lo in range(0, G, a.block):
            z = lg[lo:lo + a.block].float(); l = torch.logsumexp(z, -1); logp = z - l[:, None]; pr = logp.exp()
            lp.append(logp.gather(1, gt[lo:lo + a.block, None])[:, 0]); ent.append(-(pr * logp).sum(-1)); mp.append(pr.max(-1).values); lse.append(l)
        lp, ent, mp, lse = [torch.cat(x).cpu().numpy() for x in (lp, ent, mp, lse)]; vp = verdict_pos(tok, g, a.bench)
        rows.append(dict(item_id=r.item_id, n_gen=G, mean_logprob=lp.mean(), mean_entropy=ent.mean(), mean_maxprob=mp.mean(), mean_lse=lse.mean(),
                         verdict_prob=float(np.exp(lp[vp])) if vp is not None else np.nan, verdict_entropy=float(ent[vp]) if vp is not None else np.nan))
        del lg
        if n % 200 == 0:
            print(f"{n}/{len(gen)}  {time.time() - t0:.0f}s", flush=True)
    os.makedirs(a.out, exist_ok=True); tag = os.path.basename(a.gen).replace("_gen.jsonl", ""); df = pd.DataFrame(rows); df.to_csv(os.path.join(a.out, f"{tag}_tokstats.csv"), index=False)
    print(f"saved {tag}_tokstats.csv  verdict position found for {df.verdict_prob.notna().mean():.3f} of items; mean_logprob {df.mean_logprob.mean():.3f}", flush=True)


if __name__ == "__main__":
    main()
