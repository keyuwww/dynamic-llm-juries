"""
Benchmark loaders for the Tinker pool experiments.

- BFF-Bench (kensho/BFFBench): 80 two-turn finance conversations with expert references.
- VERDICTS (kensho/VERDICTS): 1,200 expert-labelled responses from six 2024 models; reused here as the
  human-labelled candidates for Phase 2 (judging). Item construction is shared with Exp 1
  (experiments/jev_bff/run_jev_bff.py) so the numbers are directly comparable.
- BBEH Mini (google-deepmind/bbeh): 460 hard reasoning questions with deterministic answers.

All loaders accept a local file path so you can run offline (--bff-path / --verdicts-path / --bbeh-path).
"""
import json, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data_cache"
BBEH_MINI_URL = "https://raw.githubusercontent.com/google-deepmind/bbeh/main/bbeh/mini/data.json"

sys.path.insert(0, str(HERE.parent / "jev_bff"))


def _to_list(x):
    if x is None:
        return []
    if hasattr(x, "tolist"):
        x = x.tolist()
    return list(x)


def _read_table(path):
    import pandas as pd
    path = str(path)
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    if path.endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_json(path, lines=path.endswith(".jsonl"))


# ----------------------------------------------------------------------------- BFF-Bench
def load_bff(bff_path=None):
    """List of dict(uid, question_id, turns=[q1, q2], refs=[r1, r2])."""
    if bff_path:
        b = _read_table(bff_path)
    else:
        from datasets import load_dataset
        b = load_dataset("kensho/BFFBench", split="train").to_pandas()
    rows = []
    for _, r in b.iterrows():
        rows.append(dict(uid=str(r["uid"]), question_id=str(r.get("question_id")),
                         turns=[str(t) for t in _to_list(r["turns"])],
                         refs=[str(t) for t in _to_list(r.get("references"))]))
    return rows


def bff_key_to_uid(bff_rows):
    """VERDICTS' qid can be either BFFBench's uid or question_id; map both to uid."""
    m = {}
    for r in bff_rows:
        m[r["uid"]] = r["uid"]
        if r["question_id"] not in (None, "None"):
            m[r["question_id"]] = r["uid"]
    return m


def load_verdicts_items(verdicts_path=None, bff_path=None, consensus="unanimous"):
    """Same items as Exp 1: one per (conversation, turn, examinee) with a consensus human label.
    Each: id, qid, cid, turn, examinee, human (1/0), conv (ends with the examinee's answer), ref."""
    from run_jev_bff import load_data, build_items
    v, b = load_data(verdicts_path, bff_path)
    items, dropped = build_items(v, b, consensus)
    return items, dropped


# ----------------------------------------------------------------------------- BBEH Mini
BBEH_SUFFIX = ("\n\nThink step by step, and when you provide the final answer, please use the prefix "
               "\"The answer is:\" without any modification, and provide the answer directly, with no "
               "formatting, no bolding, and no markup.")


def load_bbeh_mini(bbeh_path=None):
    """List of dict(id, task, input, target). Downloads once into data_cache/."""
    if bbeh_path:
        raw = json.loads(Path(bbeh_path).read_text())
    else:
        DATA_DIR.mkdir(exist_ok=True)
        local = DATA_DIR / "bbeh_mini.json"
        if not local.exists():
            print(f"downloading {BBEH_MINI_URL}", file=sys.stderr)
            with urllib.request.urlopen(BBEH_MINI_URL, timeout=60) as f:
                local.write_bytes(f.read())
        raw = json.loads(local.read_text())
    exs = raw["examples"] if isinstance(raw, dict) else raw
    out = []
    for i, e in enumerate(exs):
        # The mini file has only input/target. It holds 20 examples per task (23 x 20 = 460); we ASSUME
        # they are stored in task blocks, so block index = task. Spot-check a few inputs per block.
        task = e.get("task") or e.get("task_name") or f"block{i // 20:02d}"
        out.append(dict(id=f"bbeh-{i:04d}", task=str(task), input=str(e["input"]), target=str(e["target"])))
    return out


# --- BBEH official scoring (google-deepmind/bbeh/bbeh/evaluate.py, Apache-2.0), copied verbatim in logic.
def _strip_latex(response):
    if response.startswith("$") and response.endswith("$"):
        response = response[1:-1]
    if "boxed{" in response and response.endswith("}"):
        response = response[0:-1].split("boxed{")[1]
    if "text{" in response and response.endswith("}"):
        response = response[0:-1].split("text{")[1]
    if "texttt{" in response and response.endswith("}"):
        response = response[0:-1].split("texttt{")[1]
    return response


def _extract_answer(sample):
    answer = sample
    for prefix in ["The answer is:", "The final answer is ", "The final answer is: ", "The answer is "]:
        if prefix in answer:
            answer = answer.split(prefix)[-1].strip()
    if answer.endswith("."):
        answer = answer[:-1]
    return _strip_latex(answer)


