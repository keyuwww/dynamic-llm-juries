"""Which saved rows each stage of the experiment still needs, and the calls that would fill them.

    from lib import run_stages
    run_stages.missing()           # {stage name: [rows still needed]}, every list empty as shipped
    run_stages.status()            # one line per stage: expected rows, rows present, missing, extra
    run_stages.run("reads")        # makes only the missing calls of one stage and appends their rows to runs/

As shipped every row exists, so missing() is empty for every stage and run() returns at once. It never imports tinker or
modal, reads a key or opens a client. missing() reads only data/ and runs/, through lib/self_agreement.py for the answers (the
same ids, turns and texts the run used) and the screening decisions.

The stages, their order and their gates are those of the run on Oct 24, 2026:
  1 grader_check        2 candidate graders grade 150 finance answers with the expert reference. The one closer to the
                        experts grades the jurors' own answers (runs/screening_decisions.json, "grader_check").
  2 juror_check         6 jurors, gut and reasoned reads, on the first 100 finance answers. A juror is kept if its gut
                        reads separate right from wrong (AUROC at least 0.60), it parses at least 90% of its reasoned
                        verdicts and at most 5% of its gut margins are missing ("juror_check").
  3 self_solve_turn1    each kept juror answers every turn-1 question itself.
  4 self_solve_turn2    and every turn-2 question, after its own turn-1 answer. With no own turn-1 answer the row says
                        "t1_missing" and no call is made.
  5 grade_own_answers   the chosen grader grades every own answer with the expert reference. MT-Bench answers with a
                        hand-written answer key are also checked against it (CMT_KEYS).
  6 reads               each kept juror reads all 544 answers, gut and reasoned, with no reference.
  7 repeats_and_own_answer_reads   a second gut and reasoned read of the first 40 answers (the noise check), and a gut
                        read with the juror's own answer where the reference goes, on every answer it has an own answer
                        for. Own-answer reads on questions a juror solved ran only while projected spend stayed at or
                        under $28.
  9 safeguard           add-on juror gpt-oss-safeguard-20b on Modal (lib/modal_safeguard.py), gut and reasoned, all 544.
Stage 8 was the analysis, now lib/self_agreement.py. A stage runs only when every earlier stage is complete. Screening decisions
are read from runs/screening_decisions.json and recomputed only when rows of stage 1 or 2 are added.

Rows are keyed as the original run keyed its calls: stage 1 (item_id, grader), 2 and 6 (item_id, juror, mode), 3 and 4
(turn, juror), 5 (juror, turn), 7 (cell, item_id, juror, mode), 9 (item_id, mode). Every new row has the original fields
and is appended atomically: a temporary copy of the file with the row added is renamed over the old one. Calls go through
lib/tinker_client.py (TINKER_API_KEY, $35 cap in .spend/). As in the original, a stage also stops before it starts if the
spend so far plus a projection of its calls would pass $33.
"""
from __future__ import annotations

import collections
import functools
import json
import os
import re
import threading
from pathlib import Path

from . import self_agreement as G
from . import prompts as P

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
DECISIONS = "screening_decisions.json"          # {"grader_check": {...}, "juror_check": {...}} inside runs/

# ------------------------------------------------------------------------------------------------ models
# Short codes, as stored in every row, with the model id and the name used in file names, from lib/self_agreement.py.
MODELS = {k: (v[1], v[0]) for k, v in G.MODELS.items()}          # short code: (model id, slug)
JURORS, GRADERS = list(G.JURORS), list(G.GRADERS)
OSS_MAX, THINK_MAX, GRADE_MAX = 4096, 6144, 8192     # max new tokens: gpt-oss reasoned and self-solve, thinking models, graders
STOP_AT, OWN_SOLVED_GATE = 33.0, 28.0                # $: stop a stage before it starts, and own-answer reads on solved questions
SAFEGUARD = dict(gpu="L40S", deadline_s=2400, chunk=200, cap=4.0,
                 gut=dict(max_tokens=1, temperature=0.0, logprobs=20, n=1, seed=0),
                 reasoned=dict(max_tokens=4096, temperature=0.0, n=1, seed=0))


