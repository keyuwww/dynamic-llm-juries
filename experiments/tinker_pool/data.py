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


# ----------------------------------------------------------------------------- RewardBench 2 (Safety)
def load_rb2_safety(rb2_path=None):
    """allenai/reward-bench-2, Safety subset only (450 rows, CoCoNot prompts, human-annotated per the
    paper's Table 2 -- the only RewardBench 2 domain that's genuinely human-labeled rather than
    LLM-judged or purely algorithmic; see docs/findings_zeroshot_juries.md for why that distinction
    matters here). Flattened to one item per (prompt, response): human=1 for each 'chosen' response,
    human=0 for each 'rejected' response -- same shape as the BFF-Bench VERDICTS items.
    Returns: list of dict(id, prompt, response, human)."""
    if rb2_path:
        df = _read_table(rb2_path)
        rows = df.to_dict(orient="records")
    else:
        from datasets import load_dataset
        rows = load_dataset("allenai/reward-bench-2", split="test").to_pandas().to_dict(orient="records")
    out = []
    for r in rows:
        if r["subset"] != "Safety":
            continue
        for i, resp in enumerate(_to_list(r["chosen"])):
            out.append(dict(id=f"rb2safety-{r['id']}-chosen{i}", prompt=str(r["prompt"]), response=str(resp), human=1))
        for i, resp in enumerate(_to_list(r["rejected"])):
            out.append(dict(id=f"rb2safety-{r['id']}-rejected{i}", prompt=str(r["prompt"]), response=str(resp), human=0))
    return out


def bbeh_correct(sample, reference):
    prediction = _extract_answer(sample.strip()).lower()
    prediction = prediction.replace(", ", ",").replace("**", "")
    prediction = prediction.split("\n")[0]
    prediction = prediction[0:-1] if prediction.endswith(".") else prediction
    reference = reference.strip().lower().replace(", ", ",")
    return _fuzzy_match(prediction, reference)
