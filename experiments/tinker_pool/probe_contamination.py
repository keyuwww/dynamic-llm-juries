#!/usr/bin/env python3
"""
Contamination probe: has a judge seen BFF-Bench (questions or expert references) during training?

BFF-Bench has been public on Hugging Face since early 2025, so a model trained later may have read the
expert references. If so, its "no reference" judging is not really reference-free. Two recall tests,
both on the 160 BFF-Bench turns:

  1. reference completion: show the question and the first half of the expert reference; ask the model
     to continue it word for word. Score the longest run of words the continuation shares with the real
     second half, and the share of turns with a 13-word verbatim match (rarely happens by chance in
     prose full of specific numbers).
  2. masked number (TS-Guessing, Deng et al. 2024): replace one number that appears once in the
     question with [MASK]; ask for the exact number. Questions use arbitrary figures, so exact recall of
     many of them means memorization. Numbers that can be derived from the rest of the question make
     this an upper bound, so read it next to a control model.

Usage (from the repo root):
  uv run python experiments/tinker_pool/probe_contamination.py --models gpt-oss-120b,gpt-oss-20b,qwen3.5-4b
  uv run python experiments/tinker_pool/probe_contamination.py --mock
Outputs in experiments/tinker_pool/contamination_results/: probes.jsonl (cache) and summary.md.
"""
import argparse, asyncio, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import JsonlCache, call_cost, make_chats, run_jobs, select_models  # noqa: E402
from data import load_bff  # noqa: E402

COMPLETE = """The text below is the beginning of an expert's answer to a finance question from a public benchmark.
Continue the expert's answer exactly as it was originally written, word for word, from where it stops.
Output only the continuation.

[QUESTION]
{question}

[BEGINNING OF THE EXPERT ANSWER]
{prefix}"""

MASKED = """The finance question below comes from a public benchmark. One number in it has been replaced by [MASK].
What exact number was originally there? If you are not sure, give your best guess.
Reason briefly, then end with exactly one line: "ANSWER: <number>".

{question}"""

NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?")


def words(s):
    return re.findall(r"[a-z0-9]+(?:[.,][0-9]+)*", s.lower())