def model_id(short): return MODELS[short][0]
def slug(short): return MODELS[short][1]


def sample_params(model, kind):
    """Token budget per call, all at temperature 0. est_out is the output length assumed for the spend check."""
    if kind == "grade": return dict(max_tokens=GRADE_MAX, temperature=0.0, est_out=1500)
    if P.family(model) == "oss": return dict(max_tokens=OSS_MAX, temperature=0.0, est_out=900)
    return dict(max_tokens=THINK_MAX, temperature=0.0, est_out=1500)


# ------------------------------------------------------------------------------------------------ the answers
@functools.lru_cache(maxsize=1)
def design():
    """Every id and turn the stages are keyed on, from lib/self_agreement.py, which rebuilds the answers from data/ as the run picked
    them: the 799 finance answers of the grader screening pool, the 544 answers in reading order with their conversations and
    references, the 198 question turns, the 150 + 100 screening answers and the 40 repeat answers."""
    code = {v: k for k, v in G.SETS.items()}                    # finance: BFF, mt_bench: CMT (the codes in the rows)
    X = G.items()
    ITEMS = {r.item_id: dict(item_id=r.item_id, qid=r.question_id, gold=int(r.label_correct), turn=int(r.turn), conv=r.conv, ref=r.ref,
                             ds=code[r.answer_set]) for r in X.itertuples()}
    ORDER = list(X.item_id); TURNS = G.turns()
    assert len(ORDER) == 544 and len(TURNS) == 198, (len(ORDER), len(TURNS))
    return dict(POOL=G.finance_pool(), ITEMS=ITEMS, ORDER=ORDER, TURNS=TURNS,
                T1_KEYS=sorted(k for k, v in TURNS.items() if v["turn"] == "t1"),
                T2_KEYS=sorted(k for k, v in TURNS.items() if v["turn"] == "t2"),
                GATE_IDS=G.grader_check_ids(), GATE_ITEMS=G.juror_check_ids(), DUP_IDS=G.duplicate_ids())


def turn_of(i):
    x = design()["ITEMS"][i]; return f"{x['qid']}|t{x['turn']}"


# ------------------------------------------------------------------------------------------------ the MT-Bench answer keys
# Hand-written from each MT-Bench reference. All regexes must match in the last 1,000 characters of the own answer after
# normalization (lower case, with '$', '*', '\\' and thousands commas removed). None = open-ended turn (4 turns): the grader alone decides.
CMT_KEYS = {
    "01419b73|t1": [r"(=|is|equals)\s*0\b"], "01419b73|t2": [r"x\s*=\s*2\b"],
    "034f7bf4|t1": [r"\bcar\b"], "034f7bf4|t2": None,
    "0605a0ea|t1": [r"\b19(\.0+)?\s*%|0\.19\b"], "0605a0ea|t2": [r"48\.8|48\.9|0\.48[89]|22\s*%?\s*/\s*45"],
    "0d01dbdf|t1": [r"(remainder|is|=)\s*:?\s*0\b"], "0d01dbdf|t2": [r"(remainder|is|=)\s*:?\s*3\b"],
    "0f47d4fd|t1": [r"\b280\b"], "0f47d4fd|t2": [r"\b350\b"],
    "1153dd86|t1": [r"\btrue\b"], "1153dd86|t2": [r"uncertain"],
    "2bf8ddb0|t1": [r"\b19\b"], "2bf8ddb0|t2": [r"\b9\b"],
    "3258feef|t1": [r"35\s*/\s*36|0\.97"], "3258feef|t2": [r"100\s*%|36\s*/\s*36|\b1\b"],
    "3def50bb|t1": [r"x\s*-\s*y\s*=\s*0\b"], "3def50bb|t2": [r"-\s*\(?\s*y\s*/\s*2|-\s*frac\{y\}\{2\}|-\s*0\.5\s*y|-\s*y\s*÷\s*2|-\s*\(?1/2\)?\s*y"],
    "40820c84|t1": None, "40820c84|t2": None,
    "54656983|t1": [r"\bwest\b"], "54656983|t2": [r"\bsouth\b"],
    "64c35abd|t1": [r"\b38\b"], "64c35abd|t2": [r"\b100\b"],
    "785f9777|t1": [r"grandfather|grandparent"], "785f9777|t2": [r"great[- ]?grandfather|great[- ]?grandparent|three generations|3 generations"],
    "9a29c699|t1": [r"(=|is)\s*3\b"], "9a29c699|t2": [r"5\s*(pi|π)|15\.7"],
    "b16eb1dd|t1": [r"\bno brothers?\b|\bzero\b|\b0 brothers?\b|\bnone\b|does ?n[o']t have any|\bno other brothers?\b"],
    "b16eb1dd|t2": [r"\bone brother|\b1 brother|\bone\b|\b1\b"],
    "b5ec8d6f|t1": [r"\(c\)|\bc\)|option c\b|situation c\b|\bc\b"], "b5ec8d6f|t2": None,
    "b867a9e6|t1": [r"washington|pennsylvania"], "b867a9e6|t2": [r"\bno\b|not contain|does ?n[o']t contain|no clues?"],
    "cd3cca8d|t1": [r"\b12000\b"], "cd3cca8d|t2": [r"\b2000\b"],
    "d9a7459b|t1": [r"second", r"third"], "d9a7459b|t2": [r"second[- ]to[- ]last|second[- ]last|next[- ]to[- ]last|penultimate"],
    "df18b293|t1": [r"alice"], "df18b293|t2": [r"purple.{0,60}yellow.{0,60}green.{0,60}blue.{0,60}red"],
}


