"""Reasoning baseline with an exact verdict score (repairs cot_modal.py / cot_vllm.py).

The old score read the top-20 next-token log-probabilities after "<reasoning>VERDICT:" and gave a token missing from
the top 20 the 20th log-probability minus 1; it also took the verdict tokens from vLLM's tokenizer. Here:
  - the verdict tokens are the first tokens of " CORRECT" / " INCORRECT" under the Hugging Face tokenizer, exactly as
    in the hidden-state study (dir_capture.verdict_ids, which asserts they differ);
  - prompts are tokenised with the Hugging Face tokenizer and given to vLLM as token ids;
  - the score is exact: log P(t1) - log P(t2) read as prompt log-probabilities of ids(P2)+[t1] and ids(P2)+[t2]
    (each prompt token's own log-probability is always returned), plus the full-word log-likelihoods of " CORRECT"
    and " INCORRECT" for reference.
Same reasoning procedure: greedy, thinking off, at most --reason tokens, stop at "VERDICT:". The reasoning text is saved.

  python cot_exact.py --model mistralai/Mistral-7B-Instruct-v0.3 --items inputs/mmlu_full_items.jsonl.gz \
      --out outcot/mistral-7b_mmlu/cot_main.jsonl --reason 1536 [--limit 20 --check]
--check: for the scored rows, recompute log P(t1) - log P(t2) with a Transformers forward pass and print the largest
         difference (exact-logit parity; run on a few rows only).
"""
import argparse
import gzip
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--items", required=True, nargs="+")
    ap.add_argument("--out", required=True, nargs="+")
    ap.add_argument("--reason", type=int, nargs="+", default=[1536], help="one per items file, or one for all")
    ap.add_argument("--window", type=int, default=16384)
    ap.add_argument("--tp", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    assert len(a.items) == len(a.out)
    reasons = a.reason * len(a.items) if len(a.reason) == 1 else a.reason
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    hf = AutoTokenizer.from_pretrained(a.model)
    t1 = hf.encode(" CORRECT", add_special_tokens=False)[0]
    t2 = hf.encode(" INCORRECT", add_special_tokens=False)[0]
    assert t1 != t2, (t1, t2)
    w1 = hf.encode(" CORRECT", add_special_tokens=False)
    w2 = hf.encode(" INCORRECT", add_special_tokens=False)
    print("verdict tokens", t1, t2, hf.convert_ids_to_tokens([t1, t2]), "words", w1, w2, flush=True)
    llm = LLM(a.model, max_model_len=a.window, gpu_memory_utilization=0.9, seed=0, enable_prefix_caching=True,
              tensor_parallel_size=a.tp)
    kw = {"enable_thinking": False} if "Qwen3" in a.model else {}
    for fin, fout, reason in zip(a.items, a.out, reasons):
        rows = [r for r in map(json.loads, gzip.open(fin, "rt")) if r["mode"] == "J"][: a.limit or None]
        P = [hf.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True, **kw) for r in rows]
        ids = [hf(p, add_special_tokens=False).input_ids for p in P]
        keep = [i for i, x in enumerate(ids) if len(x) < a.window - reason - 32]
        g = llm.generate([TokensPrompt(prompt_token_ids=ids[i]) for i in keep],
                         SamplingParams(temperature=0, max_tokens=reason, stop=["VERDICT:"]))
        texts = [o.outputs[0] for o in g]
        P2 = [P[i] + o.text.rstrip() + ("\n" if o.text.strip() else "") + "VERDICT:" for i, o in zip(keep, texts)]
        ids2 = [hf(p, add_special_tokens=False).input_ids for p in P2]
        sp = SamplingParams(temperature=0, max_tokens=1, prompt_logprobs=0)
        probe = []
        for x in ids2:
            probe += [x + [t1], x + [t2], x + w1, x + w2]
        res = llm.generate([TokensPrompt(prompt_token_ids=x) for x in probe], sp)

        def lp(o, k):  # summed log-probability of the last k prompt tokens
            pl, toks = o.prompt_logprobs, o.prompt_token_ids
            return float(sum(pl[-j][toks[-j]].logprob for j in range(1, k + 1)))
        out_rows = []
        for n, (i, o) in enumerate(zip(keep, texts)):
            r1, r2, r3, r4 = res[4 * n: 4 * n + 4]
            r = rows[i]
            out_rows.append({k: r[k] for k in ("aid", "qid", "gold", "src")} | dict(
                score=lp(r1, 1) - lp(r2, 1), score_word=lp(r3, len(w1)) - lp(r4, len(w2)), n_reason=len(o.token_ids),
                reached=o.finish_reason == "stop", reasoning=o.text))
        with open(fout, "w") as fh:
            for x in out_rows:
                fh.write(json.dumps(x) + "\n")
        print(f"{fout}: {len(out_rows)}/{len(rows)}, distinct scores {len({round(x['score'], 4) for x in out_rows})}",
              flush=True)
        if a.check:
            del llm
            import gc

            import torch
            from transformers import AutoModelForCausalLM
            gc.collect(), torch.cuda.empty_cache()
            m = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).to("cuda").eval()
            diffs = []
            for x, row in list(zip(ids2, out_rows))[:20]:
                with torch.no_grad():
                    lg = m(input_ids=torch.tensor([x], device="cuda"), logits_to_keep=1).logits[0, -1].float()
                ls = torch.log_softmax(lg, -1)
                diffs.append(abs(float(ls[t1] - ls[t2]) - row["score"]))
                print(f"  check gold {row['gold']} vllm {row['score']:+.3f} hf {float(ls[t1] - ls[t2]):+.3f} "
                      f"reason[:80] {row['reasoning'][:80]!r}", flush=True)
            print(f"CHECK max |vllm - hf| = {max(diffs):.4f} over {len(diffs)} rows", flush=True)
            return


if __name__ == "__main__":
    main()