def _fuzzy_match(prediction, reference):
    if prediction == reference:
        return True
    if len(prediction) == 3 and prediction[0] == "(" and prediction[-1] == ")":
        return prediction[1] == reference
    if len(reference) == 3 and reference[0] == "(" and reference[-1] == ")":
        return reference[1] == prediction
    try:
        if float(prediction) == float(reference):
            return True
    except ValueError:
        pass
    if prediction.replace("'", "") == reference.replace("'", ""):
        return True
    if f"[{reference}]" == prediction or f"[{prediction}]" == reference:
        return True
    if prediction.endswith("?") and prediction[:-1] == reference:
        return True
    return False


# ----------------------------------------------------------------------------- RewardBench 2 (all domains)
RB2_DOMAINS = ["Safety", "Factuality", "Focus", "Math", "Precise IF", "Ties"]
RB2_HUMAN_LABELED = {"Safety"}  # per the paper's own Table 2 -- the rest are LLM-judged/algorithmic gold,
                                 # not human annotation. See docs/findings_zeroshot_juries.md.


def _load_rb2_raw(rb2_path=None):
    if rb2_path:
        df = _read_table(rb2_path)
        return df.to_dict(orient="records")
    from datasets import load_dataset
    return load_dataset("allenai/reward-bench-2", split="test").to_pandas().to_dict(orient="records")


def load_rb2_domain(domain, rb2_path=None):
    """allenai/reward-bench-2, one domain at a time. Only 'Safety' is human-annotated (per the paper's
    Table 2); the rest (Factuality, Focus, Math, Precise IF, Ties) use LLM-judged or algorithmic gold
    labels -- treat those as capability/algorithmic-agreement checks, not human-preference ones.
    Flattened to one item per (prompt, response): human=1 for each 'chosen' response, human=0 for each
    'rejected' response -- same shape as the BFF-Bench VERDICTS items.
    Returns: list of dict(id, prompt, response, human, domain)."""
    assert domain in RB2_DOMAINS, f"unknown RB2 domain {domain!r}, choose from {RB2_DOMAINS}"
    rows = _load_rb2_raw(rb2_path)
    tag = domain.lower().replace(" ", "")
    out = []
    for r in rows:
        if r["subset"] != domain:
            continue
        for i, resp in enumerate(_to_list(r["chosen"])):
            out.append(dict(id=f"rb2{tag}-{r['id']}-chosen{i}", prompt=str(r["prompt"]), response=str(resp),
                             human=1, domain=domain))
        for i, resp in enumerate(_to_list(r["rejected"])):
            out.append(dict(id=f"rb2{tag}-{r['id']}-rejected{i}", prompt=str(r["prompt"]), response=str(resp),
                             human=0, domain=domain))
    return out


def load_rb2_safety(rb2_path=None):
    """Backwards-compatible alias: RewardBench 2, Safety domain only."""
    return load_rb2_domain("Safety", rb2_path)


def load_rb2_all(rb2_path=None):
    """All six RewardBench 2 domains, flattened together. Each item carries its own 'domain' field so
    results can be broken out per domain; only 'domain' == 'Safety' items are human-annotated."""
    rows = _load_rb2_raw(rb2_path)
    out = []
    for domain in RB2_DOMAINS:
        tag = domain.lower().replace(" ", "")
        for r in rows:
            if r["subset"] != domain:
                continue
            for i, resp in enumerate(_to_list(r["chosen"])):
                out.append(dict(id=f"rb2{tag}-{r['id']}-chosen{i}", prompt=str(r["prompt"]), response=str(resp),
                                 human=1, domain=domain))
            for i, resp in enumerate(_to_list(r["rejected"])):
                out.append(dict(id=f"rb2{tag}-{r['id']}-rejected{i}", prompt=str(r["prompt"]), response=str(resp),
                                 human=0, domain=domain))
    return out


# ----------------------------------------------------------------------------- JudgeBench
def load_judgebench():
    """ScalerLab/JudgeBench (arXiv:2410.12784): pairwise response comparisons with FULLY ALGORITHMIC
    gold labels (MMLU-Pro / LiveBench / LiveCodeBench verifiers) -- not human-labeled, not LLM-judged.
    Treat as a capability/algorithmic-agreement benchmark only, same caveat as BBEH Mini and RB2's
    non-Safety domains. Two splits ('claude' and 'gpt', named for which model generated response_B),
    both loaded and tagged.
    Returns: list of dict(id, question, response_a, response_b, gold, source, split), where gold=1
    means response_A is better ('A>B'), gold=0 means response_B is better ('B>A')."""
    from datasets import load_dataset
    out = []
    for split in ("claude", "gpt"):
        ds = load_dataset("ScalerLab/JudgeBench", split=split)
        for r in ds:
            label = str(r["label"]).strip()
            if label not in ("A>B", "B>A"):
                continue
            out.append(dict(id=f"judgebench-{split}-{r['pair_id']}", question=str(r["question"]),
                             response_a=str(r["response_A"]), response_b=str(r["response_B"]),
                             gold=1 if label == "A>B" else 0, source=str(r.get("source", "")), split=split))
    return out