def _norm(s):
    s = s.lower().replace("$", "").replace("*", "").replace("\\", "")
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)


def exact_check(turn, own):
    """1 = key found, 0 = not found, None = no key (finance turn or open-ended MT-Bench turn)."""
    key = CMT_KEYS.get(turn)
    if key is None: return None
    if not own: return 0
    tail = _norm(own)[-1000:]
    return int(all(re.search(k, tail, re.S) for k in key))


def status_of(ds_key, v, ex, own):
    """solved / unsolved / contested. No own answer (empty, cut at the limit or missing) = unsolved. Finance: the grader
    decides (unparsed = contested). MT-Bench with a key: grader and key must agree, else contested."""
    if not own: return "unsolved"
    if ex is None: return "solved" if v == 1 else "unsolved" if v == 0 else "contested"
    if v == 1 and ex == 1: return "solved"
    if v == 0 and ex == 0: return "unsolved"
    return "contested"


# ------------------------------------------------------------------------------------------------ the runs/ layout
STAGES = {1: "grader_check", 2: "juror_check", 3: "self_solve_turn1", 4: "self_solve_turn2", 5: "grade_own_answers",
          6: "reads", 7: "repeats_and_own_answer_reads", 9: "safeguard"}
KEYS = {1: ("item_id", "grader"), 2: ("item_id", "juror", "mode"), 3: ("turn", "juror"), 4: ("turn", "juror"),
        5: ("juror", "turn"), 6: ("item_id", "juror", "mode"), 7: ("cell", "item_id", "juror", "mode"), 9: ("item_id", "mode")}


def stage_number(stage) -> int:
    if isinstance(stage, int) and stage in STAGES: return stage
    for k, v in STAGES.items():
        if stage == v: return k
    raise ValueError(f"unknown stage {stage!r}. Stages: {STAGES}")


def file_of(k, row) -> str:
    """The run file (relative to runs/) a stage-k row belongs to."""
    if k == 1: return f"checks/grader__{slug(row['grader'])}.jsonl"
    if k == 2: return f"checks/juror__{slug(row['juror'])}__{row['mode']}.jsonl"
    if k in (3, 4): return f"self_solve/{slug(row['juror'])}__turn{k - 2}.jsonl"
    if k == 5: return f"self_solve/grades__{slug(grader())}.jsonl"
    if k == 6: return f"reads/{slug(row['juror'])}__{row['mode']}.jsonl"
    if k == 7:
        if row["cell"] == "dup": return f"duplicates/{slug(row['juror'])}__{row['mode']}.jsonl"
        return f"reads/{slug(row['juror'])}__own_answer_reference.jsonl"
    if k == 9: return f"reads/{slug('sg20')}__{row['mode']}.jsonl"
    raise ValueError(k)


