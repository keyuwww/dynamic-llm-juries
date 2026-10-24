"""
Shared pieces for the judge-confidence / error-injection experiments (docs/judge_confidence_and_error_injection_plan.md).

- paths: every raw output goes under experiments/judge_confidence/results/raw/ (git-ignored, kept on disk for reuse)
- load_bff_correct(): BFF answers all three experts marked correct, with conversation and expert reference
- sample_with_verdict_probs(): Tinker sampling that also returns, for each sample, the top-k log-probs at the
  verdict token, so P(CORRECT) can be read without extra calls
- number helpers used by the variant checker
"""
import asyncio, math, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RAW = HERE / "results" / "raw"
sys.path.insert(0, str(REPO / "experiments" / "tinker_pool"))
sys.path.insert(0, str(REPO / "experiments" / "jev_bff"))

from common import JsonlCache, call_cost, make_chats, select_models, run_jobs  # noqa: E402,F401


# ----------------------------------------------------------------------------- modal credentials
def modal_env():
    """Export Modal credentials from the repo .env into the names Modal reads (MODAL_TOKEN_ID / MODAL_TOKEN_SECRET).
    Accepts either those names or the modal.toml-style lines `token_id = "..."` / `token_secret = "..."`.
    Never prints the values."""
    import os
    path = REPO / ".env"
    if not path.exists():
        return False
    for line in path.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = (s.strip() for s in line.split("=", 1))
        v = v.strip('"').strip("'")
        k = {"token_id": "MODAL_TOKEN_ID", "token_secret": "MODAL_TOKEN_SECRET"}.get(k, k)
        if k in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"):
            os.environ.setdefault(k, v)
    return bool(os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"))


# ----------------------------------------------------------------------------- items
def load_bff_items(consensus="unanimous"):
    """VERDICTS BFF items (same construction as every other BFF experiment): id, qid, cid, turn, examinee,
    human (1/0), n_annot, conv (ends with the examinee's answer), ref (expert reference for that turn)."""
    from data import load_verdicts_items
    items, _ = load_verdicts_items(consensus=consensus, dataset="bff")
    return items


def load_bff_all():
    """Every VERDICTS BFF answer, whatever the annotators said (incl. split votes), with all labels kept.
    Each: id, qid, cid, turn, examinee, labels (list of raw annotator labels), n_correct, n_incorrect,
    gold_unanimous (1/0/None), gold_majority (1/0/None), conv, ref."""
    from run_jev_bff import load_data, _to_list
    v, b = load_data(None, None, "bff")
    v = v[v["dataset"].astype(str).str.lower() == "bffbench"].copy()
    refs = {}
    for _, r in b.iterrows():
        rl = [str(x) for x in _to_list(r.get("references"))]
        for key in (r.get("uid"), r.get("question_id")):
            if key is not None:
                refs[str(key)] = rl
    items = []
    for (qid, cid, turn, model), g in v.groupby(["qid", "cid", "turn", "model"]):
        labs = [str(x) for x in g["label"]]
        c = sum(l.lower() == "correct" for l in labs)
        i = sum(l.lower() == "incorrect" for l in labs)
        unan = 1 if c == len(labs) else 0 if i == len(labs) else None
        maj = 1 if c > i and c * 2 > len(labs) else 0 if i > c and i * 2 > len(labs) else None
        rl = refs.get(str(qid), [])
        items.append(dict(id=f"{cid}-t{turn}", qid=str(qid), cid=str(cid), turn=int(turn), examinee=str(model),
                          labels=labs, n_correct=c, n_incorrect=i, gold_unanimous=unan, gold_majority=maj,
                          conv=[{"role": m["role"], "content": m["content"]} for m in _to_list(g.iloc[0]["conv"])],
                          ref=rl[int(turn) - 1] if 0 < int(turn) <= len(rl) else None))
    return sorted(items, key=lambda it: it["id"])


def load_bff_correct():
    """Answers all annotators marked correct (unanimous, >= 3 annotators), sorted by id for reproducibility."""
    items = [it for it in load_bff_items("unanimous") if it["human"] == 1 and it["n_annot"] >= 3 and it["ref"]]
    return sorted(items, key=lambda it: it["id"])


# ----------------------------------------------------------------------------- numbers
NUM_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def numbers(text):
    """All numbers in order, as strings exactly as written."""
    return NUM_RE.findall(text or "")


def to_float(s):
    """'$4,520' / '12.5%' / '(1,200)' / '0.94x' -> float; None if there is no number."""
    m = NUM_RE.search(str(s or "").replace("$", " ").replace("(", " "))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def mask_numbers(text):
    return NUM_RE.sub("N", text or "")


# ----------------------------------------------------------------------------- sampling with verdict probabilities
def _classify(tok_text):
    t = tok_text.strip().strip("*").strip().upper()
    if not t:
        return None
    if t.startswith("IN"):
        return "incorrect"
    if t.startswith("C"):
        return "correct"
    if t.startswith("UN"):
        return "unsure"
    return None


def verdict_token_info(tokenizer, tokens, topk):
    """Locate the decision token right after the LAST 'VERDICT:' in a sampled sequence and read the top-k there.
    Returns dict(pos, token, topk=[(text, logprob)], p_correct) or None if there is no verdict line."""
    pieces = [tokenizer.decode([t]) for t in tokens]
    text, starts = "", []
    for p in pieces:
        starts.append(len(text))
        text += p
    k = text.upper().rfind("VERDICT:")
    if k < 0:
        return None
    end = k + len("VERDICT:")
    for i, s in enumerate(starts):
        if s + len(pieces[i]) <= end:
            continue
        if not pieces[i].strip().strip("*").strip():
            continue  # whitespace / markdown between "VERDICT:" and the word
        alts = []
        if topk is not None and i < len(topk) and topk[i]:
            alts = [(tokenizer.decode([tid]), float(lp)) for tid, lp in topk[i]]
        mass = {"correct": 0.0, "incorrect": 0.0, "unsure": 0.0}
        for t, lp in alts:
            c = _classify(t)
            if c:
                mass[c] += math.exp(lp)
        tot = mass["correct"] + mass["incorrect"] + mass["unsure"]
        return dict(pos=i, token=pieces[i], topk=alts,
                    p_correct=mass["correct"] / tot if tot > 0 else None,
                    p_unsure=mass["unsure"] / tot if tot > 0 else None,
                    covered_mass=tot)
    return None


async def sample_with_verdict_probs(chat, messages, n=5, max_tokens=4096, temperature=0.7, topk=5):
    """n samples in one request (prefill paid once). For each: text, clean flag, n_out, mean token log-prob,
    and the verdict-token info (top-k log-probs, P(CORRECT))."""
    from tinker import types
    prompt = chat.renderer.build_generation_prompt(messages)
    params = types.SamplingParams(max_tokens=max_tokens, temperature=temperature, stop=chat.stop)
    t0 = time.time()
    res = await asyncio.wait_for(chat.client.sample_async(prompt=prompt, num_samples=n, sampling_params=params,
                                                          topk_sample_logprobs=topk), 900)
    tok = chat.client.get_tokenizer() if not hasattr(chat, "_tok") else chat._tok
    chat._tok = tok
    n_in = prompt.length() if callable(prompt.length) else prompt.length
    outs = []
    for seq in res.sequences:
        toks = list(seq.tokens)
        msg, term = chat.renderer.parse_response(toks)
        lps = list(seq.logprobs) if seq.logprobs is not None else []
        tk = getattr(seq, "topk_logprobs", None)
        outs.append(dict(text=chat._renderers.get_text_content(msg), clean=bool(term.is_clean), n_out=len(toks),
                         mean_logprob=(sum(lps) / len(lps)) if lps else None,
                         verdict_tok=verdict_token_info(tok, toks, tk)))
    return dict(outputs=outs, n_in=n_in, n_out=sum(o["n_out"] for o in outs), latency=time.time() - t0,
                renderer=chat.renderer_name)
