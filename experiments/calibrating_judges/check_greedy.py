#!/usr/bin/env python
"""Teacher-forced check that vLLM's greedy decode is a greedy decode of the same model: run the HF model over prompt + vLLM's sampled tokens and, at every generated
position, compare HF's argmax token with the token vLLM chose. Two greedy decoders of the same weights in bf16 can still diverge where the top two tokens are nearly tied,
so the report separates agreement at all positions from the size of the logit gap at the positions where they disagree."""
import argparse
import numpy as np, pandas as pd, torch
from judge_data import load_items
from prompts import build_prompt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--bench", required=True); ap.add_argument("--gen", required=True)
    ap.add_argument("--data"); ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--jb-dir"); ap.add_argument("--prompt", default="uncertainty")
    ap.add_argument("--max-len", type=int, default=8192); ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    gen = pd.read_json(a.gen, lines=True, dtype={"item_id": str}); items = {it["item_id"]: it for it in load_items(a.bench, a.data, a.verdicts_path, a.rb2_path, a.jb_dir)}
    if a.limit:
        gen = gen.iloc[:a.limit]
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)

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
    model = model.cuda().eval(); n_pos = n_dis = 0; per_seq, gaps, first_dis = [], [], []
    for r in gen.itertuples():
        p = tok(templ(build_prompt(a.bench, a.prompt, items[r.item_id])), add_special_tokens=False)["input_ids"][-a.max_len:]; g = list(r.token_ids); G = len(g)
        ids = torch.tensor([p + g], device="cuda")
        with torch.no_grad():
            lg = model(input_ids=ids, use_cache=False, logits_to_keep=G + 1).logits[0, :G].float()             # logits[k] predicts generated token k
        top2 = lg.topk(2, dim=-1); am = top2.indices[:, 0].cpu().numpy(); gt = np.array(g); dis = am != gt
        n_pos += G; n_dis += int(dis.sum()); per_seq.append(1.0 - dis.mean())
        first_dis.append(int(np.argmax(dis)) if dis.any() else -1)
        if dis.any():                                                                                          # logit gap between HF's top token and the token vLLM chose, at the disagreements
            idx = np.where(dis)[0]; chosen = lg[torch.tensor(idx, device="cuda"), torch.tensor(gt[idx], device="cuda")]; gaps.extend((top2.values[idx, 0] - chosen).cpu().numpy().tolist())
        del lg, top2
    gaps = np.array(gaps); ps = np.array(per_seq)
    print(f"{len(per_seq)} sequences, {n_pos} generated tokens")
    print(f"HF argmax == vLLM token at {1 - n_dis / n_pos:.5f} of positions  ({n_dis} disagreements)")
    print(f"sequences with 100% agreement: {(ps == 1.0).mean():.3f}   median per-sequence agreement {np.median(ps):.5f}   min {ps.min():.5f}")
    if len(gaps):
        print(f"at the {len(gaps)} disagreements, the logit gap between HF's top token and vLLM's token: median {np.median(gaps):.3f}  90th pct {np.percentile(gaps, 90):.3f}  max {gaps.max():.3f}")
        print(f"share of disagreements with gap < 0.5: {(gaps < 0.5).mean():.3f}   < 1.0: {(gaps < 1.0).mean():.3f}   (bf16 near-ties; a different model would give large gaps)")
    fd = [x for x in first_dis if x >= 0]
    if fd:
        print(f"first disagreement position (tokens): median {np.median(fd):.0f}  min {min(fd)}")


if __name__ == "__main__":
    main()