def raw9_file(mode) -> str:
    """The safeguard juror's raw vLLM outputs (the parsed rows above are derived from them)."""
    return f"safeguard_raw/{slug('sg20')}__{mode}.jsonl"


def _lines(rel):
    p = RUNS / rel
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


_dec = {}


def decisions() -> dict:
    """The two screening decisions as saved: {"grader_check": {...}, "juror_check": {...}}."""
    p = RUNS / DECISIONS
    if not p.exists(): return {}
    st = p.stat(); key = (str(p), st.st_mtime_ns, st.st_size)
    if _dec.get("key") != key: _dec.update(key=key, text=p.read_text())
    return json.loads(_dec["text"])


def kept():
    d = decisions().get("juror_check")
    if d is None: raise RuntimeError("runs/screening_decisions.json has no juror_check decision. Complete stage 2 first")
    return [s for s in JURORS if s in d["kept"]]


def grader():
    d = decisions().get("grader_check")
    if d is None: raise RuntimeError("runs/screening_decisions.json has no grader_check decision. Complete stage 1 first")
    return [g for g in GRADERS if g == d["chosen"]][0]


def own_map():
    """{(juror, turn): the juror's own answer} (None if it has none), from the self-solve rows present."""
    out = {}
    for k in (3, 4):
        for s in kept():
            for r in _lines(f"self_solve/{slug(s)}__turn{k - 2}.jsonl"):
                out[(r["juror"], r["turn"])] = r["own"]
    return out


def _status_map():
    try:
        return {(r["juror"], r["turn"]): r["status"] for r in _lines(file_of(5, {}))}
    except RuntimeError:
        return {}


def expected(k) -> list[dict]:
    """Every row stage k must have, as key dicts, in the order the original run made them."""
    D = design()
    if k == 1: return [dict(item_id=i, grader=g) for g in GRADERS for i in D["GATE_IDS"]]
    if k == 2: return [dict(item_id=i, juror=s, mode=md) for s in JURORS for md in ("gut", "reasoned") for i in D["GATE_ITEMS"]]
    if k == 3: return [dict(turn=t, juror=s) for s in kept() for t in D["T1_KEYS"]]
    if k == 4: return [dict(turn=t, juror=s) for s in kept() for t in D["T2_KEYS"]]
    if k == 5: return [dict(juror=s, turn=t) for s, t in sorted((s, t) for s in kept() for t in D["T1_KEYS"] + D["T2_KEYS"])]
    if k == 6: return [dict(item_id=i, juror=s, mode=md) for s in kept() for md in ("gut", "reasoned") for i in D["ORDER"]]
    if k == 7:
        dup = [dict(cell="dup", item_id=i, juror=s, mode=md) for s in kept() for md in ("gut", "reasoned") for i in D["DUP_IDS"]]
        own = own_map()
        ref = [dict(cell="selfref", item_id=i, juror=s, mode="gut") for s in kept() for i in D["ORDER"] if own.get((s, turn_of(i)))]
        return dup + ref
    if k == 9: return [dict(item_id=i, mode=md) for i in D["ORDER"] for md in ("gut", "reasoned")]
    raise ValueError(k)


def _key(k, row): return tuple(row.get(f) for f in KEYS[k])


def _present(k, files):
    have = collections.Counter()
    for rel in files:
        for r in _lines(rel):
            have[_key(k, r)] += 1
    return have


