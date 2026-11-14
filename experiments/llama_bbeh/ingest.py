"""Grade a Modal Llama run and write it in the Tinker pool's file format.

Reads experiments/llama_bbeh/raw_<model>.jsonl (from llama_modal.py) and writes
  experiments/llama_bbeh/answers.jsonl     same fields as tinker_pool/bbeh_results/answers.jsonl
  experiments/llama_bbeh/judgments.jsonl   same fields as tinker_pool/bbeh_results/judgments.jsonl
so the pool analyses can load pool files + these files together. Rows are keyed by --key
(default llama3.1-8b); rerunning replaces that model's rows.

  python3 experiments/llama_bbeh/ingest.py [--raw raw_llama-3.1-8b-instruct.jsonl] [--key llama3.1-8b]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_verdict  # noqa: E402
from data import bbeh_correct  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="raw_llama-3.1-8b-instruct.jsonl")
    ap.add_argument("--key", default="llama3.1-8b")
    a = ap.parse_args()

    prompts = {(p["kind"], p["id"]): p for p in map(json.loads, open(HERE / "prompts.jsonl"))}
    raw = [json.loads(l) for l in open(HERE / a.raw)]

    answers, judgments = [], []
    for o in raw:
        p = prompts[(o["kind"], o["id"])]
        text = o["text"] or ""
        if o["kind"] == "solve":
            c = int(bbeh_correct(text, p["target"])) if text else 0
            answers.append(dict(cache_key=f"{a.key}|{p['id']}|1", model=a.key, item=p["id"], task=p["task"], turn=1,
                                messages=p["messages"], answer=text, correct=c, correct_all=[c], target=p["target"],
                                n_in=o["n_in"], n_out=o["n_out"], finish=o["finish"], renderer="vllm-chat-template",
                                temperature=0.7, hf_model=o["model"]))
        else:
            v = parse_verdict(text) if text else None
            judgments.append(dict(cache_key=f"{a.key}|{p['id']}|none", judge=a.key, item_id=p["id"],
                                  condition="none", examinee=p["examinee"], gold=p["gold"], votes=[v],
                                  n_parsed=int(v is not None), vote_share=v, raw=[text],
                                  n_in=o["n_in"], n_out=o["n_out"], finish=o["finish"], hf_model=o["model"]))

    for name, new in (("answers.jsonl", answers), ("judgments.jsonl", judgments)):
        path = HERE / name
        keep = []
        if path.exists():  # drop this model's old rows, keep other models'
            keep = [r for r in map(json.loads, open(path))
                    if r.get("model", r.get("judge")) != a.key]
        with open(path, "w") as f:
            for r in keep + new:
                f.write(json.dumps(r) + "\n")

    n = len(answers)
    acc = sum(r["correct"] for r in answers) / n if n else float("nan")
    trunc = sum(r["finish"] == "length" for r in answers) / n if n else float("nan")
    parsed = sum(r["n_parsed"] for r in judgments) / len(judgments) if judgments else float("nan")
    print(f"{a.key}: {n} solves (accuracy {acc:.3f}, truncated {trunc:.2f}); "
          f"{len(judgments)} judgments (parse rate {parsed:.2f})")


if __name__ == "__main__":
    main()
