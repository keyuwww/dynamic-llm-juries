"""Bundle every question, answer and judgment of the beyond-capability study into compact Parquet files (zstd), so
nothing has to be regenerated to re-judge later. Re-run any time; it overwrites archive/*.parquet.

  archive/questions.parquet          benchmark, qid, prompt, gold, extra (subject / level / task)
  archive/answers_<bench>.parquet    benchmark, qid, model, role (candidate | own_solve | strong_solve), sample, text,
                              final (extracted final answer), correct (1/0/None), n_out, clean, thinking
  archive/judgments_<bench>.parquet  benchmark, judge, item (candidate id), qid, condition, gold, sample, text, verdict, n_out

  python3 experiments/beyond_capability/archive.py
  pandas.read_parquet("experiments/beyond_capability/archive/answers_mmlu_redux.parquet")
"""
import gzip
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from bc_common import norm_answer  # noqa: E402
from data import bbeh_correct  # noqa: E402


def jl(p):
    p = Path(p)
    if not p.exists():
        return []
    op = gzip.open if p.suffix == ".gz" else open
    rows = []
    with op(p, "rt") as f:
        for l in f:
            if l.strip():
                try:
                    rows.append(json.loads(l, strict=False))  # tolerate raw control characters in model text
                except json.JSONDecodeError:
                    pass  # a line still being written when the file was copied
    return rows


def letter(text):
    m = re.findall(r"answer is:?\s*\**\s*\(?([A-J])\)?\b", text or "", re.I)
    return m[-1].upper() if m else None


def math_final(text):
    if not text or "answer is" not in text.lower():
        return None
    i = text.lower().rfind("answer is")
    return text[i + len("answer is"):].lstrip(": ").strip().split("\n")[0].strip().rstrip(".").strip("$ ") or None


def main():
    A = HERE / "archive"
    A.mkdir(exist_ok=True)
    Q, ANS, J = [], [], []
    # ---------------- questions
    bbeh = {q["id"]: q for q in jl(HERE / "inputs" / "questions.jsonl")}
    for q in bbeh.values():
        Q.append(dict(benchmark="bbeh", qid=q["id"], prompt=q["input"], gold=q["target"], extra=q["task"]))
    for stem, bench in (("mmlu_full", "mmlu_redux"), ("math_sub", "math")):
        for q in jl(HERE / "inputs" / f"{stem}.jsonl"):
            Q.append(dict(benchmark=bench, qid=q["id"], prompt=q["prompt"], gold=q["gold"],
                          extra=str(q.get("level") or q.get("subject") or "")))
    for q in jl(HERE / "inputs" / "bff_questions.jsonl"):
        Q.append(dict(benchmark="bff", qid=q["id"], prompt=json.dumps(q["messages"]), gold=q["ref"], extra=""))
    gold = {(q["benchmark"], q["qid"]): q["gold"] for q in Q}
    mgrades = {r["cache_key"]: r["verdict"] for r in jl(OUT / "egrades_math_sub.jsonl")}
    bgrades = {r["cache_key"]: r["verdict"] for r in jl(OUT / "bff_grades_glm.jsonl")}

    def add(bench, qid, model, role, i, s, final, correct, thinking):
        ANS.append(dict(benchmark=bench, qid=qid, model=model, role=role, sample=i, text=s.get("text"), final=final,
                        correct=correct, n_out=s.get("n_out"), clean=s.get("clean"), thinking=thinking))

    # BBEH: pool candidates (thinking on, 16K cap) + this study's own solves
    for r in jl(HERE.parent / "tinker_pool" / "bbeh_results" / "answers.jsonl"):
        t = r["answer"] or ""
        add("bbeh", r["item"], r["model"], "candidate", 0, dict(text=t, n_out=r["n_out"], clean=r["n_out"] < 16384),
            norm_answer(t), int(bbeh_correct(t, bbeh[r["item"]]["target"])), "on")
    for p in sorted(OUT.glob("solves_*.jsonl")):
        model = p.stem[len("solves_"):]
        for r in jl(p):
            for i, s in enumerate(r["samples"]):
                add("bbeh", r["qid"], model.split("@")[0], "strong_solve" if "kimi" in model else "own_solve", i, s,
                    norm_answer(s["text"]), int(bbeh_correct(s["text"], bbeh[r["qid"]]["target"])),
                    "on" if ("@think" in model or "kimi" in model) else "off")
    # MMLU-Redux / MATH: Tinker answers (candidates + Qwen-9B own) and the cluster's Llama answers
    roles = {"qwen3.5-9b": "own_solve", "llama3.1-8b": "own_solve"}
    for stem, bench in (("mmlu_full", "mmlu_redux"), ("math_sub", "math")):
        files = list(OUT.glob(f"esolves_{stem}_*.jsonl")) + list((HERE / "out_cluster").glob(f"esolves_{stem}_*.jsonl"))
        for p in sorted(files):
            model = p.stem[len(f"esolves_{stem}_"):]
            for r in jl(p):
                samples = r["samples"] if "samples" in r else [dict(text=r["text"], n_out=r.get("n_out"), clean=r.get("clean"))]
                for i, s in enumerate(samples):
                    if bench == "mmlu_redux":
                        f = letter(s["text"])
                        c = int(f == gold[(bench, r["qid"])]) if f else 0
                    else:
                        f = math_final(s["text"])
                        c = mgrades.get(f"{p.stem}|{r['qid']}|{i}")
                    add(bench, r["qid"], model, roles.get(model, "candidate"), i, s, f, c, "off")
    # BFF: each model's own answers (graded by GLM vs the expert reference)
    for p in sorted(OUT.glob("bff_solves_*.jsonl")):
        model = p.stem[len("bff_solves_"):]
        for r in jl(p):
            for i, s in enumerate(r["samples"]):
                add("bff", r["qid"], model, "strong_solve" if "kimi" in model else "own_solve", i, s, None,
                    bgrades.get(f"{r['cache_key']}|{i}"), "on" if "kimi" in model else "off")
    # ---------------- judgments (BBEH + BFF; every condition, every sample)
    for p in sorted(OUT.glob("*judge_*.jsonl")):
        bench = "bff" if p.name.startswith("bff_") else "bbeh"
        for r in jl(p):
            for i, s in enumerate(r["samples"]):
                J.append(dict(benchmark=bench, judge=r["judge"], item=r.get("cid") or r.get("item"), qid=r["qid"],
                              condition=r["cond"], gold=r["gold"], sample=i, text=s["text"], verdict=s.get("verdict"),
                              n_out=s.get("n_out")))
    jdf = pd.DataFrame(J).drop_duplicates(["benchmark", "judge", "item", "condition", "sample"])
    adf = pd.DataFrame(ANS)
    parts = [("questions", pd.DataFrame(Q))]
    parts += [(f"answers_{b}", g) for b, g in adf.groupby("benchmark")]
    parts += [(f"judgments_{b}", g) for b, g in jdf.groupby("benchmark")]
    for old_file in A.glob("*.parquet"):
        old_file.unlink()
    for name, df in parts:  # one file per kind x benchmark, max zstd level: each well under GitHub's 100 MB limit
        df.to_parquet(A / f"{name}.parquet", compression="zstd", compression_level=19, index=False)
        print(f"{name}: {len(df):,} rows, {(A / f'{name}.parquet').stat().st_size / 1e6:.1f} MB")
    print(adf.groupby(["benchmark", "role"]).size().to_string())


if __name__ == "__main__":
    main()