def _check(k):
    """(expected rows with their files, missing rows, extra rows) for stage k."""
    exp = [dict(e, file=file_of(k, e)) for e in expected(k)]
    files = sorted({e["file"] for e in exp})
    if k == 9: files += [raw9_file("gut"), raw9_file("reasoned")]
    have = _present(k, [f for f in files if not f.startswith("safeguard_raw/")])
    want = collections.Counter(_key(k, e) for e in exp)
    miss = [e for e in exp if have[_key(k, e)] == 0]
    if k == 9:   # a parsed safeguard row also needs its raw output
        raw = {json.loads(x)["key"] for m in ("gut", "reasoned") if (RUNS / raw9_file(m)).exists()
               for x in (RUNS / raw9_file(m)).read_text().splitlines() if x.strip()}
        miss += [dict(e, file=raw9_file(e["mode"])) for e in exp if have[_key(k, e)] and f"{e['mode']}|{e['item_id']}" not in raw]
    extra = sum(n for key, n in have.items() if key not in want) + sum(n - 1 for key, n in have.items() if key in want and n > 1)
    return exp, miss, extra


def _blocked(k):
    """The first earlier stage that still misses rows (a stage waits for every earlier stage, as the original ran them)."""
    for j in STAGES:
        if j >= k: break
        if _check(j)[1]: return j
    return None


def missing(stage=None):
    """Rows still needed. missing() gives {stage name: [row keys + file]} for every stage, missing(stage) that stage's list.
    As shipped every list is empty."""
    if stage is not None:
        return _check(stage_number(stage))[1]
    return {STAGES[k]: _check(k)[1] for k in STAGES}


def status() -> list[dict]:
    """One dict per stage: number, name, expected, present, missing, extra (unexpected or repeated keys), waits_for."""
    out = []
    for k in STAGES:
        exp, miss, extra = _check(k)
        out.append(dict(stage=k, name=STAGES[k], expected=len(exp), present=len(exp) - len(miss), missing=len(miss), extra=extra,
                        waits_for=_blocked(k) if miss else None))
    return out


# ------------------------------------------------------------------------------------------------ appending rows
_wlock = threading.Lock()


def append_rows(rel, rows):
    """Append rows to runs/<rel> atomically: write old bytes + new lines to a temporary file, fsync, rename over the file."""
    if not rows: return
    p = RUNS / rel
    with _wlock:
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_bytes() if p.exists() else b""
        if old and not old.endswith(b"\n"):
            raise RuntimeError(f"{rel} does not end with a newline. Fix it by hand before appending")
        tmp = p.with_name(p.name + ".tmp")
        with open(tmp, "wb") as fh:
            fh.write(old + "".join(json.dumps(r) + "\n" for r in rows).encode())
            fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, p)


def tail(s, n=3000): return s if len(s) <= n else s[-n:]


# ------------------------------------------------------------------------------------------------ the screening decisions
def grader_decision():
    """Stage 1 decision recomputed from its rows (lib/self_agreement.py screening()): kappa with the experts per candidate grader,
    the closer one is chosen, and it passes at 0.80."""
    return G.screening()["grader_check"]


def juror_decision():
    """Stage 2 decision recomputed from its rows: a juror is kept with gut AUROC >= 0.60, parse rate >= 0.90, nan rate <= 0.05."""
    return G.screening()["juror_check"]


def _save_decision(name, d):
    cur = decisions()
    if cur.get(name) == d: return False
    cur[name] = d
    p = RUNS / DECISIONS; tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(cur, indent=1) + "\n"); os.replace(tmp, p)
    print(f"runs/{DECISIONS}: {name} recomputed from the new rows and CHANGED: {d}")
    return True


# ------------------------------------------------------------------------------------------------ making the calls
def _client():
    """lib/tinker_client.py, imported only when a call is needed."""
    from . import tinker_client
    return tinker_client


def _read_row(meta, short, kind, o):
    """A juror read row with the original fields: gut adds margin, reasoned adds v, finish, n_out, n_in, final, text."""
    row = dict(meta, juror=short, mode=kind)
    if kind == "gut":
        m = o["margin"]; row["margin"] = float(m) if m is not None else float("nan")
    else:
        if P.family(model_id(short)) == "oss": v, fin = P.parse_verdict(o), o["final"]
        else: fin, v = P.parse_think(o["text"])
        row.update(v=v, finish=o["finish"], n_out=o["n_out"], n_in=o["n_in"], final=tail(fin, 1500), text=tail(o["text"]))
    return row


