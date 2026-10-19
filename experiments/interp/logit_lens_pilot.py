#!/usr/bin/env python3
"""
Logit-lens pilot: does a judge's per-layer "decision" change between the standard BFF prompt and
the detailed expert-rules prompt, and where in the network does it change?

Method follows Wang et al. 2025 (arXiv:2508.02087, "When Truth Is Overridden: Internal Origins of
Sycophancy") -- same paper the project lead co-authored: logit lens at each layer to get a
per-layer Decision Score for the two candidate tokens, then per-layer KL divergence between two
prompt conditions to find the "critical layer" where the model's internal verdict diverges.

Simplification for this first pass ("start simpler," per instructions): a single forced-choice
forward pass (no free-form reasoning first) -- the prompt ends by asking for exactly one word,
CORRECT or INCORRECT, so the verdict is the very next token and there is exactly one position to
read at every layer. This mirrors Jev's own decision-only design, not just a shortcut.

Model: Qwen/Qwen3.5-4B -- our own smallest real judge (not a toy stand-in), small enough (4B
params) to run full logit-lens cheaply on one GPU. Chosen as the first pass specifically because
its behavioral result was the "normal" direction (rules IMPROVED its agreement, noref kappa 0.481
-> rules kappa 0.544) -- establishing what logit-lens looks like for a judge rules HELP, before
spending GPU time on gpt-oss-20b, where rules HURT it.

Usage (inside the Modal image): python experiments/interp/logit_lens_pilot.py --limit 20
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

STANDARD_INSTR = (
    "Evaluate the assistant's FINAL response in this finance/accounting conversation. "
    "Answer yes only if it correctly answers the user's final question: the key facts, "
    "calculations, numbers and conclusions must be correct. Minor wording or formatting "
    "issues do not matter; a wrong number, wrong method or wrong conclusion makes it incorrect."
)

RULES_INSTR = """Evaluate the assistant's FINAL response in this finance/accounting conversation
against the following expert grading rubric. Answer CORRECT only if ALL rules are satisfied.

RULE 1 (Numerical accuracy): Every final numeric answer must be correct to within normal rounding
tolerance (about 1%). A value outside that tolerance is incorrect, even if the method was right.
RULE 2 (Method validity): The formula, accounting treatment, or financial reasoning method used
must be the standard correct one for this question type. A plausible-sounding but non-standard
method is incorrect even if it happens to produce the right number.
RULE 3 (Completeness): If the question has multiple parts, every part must be correctly answered.
A response that correctly answers only some parts is incorrect overall.
RULE 4 (No unsupported assumptions): The response must not introduce assumptions not stated or
implied by the conversation that change the answer, unless it flags them as assumptions.
RULE 5 (Units and sign): Units, currency, and sign (positive/negative, percentage vs. decimal)
must be correct and consistent with the question.
RULE 6 (No partial credit): A response with the right method but a wrong final number due to an
arithmetic slip is still INCORRECT under this rubric -- do not give credit for "close enough"
reasoning if Rule 1 is violated."""

# RULES2: NOT researcher-constructed -- the actual human-annotator labeling guideline BFF-Bench's
# own experts used to create the gold labels (recovered verbatim from a teammate's findings page),
# reused as the LLM judge's grading instructions. Behaviorally (Tinker-pool run), this rubric drops
# gpt-oss-20b's kappa 0.667->0.617 but NOT gpt-oss-120b (0.677->0.680); removing Rule 2 alone fully
# restores gpt-oss-20b (0.666), confirming Rule 2 ("steps must match, not just the final answer")
# specifically, not "rules in general," drives the effect.
RULES2_INSTR = """Evaluate the assistant's FINAL response in this finance/accounting conversation
using the following grading rules -- the same rules used by the human experts who created the
reference labels for this benchmark. Answer CORRECT only if the response is correct under ALL
applicable rules below.

