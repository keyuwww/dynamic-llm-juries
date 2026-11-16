#!/usr/bin/env python
"""Cheap belief (Project 2, version b): how likely the JUDGE model finds the candidate's response, in one forward pass, no generation.
For each BFF item: chat = [user: conversation so far, assistant: candidate's final response]; mean and sum log-probability of the response tokens
under the judge model (Wataoka et al.'s perplexity measure). Output: <out>/<model>__bff__candlp.csv (item_id, n_tok, mean_lp, sum_lp, min_lp)."""
import argparse, os, numpy as np, pandas as pd, torch
from judge_data import load_items


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--data"); ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--jb-dir")
    ap.add_argument("--max-len", type=int, default=8192); ap.add_argument("--out", required=True); a = ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    try:
        model = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, dtype=torch.bfloat16).cuda().eval()
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, torch_dtype=torch.bfloat16).cuda().eval()
    items = load_items("bff", a.data, a.verdicts_path, a.rb2_path, a.jb_dir); rows = []
    for it in items:
        try:
            ptxt = tok.apply_chat_template([dict(role="user", content=it["input"])], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            ptxt = tok.apply_chat_template([dict(role="user", content=it["input"])], tokenize=False, add_generation_prompt=True)
        p = tok(ptxt, add_special_tokens=False)["input_ids"]; r = tok(it["response"], add_special_tokens=False)["input_ids"]   # prompt tokens, then exactly the response tokens
        assert len(r) > 0, "empty response"; full = (p + r)[-a.max_len:]; start = max(1, len(full) - len(r))
        with torch.no_grad():
            lp = torch.log_softmax(model(torch.tensor([full]).cuda()).logits[0, :-1].float(), -1)
        tgt = torch.tensor(full[1:]).cuda(); tl = lp.gather(1, tgt[:, None])[:, 0][start - 1:].cpu().numpy()
        rows.append(dict(item_id=it["item_id"], n_tok=len(tl), mean_lp=float(tl.mean()), sum_lp=float(tl.sum()), min_lp=float(tl.min())))
    os.makedirs(a.out, exist_ok=True); pd.DataFrame(rows).to_csv(os.path.join(a.out, f"{a.model.split('/')[-1]}__bff__candlp.csv"), index=False); print(f"saved {len(rows)} rows", flush=True)


if __name__ == "__main__":
    main()