def _call(TC, short, kind, prompts, on_result):
    """One batch of calls for one model: kind gut, reasoned, grade or solve."""
    m = model_id(short)
    if kind == "gut":
        if P.family(m) == "oss": return TC.gut_oss(m, prompts, on_result=on_result)
        return TC.verdict_margin(m, prompts, on_result=on_result)
    kw = sample_params(m, "grade" if kind == "grade" else "read")
    return TC.sample(m, prompts, kw["max_tokens"], kw["temperature"], est_out=kw["est_out"], on_result=on_result)


def _projection(TC, jobs):
    """Rough $ for a list of (short, kind, prompts): prompt tokens at list price plus the assumed output length."""
    total = 0.0
    for short, kind, prompts in jobs:
        m = model_id(short); tok = TC.tokenizer(m); oss = P.family(m) == "oss"
        n_in = sum(len(tok.encode(p, add_special_tokens=False)) for p in prompts)
        if kind == "gut":
            total += TC.cost(m, n_in * (1 if oss else 2), len(prompts) if oss else 0)
        else:
            total += TC.cost(m, n_in, len(prompts) * sample_params(m, "grade" if kind == "grade" else "read")["est_out"])
    return total


def _run_jobs(TC, k, jobs, gate=STOP_AT):
    """jobs: list of (short, kind, prompts, metas, build(meta, output) returning the row). Appends each row to its file as it arrives."""
    if not jobs: return collections.Counter()
    proj = _projection(TC, [(s, kd, ps) for s, kd, ps, _, _ in jobs])
    if TC.spent() + proj > gate:
        raise TC.BudgetStop(f"stage {k} {STAGES[k]}: spent ${TC.spent():.2f} + projected ${proj:.2f} would pass ${gate:.0f}")
    added = collections.Counter()
    for short, kind, prompts, metas, build in jobs:
        def save(n, o, metas=metas, build=build):
            row = build(metas[n], o); rel = file_of(k, row); append_rows(rel, [row]); added[rel] += 1
        _call(TC, short, kind, prompts, save)
    return added


def _pre_rows(k, todo):
    """Rows the original wrote with no call: turn 2 without an own turn-1 answer (stage 4), and the grade row of a unit
    with no own answer (stage 5). Returns (rows, the todo entries that still need a call)."""
    if k == 4:
        o1 = {(r["juror"], r["turn"]): r["own"] for s in kept() for r in _lines(f"self_solve/{slug(s)}__turn1.jsonl")}
        pre = [e for e in todo if not o1.get((e["juror"], e["turn"].replace("|t2", "|t1")))]
        rows = [dict(turn=e["turn"], juror=e["juror"], own=None, finish="t1_missing", n_out=0, text="") for e in pre]
    elif k == 5:
        own = own_map(); pre = [e for e in todo if not own[(e["juror"], e["turn"])]]
        rows = [_grade_row(e["juror"], e["turn"], own, None) for e in pre]
    else:
        return [], todo
    ids = {id(e) for e in pre}
    return rows, [e for e in todo if id(e) not in ids]


def _grade_row(j, t, own, o):
    """Stage 5 row: the grader's verdict on a juror's own answer, the MT-Bench key check and the status."""
    T = design()["TURNS"][t]; ex = exact_check(t, own[(j, t)]) if T["ds"] == "CMT" else None
    fin, v = P.parse_think(o["text"]) if o is not None else ("", None)
    return dict(juror=j, turn=t, ds=T["ds"], has_own=bool(own[(j, t)]), v=v, exact=ex, status=status_of(T["ds"], v, ex, own[(j, t)]),
                finish=o["finish"] if o is not None else None, final=tail(fin, 1200) if o is not None else "",
                text=tail(o["text"], 1500) if o is not None else "")