RULE 1: If the final answer disagrees with the reference answer, the response is INCORRECT.
RULE 2: If the final answer agrees with the reference but the reasoning steps disagree, the
response is INCORRECT.
RULE 3: Extra information that is not obviously wrong does not make the response incorrect; it is
still CORRECT.
RULE 4: A final answer that is only slightly off due to rounding is still CORRECT.
RULE 5: If the response is missing information, judge whether that missing information is
crucial to the question; if unsure, treat the response as CORRECT."""

RULES2_NO_RULE2_INSTR = """Evaluate the assistant's FINAL response in this finance/accounting conversation
using the following grading rules -- the same rules used by the human experts who created the
reference labels for this benchmark (with the step-matching rule removed). Answer CORRECT only if
the response is correct under ALL applicable rules below.

RULE 1: If the final answer disagrees with the reference answer, the response is INCORRECT.
RULE 3: Extra information that is not obviously wrong does not make the response incorrect; it is
still CORRECT.
RULE 4: A final answer that is only slightly off due to rounding is still CORRECT.
RULE 5: If the response is missing information, judge whether that missing information is
crucial to the question; if unsure, treat the response as CORRECT."""

RUBRICS = {"rules": RULES_INSTR, "rules2": RULES2_INSTR, "rules2_norule2": RULES2_NO_RULE2_INSTR}

FORCED_CHOICE_SUFFIX = (
    "\n\nAnswer with exactly one word, either CORRECT or INCORRECT. Do not explain. "
    "Do not say anything else.\n\nAnswer:"
)


def render_conv(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv)


def build_prompt(it, instr):
    return (
        f"You are grading an AI assistant's answer in a finance/accounting conversation.\n\n"
        f"{render_conv(it['conv'])}\n\n{instr}{FORCED_CHOICE_SUFFIX}"
    )


def decision_score(logit_correct, logit_incorrect):
    lo, hi = min(logit_correct, logit_incorrect), max(logit_correct, logit_incorrect)
    rng = hi - lo + 1e-9
    return (logit_correct - lo) / rng  # 1.0 = fully favors CORRECT, 0.0 = fully favors INCORRECT
    # NOTE: degenerate with only 2 candidates -- min/max ARE the two logits, so this saturates to
    # ~0/1 for almost any nonzero gap. Kept only for backward-compat; p_correct_norm below (the
    # actual two-way softmax share, already used internally by kl_per_layer) is the real metric.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--rubric", choices=list(RUBRICS), default="rules")
    ap.add_argument("--out", default=None)
    ap.add_argument("--verdicts-path"), ap.add_argument("--bff-path")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from data import load_bff, load_verdicts_items, bff_key_to_uid  # noqa: E402

    items, dropped = load_verdicts_items(a.verdicts_path, a.bff_path, "unanimous")
    to_uid = bff_key_to_uid(load_bff(a.bff_path))
    for it in items:
        it["uid"] = to_uid.get(it["qid"], it["qid"])
        it["gold"] = it["human"]
    items = items[: a.limit]
    print(f"{len(items)} BFF items (of {len(items) + sum(dropped.values())} total, dropped {dropped})", flush=True)

    print(f"Loading {a.model} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()
    n_layers = model.config.num_hidden_layers
    print(f"Loaded. {n_layers} layers, device={model.device}", flush=True)

    # Candidate tokens: the first token of " CORRECT" / " INCORRECT" as they'd appear after "Answer:"
    tok_correct = tok.encode(" CORRECT", add_special_tokens=False)[0]
    tok_incorrect = tok.encode(" INCORRECT", add_special_tokens=False)[0]
    print(f"tok(CORRECT)={tok_correct} ({tok.decode([tok_correct])!r})  "
          f"tok(INCORRECT)={tok_incorrect} ({tok.decode([tok_incorrect])!r})", flush=True)

    def layerwise_scores(prompt):
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model(**inputs, output_hidden_states=True)
        hs = out.hidden_states  # tuple: embeddings + one per layer, each [1, seq, d]
        last = -1
        rows = []
        for l, h in enumerate(hs):
            h_last = h[0, last, :]
            normed = model.model.norm(h_last) if hasattr(model.model, "norm") else h_last
            logits = model.lm_head(normed)
            probs = torch.softmax(logits.float(), dim=-1)
            lc, li = logits[tok_correct].item(), logits[tok_incorrect].item()
            pc, pi = probs[tok_correct].item(), probs[tok_incorrect].item()
            rows.append(dict(layer=l, logit_correct=lc, logit_incorrect=li,
                              p_correct=pc, p_incorrect=pi, decision_score=decision_score(lc, li),
                              p_correct_norm=pc / (pc + pi + 1e-12)))
        final_logits = out.logits[0, last, :]
        final_pred = "CORRECT" if final_logits[tok_correct] > final_logits[tok_incorrect] else "INCORRECT"
        return rows, final_pred

    def kl_per_layer(rows_a, rows_b):
        """KL(a || b) restricted to the CORRECT/INCORRECT 2-way renormalized distribution --
        cheap and directly interpretable as "how much does the verdict-relevant belief differ."""
        out = []
        for ra, rb in zip(rows_a, rows_b):
            pa = [ra["p_correct"], ra["p_incorrect"]]
            pb = [rb["p_correct"], rb["p_incorrect"]]
            sa, sb = sum(pa) + 1e-12, sum(pb) + 1e-12
            pa = [x / sa for x in pa]
            pb = [x / sb for x in pb]
            kl = sum(x * (torch.log(torch.tensor(x + 1e-12)) - torch.log(torch.tensor(y + 1e-12))).item()
                     for x, y in zip(pa, pb) if x > 0)
            out.append(kl)
        return out

    out = Path(a.out or HERE / "logit_lens_results")
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / "items.jsonl"
    done = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            r = json.loads(line)
            done[r["id"]] = r
        print(f"{len(done)} items already cached, resuming", flush=True)

    with open(cache_path, "a") as fh:
        for i, it in enumerate(items):
            if it["id"] in done:
                continue
            p_std = build_prompt(it, STANDARD_INSTR)
            p_rules = build_prompt(it, RUBRICS[a.rubric])
            rows_std, pred_std = layerwise_scores(p_std)
            rows_rules, pred_rules = layerwise_scores(p_rules)
            kls = kl_per_layer(rows_std, rows_rules)
            # Exclude the final layer: its hidden state feeds directly into the lm_head readout, so
            # KL there trivially dwarfs every interior layer (it's ~where the logits ARE, not where
            # the representation diverges). The informative "critical layer" is the interior peak.
            critical_layer = max(range(len(kls) - 1), key=lambda l: kls[l])
            row = dict(id=it["id"], gold=it["gold"], pred_standard=pred_std, pred_rules=pred_rules,
                       critical_layer=critical_layer, kl_at_critical=kls[critical_layer],
                       ds_standard=[r["decision_score"] for r in rows_std],
                       ds_rules=[r["decision_score"] for r in rows_rules],
                       pcn_standard=[r["p_correct_norm"] for r in rows_std],
                       pcn_rules=[r["p_correct_norm"] for r in rows_rules],
                       kl_per_layer=kls)
            done[it["id"]] = row
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if (i + 1) % 5 == 0:
                print(f"  {i+1}/{len(items)}", flush=True)

    results = [done[it["id"]] for it in items if it["id"] in done]
    (out / "pilot_results.json").write_text(json.dumps(dict(model=a.model, rubric=a.rubric, n_layers=n_layers, items=results), indent=2))

    # ---- summary ----
    n = len(results)
    flips_to_correct = sum(1 for r in results if r["pred_standard"] != r["pred_rules"] and r["pred_rules"] == "CORRECT")
    flips_to_incorrect = sum(1 for r in results if r["pred_standard"] != r["pred_rules"] and r["pred_rules"] == "INCORRECT")
    agree_std = sum(1 for r in results if r["pred_standard"] == ("CORRECT" if r["gold"] else "INCORRECT"))
    agree_rules = sum(1 for r in results if r["pred_rules"] == ("CORRECT" if r["gold"] else "INCORRECT"))
    avg_critical_layer = sum(r["critical_layer"] for r in results) / n
    print("\n" + "=" * 60)
    print(f"n={n} items, model={a.model} ({n_layers} layers)")
    print(f"Forced-choice agreement with gold: standard={agree_std}/{n}  rules={agree_rules}/{n}")
    print(f"Verdict flips when adding rules: {flips_to_correct} -> CORRECT, {flips_to_incorrect} -> INCORRECT")
    print(f"Mean critical layer (peak standard-vs-rules KL): {avg_critical_layer:.1f} / {n_layers}")
    print(f"Results written to {out / 'pilot_results.json'}")


if __name__ == "__main__":
    main()