# ----------------------------------------------------------------------------- BiGGen Bench
def load_biggen_bench(seed=0, limit=None):
    """prometheus-eval/BiGGen-Bench-Results, 'human_eval' split (arXiv:2406.05761, NAACL 2025 best
    paper): general-purpose LM capability benchmark (9 capabilities: instruction following,
    grounding, planning, reasoning, refinement, safety, theory of mind, tool usage, multilingualism;
    77 tasks). Each instance carries an INSTANCE-SPECIFIC, human-curated 1-5 scoring rubric (not a
    researcher-invented one -- the benchmark's own rubric, written by its human annotators), and each
    row pairs one model's response to that instance with a HUMAN-assigned 1-5 score under that same
    rubric. English, non-training rows only (used_for_training == False, language == 'English').

    Binarizes the 1-5 human score to a pass/fail gold label the same way the rest of this project's
    forced-choice CORRECT/INCORRECT setup expects: score >= 4 -> gold=1 (CORRECT), else gold=0
    (INCORRECT) -- the standard "top two points of a 5-point Likert = pass" convention.

    Returns: list of dict(id, capability, task, system_prompt, input, reference_answer, response,
    rubric_criteria, rubric_scores (dict '1'..'5' -> description text), human_score, gold, model_name).
    `id` is the row's uuid (NOT the `id` column, which repeats across different models' responses to
    the same instance)."""
    from datasets import load_dataset
    ds = load_dataset("prometheus-eval/BiGGen-Bench-Results", split="human_eval")
    out = []
    for r in ds:
        if r.get("used_for_training") or str(r.get("language", "English")) != "English":
            continue
        rubric = r["score_rubric"]
        rubric_scores = {str(k): str(v) for k, v in rubric.items() if k != "criteria" and v}
        out.append(dict(id=str(r["uuid"]), capability=str(r["capability"]), task=str(r["task"]),
                         system_prompt=str(r.get("system_prompt", "")), input=str(r["input"]),
                         reference_answer=str(r["reference_answer"]), response=str(r["response"]),
                         rubric_criteria=str(rubric["criteria"]), rubric_scores=rubric_scores,
                         human_score=int(r["human_score"]), gold=1 if int(r["human_score"]) >= 4 else 0,
                         model_name=str(r["model_name"])))
    import random
    random.Random(seed).shuffle(out)
    return out[:limit] if limit else out


# ----------------------------------------------------------------------------- HealthBench meta-eval
HEALTHBENCH_META_URL = ("https://openaipublic.blob.core.windows.net/simple-evals/healthbench/"
                         "2025-05-07-06-14-12_oss_meta_eval.jsonl")


def load_healthbench_meta(seed=0, limit=None, unanimous_only=True):
    """OpenAI HealthBench's own physician meta-evaluation set (released via openai/simple-evals,
    healthbench_meta_eval.py): one row per (conversation, real model completion, ONE physician-
    WRITTEN rubric criterion verbatim from HealthBench's own rubric authoring, list of physician
    binary judgments on whether that completion meets that criterion). Real expert-authored rubric,
    real human (physician) gold labels tied directly to this benchmark -- not an upstream/borrowed
    rubric. 29,511 rows, 77.5% with unanimous physician agreement; unanimous_only=True (default)
    keeps only those, matching this project's existing BFF consensus="unanimous" policy.
    """
    import json
    import urllib.request

    with urllib.request.urlopen(HEALTHBENCH_META_URL) as resp:
        lines = resp.read().decode("utf-8").splitlines()
    out = []
    for i, line in enumerate(lines):
        r = json.loads(line)
        labels = r["binary_labels"]
        if unanimous_only and len(set(labels)) != 1:
            continue
        gold = 1 if sum(labels) / len(labels) > 0.5 else 0
        convo = r["prompt"] + [dict(content=r["completion"], role="assistant")]
        out.append(dict(id=f"{r['completion_id']}-{i}", prompt=r["prompt"],
                         completion=r["completion"], convo=convo, rubric=str(r["rubric"]),
                         category=str(r["category"]), n_physicians=len(labels), gold=gold))
    import random
    random.Random(seed).shuffle(out)
    return out[:limit] if limit else out


def bbeh_correct(sample, reference):
    prediction = _extract_answer(sample.strip()).lower()
    prediction = prediction.replace(", ", ",").replace("**", "")
    prediction = prediction.split("\n")[0]
    prediction = prediction[0:-1] if prediction.endswith(".") else prediction
    reference = reference.strip().lower().replace(", ", ",")
    return _fuzzy_match(prediction, reference)