def _stage_jobs(TC, k, todo):
    """The calls for the todo rows of stage k: list of (short, kind, prompts, metas, build)."""
    D = design(); I = D["ITEMS"]; jobs = []
    if k == 1:
        for g in GRADERS:
            ids = [e["item_id"] for e in todo if e["grader"] == g]
            if not ids: continue
            tok = TC.tokenizer(model_id(g))
            def b1(meta, o, g=g):
                fin, v = P.parse_think(o["text"])
                return dict(meta, grader=g, gold=D["POOL"][meta["item_id"]]["gold"], v=v, finish=o["finish"], n_out=o["n_out"],
                            final=tail(fin, 1500), text=tail(o["text"], 2000))
            jobs.append((g, "grade", [P.grade_prompt_item(model_id(g), I.get(i) or D["POOL"][i], tok) for i in ids],
                         [dict(item_id=i) for i in ids], b1))
    elif k in (2, 6, 7):
        own = own_map() if k == 7 else {}
        cells = (("dup", "gut"), ("dup", "reasoned"), ("selfref", "gut")) if k == 7 else ((None, "gut"), (None, "reasoned"))
        for s in (JURORS if k == 2 else kept()):
            for cell, md in cells:
                ids = [e["item_id"] for e in todo if e["juror"] == s and e["mode"] == md and e.get("cell") == cell]
                if not ids: continue
                tok = None if P.family(model_id(s)) == "oss" else TC.tokenizer(model_id(s))
                if cell == "selfref":
                    ps = [P.selfref_prompt(model_id(s), I[i], own[(s, turn_of(i))], tokenizer=tok) for i in ids]
                else:
                    ps = [P.judge_prompt(model_id(s), I[i], md, tokenizer=tok) for i in ids]
                def b2(meta, o, s=s, md=md, cell=cell):
                    row = _read_row(meta, s, md, o)
                    if cell: row["cell"] = cell
                    return row
                jobs.append((s, md, ps, [dict(item_id=i) for i in ids], b2))
    elif k in (3, 4):
        o1 = {(r["juror"], r["turn"]): r["own"] for s in kept() for r in _lines(f"self_solve/{slug(s)}__turn1.jsonl")}
        for s in kept():
            ts = [e["turn"] for e in todo if e["juror"] == s]
            if not ts: continue
            tok = TC.tokenizer(model_id(s))
            own1 = lambda t: o1[(s, t.replace("|t2", "|t1"))] if k == 4 else None  # noqa: E731
            ps = [P.solve_prompt(model_id(s), P.solve_messages(D["TURNS"][t]["users"], own1(t)), tok) for t in ts]
            def b3(meta, o, s=s):
                return dict(meta, juror=s, own=P.own_from(model_id(s), o), finish=o["finish"], n_out=o["n_out"], text=tail(o["text"], 4000))
            jobs.append((s, "solve", ps, [dict(turn=t) for t in ts], b3))
    elif k == 5:
        g = grader(); own = own_map(); units = [(e["juror"], e["turn"]) for e in todo]
        if units:
            tok = TC.tokenizer(model_id(g))
            def conv(j, t):
                u = D["TURNS"][t]["users"]
                return P.grade_conv(u, own[(j, t)]) if t.endswith("|t1") else P.grade_conv(u, own[(j, t.replace("|t2", "|t1"))], own[(j, t)])
            ps = [P.grade_prompt(model_id(g), I[D["TURNS"][t]["any_item"]], conv(j, t), tok) for j, t in units]
            jobs.append((g, "grade", ps, [dict(juror=j, turn=t) for j, t in units], lambda meta, o: _grade_row(meta["juror"], meta["turn"], own, o)))
    return jobs