def longest_common_run(a, b):
    """Longest run of consecutive words shared by word lists a and b."""
    best, prev = 0, [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def norm_num(s):
    s = s.replace("$", "").replace(",", "").replace("%", "").strip().rstrip(".")
    try:
        return float(s)
    except ValueError:
        return None


def is_specific(target):
    """A number hard to guess: 3+ significant digits, not a year. Round figures ($100, 30%), years and
    standard names (FRS 102, Form 1040 still pass, so read the examples) are easy to guess without recall."""
    v = norm_num(target)
    if v is None or (1900 <= v <= 2100 and float(v).is_integer()):
        return False
    return len(re.sub(r"\D", "", target).strip("0")) >= 3


def build_items(bff, seed):
    rng = random.Random(seed)
    items = []
    for r in bff:
        for t, (q, ref) in enumerate(zip(r["turns"], r["refs"]), 1):
            w = ref.split()
            if len(w) >= 40:
                cut = len(w) // 2
                items.append(dict(id=f"{r['uid']}-t{t}", probe="complete", question=q,
                                  prefix=" ".join(w[:cut]), target=" ".join(w[cut:])))
            nums = [m for m in NUM.finditer(q) if norm_num(m.group()) not in (None,)]
            counts = {}
            for m in nums:
                counts[m.group()] = counts.get(m.group(), 0) + 1
            unique = [m for m in nums if counts[m.group()] == 1 and len(re.sub(r"\D", "", m.group())) >= 2]
            if unique:
                m = rng.choice(unique)
                items.append(dict(id=f"{r['uid']}-t{t}", probe="masked",
                                  question=q[:m.start()] + "[MASK]" + q[m.end():], target=m.group()))
    return items


def score(it, text):
    if it["probe"] == "complete":
        run = longest_common_run(words(text), words(it["target"]))
        return dict(lcr=run, verbatim13=int(run >= 13))
    m = re.findall(r"ANSWER:\s*(\S+)", text)
    guess = norm_num(m[-1]) if m else None
    return dict(guess=m[-1] if m else None, exact=int(guess is not None and guess == norm_num(it["target"])))


def summarize(rows, models, out):
    L = ["# BFF-Bench contamination probe", "",
         "Reference completion: longest run of words the model's continuation shares with the real second half "
         "of the expert reference (`verbatim13` = share of turns with a 13+ word exact match). "
         "Masked number: share of turns where the model recovers the exact masked number from the question.", "",
         "Exact recall counts any recovered number, including ones derivable from the rest of the question "
         "(totals, tax owed) or easy to guess (years, round amounts). `Specific` restricts to numbers with 3+ "
         "significant digits that are not years. Check recovered specific numbers by hand for derivability.", "",
         "| Model | Ref turns | Mean longest run | Median | Share ≥13 words | Masked-number turns | Exact recall | "
         "Specific numbers | Specific recall | Cost |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        c = [r for r in rows if r["model"] == m and r["probe"] == "complete"]
        k = [r for r in rows if r["model"] == m and r["probe"] == "masked"]
        if not c and not k:
            continue
        runs = sorted(r["lcr"] for r in c)
        med = runs[len(runs) // 2] if runs else 0
        cost = sum(r["cost"] for r in rows if r["model"] == m)
        s = [r for r in k if is_specific(r["target"])]
        L.append(f"| {m} | {len(c)} | {sum(runs) / max(len(runs), 1):.1f} | {med} | "
                 f"{sum(r['verbatim13'] for r in c) / max(len(c), 1):.3f} | {len(k)} | "
                 f"{sum(r['exact'] for r in k) / max(len(k), 1):.3f} | {len(s)} | "
                 f"{sum(r['exact'] for r in s) / max(len(s), 1):.3f} | ${cost:.3f} |")
    hits = [r for r in rows if r["probe"] == "masked" and r["exact"] and is_specific(r["target"])]
    L += ["", "## Specific numbers recovered (check whether each is derivable from the question)", "",
          "| Model | Turn | Number |", "|---|---|---|"]
    L += [f"| {r['model']} | {r['item']} | {r['target']} |" for r in hits]
    top = sorted((r for r in rows if r["probe"] == "complete"), key=lambda r: -r["lcr"])[:10]
    L += ["", "## Longest verbatim matches", "", "| Model | Turn | Longest run (words) |", "|---|---|---|"]
    L += [f"| {r['model']} | {r['item']} | {r['lcr']} |" for r in top]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gpt-oss-120b,gpt-oss-20b,qwen3.5-4b")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--bff-path")
    a = ap.parse_args()

    out = HERE / ("mock_contamination_results" if a.mock else "contamination_results")
    cache = JsonlCache(out / "probes.jsonl")
    items = build_items(load_bff(a.bff_path), a.seed)
    models = select_models(a.models)
    chats = make_chats(models, "off", a.mock)
    print(f"{sum(i['probe'] == 'complete' for i in items)} completion + "
          f"{sum(i['probe'] == 'masked' for i in items)} masked-number probes x {len(models)} models", flush=True)

    async def probe(chat, it):
        k = f"{chat.spec['key']}|{it['id']}|{it['probe']}"
        if k in cache:
            return
        prompt = (COMPLETE.format(question=it["question"], prefix=it["prefix"]) if it["probe"] == "complete"
                  else MASKED.format(question=it["question"]))
        # temperature 0: recall, not sampling diversity
        r = await chat.chat([{"role": "user", "content": prompt}], max_tokens=a.max_tokens, temperature=0.0)
        text = r["outputs"][0]["text"]
        cache.put(dict(cache_key=k, model=chat.spec["key"], item=it["id"], probe=it["probe"], target=it["target"],
                       text=text, n_in=r["n_in"], n_out=r["n_out"], cost=call_cost(chat.spec, r["n_in"], r["n_out"]),
                       **score(it, text)))

    jobs = [lambda c=c, it=it: probe(c, it) for c in chats.values() for it in items]
    asyncio.run(run_jobs(jobs, a.concurrency, "probes"))
    summarize(list(cache.rows.values()), [m["key"] for m in models], out)


if __name__ == "__main__":
    main()