def run(stage, safeguard_runner=None) -> dict:
    """Make only the missing calls of one stage and append their rows. Returns {file: rows added}.
    Nothing missing: returns {} at once, with no import of tinker or modal and no key needed."""
    k = stage_number(stage)
    todo = missing(k)
    if not todo:
        return {}
    w = _blocked(k)
    if w is not None:
        raise RuntimeError(f"stage {k} {STAGES[k]} waits for stage {w} {STAGES[w]}, which still misses {len(missing(w))} rows. Run it first")
    if k == 9:
        return _run_safeguard(todo, safeguard_runner)
    added = collections.Counter()
    pre, todo = _pre_rows(k, todo)
    for row in pre:
        rel = file_of(k, row); append_rows(rel, [row]); added[rel] += 1
    if todo:
        TC = _client()
        if not TC.load_key():
            raise RuntimeError(f"stage {k} {STAGES[k]}: {len(todo)} rows need calls and TINKER_API_KEY is not set (environment or .env)")
        if TC.spent() > STOP_AT:
            raise TC.BudgetStop(f"spent ${TC.spent():.2f} > ${STOP_AT:.0f} before stage {k}")
        if k == 7:   # priority reads first (repeats, own-answer reads on unsolved or contested questions, all of gpt-oss-120b's)
            st = _status_map()
            solved = lambda e: e["cell"] == "selfref" and e["juror"] != "oss120" and st.get((e["juror"], turn_of(e["item_id"]))) == "solved"  # noqa: E731
            added.update(_run_jobs(TC, k, _stage_jobs(TC, k, [e for e in todo if not solved(e)])))
            try:      # then own-answer reads on solved questions, only while the projection stays under the original's $28
                added.update(_run_jobs(TC, k, _stage_jobs(TC, k, [e for e in todo if solved(e)]), gate=OWN_SOLVED_GATE))
            except TC.BudgetStop as e:
                print(f"own-answer reads on solved questions skipped, as in the original rule: {e}")
        else:
            added.update(_run_jobs(TC, k, _stage_jobs(TC, k, todo)))
    if k in (1, 2) and not missing(k):
        _save_decision("grader_check" if k == 1 else "juror_check", grader_decision() if k == 1 else juror_decision())
    return dict(added)


def run_missing(safeguard=False) -> dict:
    """run() every stage in order. The safeguard add-on runs only with safeguard=True, as the original ran it only on request."""
    out = {}
    for k in STAGES:
        if k == 9 and not safeguard: continue
        out.update(run(k))
    return out


def _run_safeguard(todo, runner=None):
    """Stage 9 on Modal: raw outputs appended to runs/safeguard_raw/, then the parsed rows to runs/reads/."""
    D = design()
    raw_have = {r["key"]: r for m in ("gut", "reasoned") for r in _lines(raw9_file(m))}
    jobs = [dict(key=f"{e['mode']}|{e['item_id']}", prompt=P.safeguard_prompt(D["ITEMS"][e["item_id"]], e["mode"]), sp=SAFEGUARD[e["mode"]])
            for e in todo if f"{e['mode']}|{e['item_id']}" not in raw_have]
    added = collections.Counter()
    if jobs:
        if runner is None:
            from . import modal_safeguard
            runner = modal_safeguard.run
        def on_chunk(res):
            for r in res:
                row = dict(key=r["key"], n_prompt=r["n_prompt"], **r["samples"][0]); rel = raw9_file(row["key"].split("|", 1)[0])
                append_rows(rel, [row]); raw_have[row["key"]] = row; added[rel] += 1
        runner(model_id("sg20"), jobs, on_chunk=on_chunk, gpu=SAFEGUARD["gpu"], deadline_s=SAFEGUARD["deadline_s"],
               chunk=SAFEGUARD["chunk"], cap=SAFEGUARD["cap"])
    have = _present(9, [file_of(9, dict(mode=m)) for m in ("gut", "reasoned")])
    for e in todo:
        r = raw_have.get(f"{e['mode']}|{e['item_id']}")
        if r is None or have[_key(9, e)]: continue
        if e["mode"] == "gut":
            mg, cens = P.margin_from_vllm(r); row = dict(item_id=e["item_id"], juror="sg20", mode="gut", margin=mg, censored=cens)
        else:
            _, fin, v = P.parse_raw(r["text"])
            row = dict(item_id=e["item_id"], juror="sg20", mode="reasoned", v=v, finish=r["finish"], n_out=r["n_out"], final=fin[-1500:])
        rel = file_of(9, row); append_rows(rel, [row]); added[rel] += 1
    return dict(added)
