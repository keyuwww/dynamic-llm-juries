"""Self-Agreement: every number in this folder, computed from the saved model outputs in runs/. Never calls a model.

Inputs, all in this folder:
  data/verdicts.parquet    Kensho's VERDICTS: three expert votes per answer, for the finance and the MT-Bench answers
  data/bffbench.parquet    Kensho's BFF-Bench: the finance questions, one reference per question turn
  data/cmtbench.parquet    Kensho's CMTBench: the 20 MT-Bench math and reasoning questions, with corrected references
  runs/                    every model output of the run on Oct 24, 2026 (README.md lists the files)

items() rebuilds the 544 answers, runs() loads every run row, summary() returns every key number and write_results() writes
results/ (README.md describes the CSV columns). Every interval comes from 2,000 resamples of the 99 questions, so summary()
takes about a minute per call. Results stay in memory, so write_results() after summary() reuses them. The analysis is a
line-by-line port of the script behind the numbers of Oct 24, 2026, and summary() returns that script's keys and values, to
the last bit. The keys keep the short names of the run rows:

  run rows and summary() keys         plain name used in results/ and the write-up
  oss20, oss120                       gpt-oss-20b, gpt-oss-120b
  q36, nemoS                          qwen3.6-35b (Qwen3.6-35B-A3B), nemotron-3-super (Nemotron-3-Super-120B-A12B)
  q4, q9                              qwen3.5-4b, qwen3.5-9b (dropped at the juror screening)
  q397, kimi                          qwen3.5-397b (the grader), kimi-k2.6 (the other grader candidate)
  sg20                                gpt-oss-safeguard-20b (the add-on juror, run on Modal)
  BFF, CMT                            finance answers (BFF-Bench), MT-Bench answers (Kensho's corrected MT-Bench)
  DYN-C                               the agreement jury: only jurors whose gut read and reasoned read agree vote
  DYN-SS                              the self-solve jury: only jurors that solved the question themselves vote
  FULL4 (FULL3, FULL5)                majority vote of all jurors, a tie counts as a reject
  GUT4 majority                       majority vote of the gut reads
  F-SYN                               own-answer reference: gpt-oss-120b's gut read with its own answer where the reference would go
  LOQO                                the best single judge chosen without the question being scored (leave one question out)
  J1, J2a, J2a_max, J2b               rule 1 and rule 2 differences in kappa (see decisions.csv)
  route                               matched coverage: each juror keeps the same number of answers under each routing rule
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, RUNS, RESULTS = ROOT / "data", ROOT / "runs", ROOT / "results"
B, BOOT_SEED = 2000, 20261023          # bootstrap resamples over questions, and the seed every bootstrap starts from

# Seed strings fixed when the experiment ran. They pick the finance answers, the MT-Bench reading order, routing tie breaks,
# the grader screening answers and the hand-check sample. Changing any of them changes the selection.
SALT_FINANCE_ANSWERS, SALT_FINANCE_TURNS = "P1", "P1-turns"
SALT_MTBENCH_ORDER, SALT_TIES, SALT_GRADER_CHECK, SALT_HAND_CHECK = "T1-cmt", "T1-ties", "T1-grader-gate", "T1-hand"

# Short name in the run rows -> (plain name, model id)
MODELS = {"oss20": ("gpt-oss-20b", "openai/gpt-oss-20b"), "oss120": ("gpt-oss-120b", "openai/gpt-oss-120b"),
          "q4": ("qwen3.5-4b", "Qwen/Qwen3.5-4B"), "q9": ("qwen3.5-9b", "Qwen/Qwen3.5-9B"),
          "q36": ("qwen3.6-35b", "Qwen/Qwen3.6-35B-A3B"), "nemoS": ("nemotron-3-super", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16"),
          "q397": ("qwen3.5-397b", "Qwen/Qwen3.5-397B-A17B"), "kimi": ("kimi-k2.6", "moonshotai/Kimi-K2.6"),
          "sg20": ("gpt-oss-safeguard-20b", "openai/gpt-oss-safeguard-20b")}
NAME = {k: v[0] for k, v in MODELS.items()}
SHORT = {v[0]: k for k, v in MODELS.items()}
JURORS = ["oss20", "oss120", "q4", "q9", "q36", "nemoS"]   # the six screened jurors, in this order
SUBSET3 = ["oss20", "oss120", "nemoS"]                     # the three-juror jury, closest to the planned design
GRADERS = ["q397", "kimi"]
SAFEGUARD = "sg20"
TOKEN_LIMIT = {"oss20": 4096, "oss120": 4096, "q4": 6144, "q9": 6144, "q36": 6144, "nemoS": 6144, "q397": 8192, "kimi": 8192, "sg20": 4096}
SETS = {"BFF": "finance", "CMT": "mt_bench"}


# ── statistics, copied unchanged ─────────────────────────────────────────────────────────────────────────────────────────
def seeded_order(ids, salt: str) -> list:
    """A fixed shuffle: sort the ids by sha1(salt|id)."""
    return sorted(ids, key=lambda i: hashlib.sha1((salt + "|" + i).encode()).hexdigest())


def kappa(a, g):
    """Cohen's kappa between two 0/1 vectors, nan when chance agreement is 1."""
    a = np.asarray(a, float); g = np.asarray(g, float)
    po = np.mean(a == g); pa = a.mean() * g.mean() + (1 - a.mean()) * (1 - g.mean())
    return np.nan if pa >= 1 else (po - pa) / (1 - pa)


def auroc(score, y):
    """Area under the ROC curve of score for the 0/1 outcome y, on finite scores, nan when y has one class."""
    from sklearn.metrics import roc_auc_score
    s, y = np.asarray(score, float), np.asarray(y, int); ok = np.isfinite(s)
    return np.nan if len(set(y[ok])) < 2 else roc_auc_score(y[ok], s[ok])


def _boot(ids, stat, qid, B=B, seed=BOOT_SEED):
    """Question-cluster bootstrap over the answers in ids: resample questions with replacement, a fresh generator per call.
    Returns (point, lo, hi) with the 2.5th and 97.5th percentiles; replicates where stat is None or not finite are dropped."""
    ids = list(ids); qs = sorted({qid[i] for i in ids}); byq = collections.defaultdict(list)
    for i in ids: byq[qid[i]].append(i)
    rng = np.random.default_rng(seed); vals = []
    for _ in range(B):
        v = stat([i for q in rng.choice(qs, len(qs)) for i in byq[q]])
        if v is not None and np.isfinite(v): vals.append(v)
    pt = stat(ids)
    if not vals: return float(pt) if pt is not None else np.nan, np.nan, np.nan
    lo, hi = np.percentile(vals, [2.5, 97.5]); return float(pt), float(lo), float(hi)


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


# ── the answers ───────────────────────────────────────────────────────────────────────────────────────────────────────────
_MEMO: dict = {}


def _pattern(c: int, i: int, n: int) -> str:
    """Expert votes as letters, majority first: C correct, I incorrect, N not sure (CCN = two correct, one not sure)."""
    return ("C" * c + "I" * i if c >= i else "I" * i + "C" * c) + "N" * n


def finance_pool() -> dict:
    """The 799 finance answers: every BFF-Bench answer in VERDICTS where at least 2 of 3 experts agree (the majority is the label),
    minus conversation fc9858ab, whose VERDICTS record stores the turn-1 reference where the question should be."""
    if "pool" not in _MEMO:
        V = pd.read_parquet(DATA / "verdicts.parquet"); V = V[V.dataset == "bffbench"]
        refs = {str(r.uid): [str(x) for x in r.references] for r in pd.read_parquet(DATA / "bffbench.parquet").itertuples()}
        votes = V.groupby(["cid", "turn"]).label.agg(list); out = {}
        for r in V.groupby(["cid", "turn"]).first().reset_index().itertuples():
            c = collections.Counter(votes[(r.cid, r.turn)]); C, I, N = c["Correct"], c["Incorrect"], c["Not sure"]
            if max(C, I) < 2 or r.qid == "fc9858ab":
                continue
            i = f"{r.cid}-t{r.turn}"
            out[i] = dict(item_id=i, qid=r.qid, gold=int(C > I), group="unanimous" if max(C, I) == 3 else ("two_plus_unsure" if min(C, I) == 0 else "split"),
                          conv=[{"role": m["role"], "content": m["content"]} for m in r.conv], ref=refs[str(r.qid)][int(r.turn) - 1],
                          ds="BFF", turn=int(r.turn), examinee=r.model, n_correct_votes=C, n_incorrect_votes=I, pattern=_pattern(C, I, N))
        _MEMO["pool"] = out
    return _MEMO["pool"]


def _finance_ids(n: int = 316) -> list:
    """Rank the answers within each question turn by seeded_order; order the turns by seeded_order; take rank 0 of every turn,
    then rank 1, and so on until n. With n = 316 this is exactly 2 answers from each of the 158 turns."""
    byt = collections.defaultdict(list)
    for i, x in finance_pool().items(): byt[x["qid"] + "|" + i[-2:]].append(i)
    ranked = {t: seeded_order(v, SALT_FINANCE_ANSWERS) for t, v in byt.items()}; order = seeded_order(sorted(byt), SALT_FINANCE_TURNS); out = []
    for r in range(6):
        for t in order:
            if len(out) < n and r < len(ranked[t]): out.append(ranked[t][r])
    return out


def _mtbench() -> dict:
    """The 228 MT-Bench answers: VERDICTS rows with dataset mtbmr (240 responses, 3 expert labels each) where at least 2 of 3 agree,
    with the corrected reference of that question turn from CMTBench."""
    V = pd.read_parquet(DATA / "verdicts.parquet"); V = V[V.dataset == "mtbmr"]
    refs = {str(r.uid): [str(x) for x in r.references] for r in pd.read_parquet(DATA / "cmtbench.parquet").itertuples()}
    out = {}
    for cid, g in V.groupby("cid"):
        labs = list(g.label); c, i = labs.count("Correct"), labs.count("Incorrect")
        if max(c, i) < 2: continue
        r = g.iloc[0]
        out[f"cmt-{cid}"] = dict(item_id=f"cmt-{cid}", qid=r.qid, gold=1 if c >= 2 else 0,
                                 group="unanimous" if max(c, i) == 3 else ("two_plus_unsure" if min(c, i) == 0 else "split"),
                                 conv=[dict(role=m["role"], content=m["content"]) for m in r.conv], ref=refs[str(r.qid)][int(r.turn) - 1],
                                 ds="CMT", turn=int(r.turn), examinee=r.model, n_correct_votes=c, n_incorrect_votes=i,
                                 pattern=_pattern(c, i, 3 - c - i))
    return out


def _ctx() -> dict:
    """Answers in reading order (316 finance, then 228 MT-Bench), question turns and the lookups the analysis uses."""
    if "ctx" in _MEMO:
        return _MEMO["ctx"]
    pool = finance_pool(); bff = _finance_ids(316); cmt = _mtbench(); cmt_ids = seeded_order(list(cmt), SALT_MTBENCH_ORDER)
    items = {i: pool[i] for i in bff}; items.update({i: cmt[i] for i in cmt_ids})
    order = bff + cmt_ids
    assert len(order) == 544 and not ({items[i]["qid"] for i in bff} & {items[i]["qid"] for i in cmt_ids})
    turns = {}
    for i in order:
        x = items[i]; k = f"{x['qid']}|t{x['turn']}"; users = [m["content"] for m in x["conv"] if m["role"] == "user"]
        assert len(users) == x["turn"], (i, len(users))
        if k in turns:
            assert turns[k]["users"] == users and turns[k]["ref"] == x["ref"], k
        else:
            turns[k] = dict(qid=x["qid"], turn=f"t{x['turn']}", users=users, ref=x["ref"], any_item=i, ds=x["ds"])
    _MEMO["ctx"] = dict(items=items, order=order, bff=bff, cmt=cmt_ids, turns=turns,
                        GOLD={i: items[i]["gold"] for i in order}, DS={i: items[i]["ds"] for i in order}, QID={i: items[i]["qid"] for i in order},
                        EXAMINEE={i: items[i]["examinee"] for i in order}, PAT={i: items[i]["pattern"] for i in order},
                        DISSENT={i: int(items[i]["pattern"] not in ("CCC", "III")) for i in order})
    return _MEMO["ctx"]


def turn_of(i: str) -> str:
    """The question turn of an answer, as in the run rows: '<question id>|t1' or '<question id>|t2'."""
    x = _ctx()["items"][i]; return f"{x['qid']}|t{x['turn']}"


def items() -> pd.DataFrame:
    """The 544 answers in reading order: 316 finance answers (2 per question turn, 79 conversations) and 228 MT-Bench answers
    (40 question turns, 20 questions). No juror saw the reference."""
    X = _ctx(); rows = []
    for k, i in enumerate(X["order"], 1):
        x = X["items"][i]
        rows.append(dict(item_id=i, answer_set=SETS[x["ds"]], question_id=x["qid"], turn=x["turn"], order=k, examinee=x["examinee"],
                         label_correct=x["gold"], group=x["group"], n_correct_votes=x["n_correct_votes"], n_incorrect_votes=x["n_incorrect_votes"],
                         expert_votes=x["pattern"], conv=x["conv"], ref=x["ref"]))
    return pd.DataFrame(rows)


def turns() -> dict:
    """The 198 question turns ('<question id>|t1' or '|t2'): the user messages up to that turn, the expert reference and the set."""
    return _ctx()["turns"]


def grader_check_ids() -> list:
    """The 150 finance answers of the grader screening (from the 799, seeded order)."""
    return seeded_order(sorted(finance_pool()), SALT_GRADER_CHECK)[:150]


def juror_check_ids() -> list:
    """The 100 finance answers of the juror screening: the first 100 in reading order."""
    return _ctx()["bff"][:100]


def duplicate_ids() -> list:
    """The 40 answers read a second time to measure noise: the first 40 in reading order."""
    return _ctx()["order"][:40]


# ── the runs ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def runs() -> pd.DataFrame:
    """Every row in runs/ (all .jsonl files), with the folder and file it came from. Fields differ by kind of run; see README.md."""
    rows = []
    for p in sorted(RUNS.rglob("*.jsonl")):
        for r in _jsonl(p):
            rows.append(dict(folder=p.parent.name, file=p.name, **r))
    return pd.DataFrame(rows)


def screening_decisions() -> dict:
    """The two screening decisions as saved by the run: grader_check (stage 1) and juror_check (stage 2)."""
    return json.loads((RUNS / "screening_decisions.json").read_text())


def screening() -> dict:
    """The two screening decisions recomputed from the rows in runs/checks/, in the saved format (equal to screening_decisions())."""
    X = _ctx()
    d1 = dict(kappa={}, kappa_parsed={}, unparsed={})
    for g in GRADERS:
        rr = _jsonl(RUNS / f"checks/grader__{NAME[g]}.jsonl")
        d1["kappa"][g] = float(kappa([int(r["v"] == 1) for r in rr], [r["gold"] for r in rr]))
        pp = [r for r in rr if r["v"] != -1]
        d1["kappa_parsed"][g] = float(kappa([r["v"] for r in pp], [r["gold"] for r in pp]))
        d1["unparsed"][g] = len(rr) - len(pp)
    best = max(d1["kappa"], key=lambda s: (d1["kappa"][s], s == "q397")); d1["chosen"] = best; d1["pass"] = d1["kappa"][best] >= 0.80
    d2 = dict(metrics={}, kept=[], dropped=[])
    for s in JURORS:
        g = _jsonl(RUNS / f"checks/juror__{NAME[s]}__gut.jsonl"); rs = _jsonl(RUNS / f"checks/juror__{NAME[s]}__reasoned.jsonl")
        mg = np.array([r["margin"] for r in g], float); gold = [X["GOLD"][r["item_id"]] for r in g]
        au = float(auroc(-mg, gold)); nan = float(np.mean(~np.isfinite(mg))); pr = float(np.mean([r["v"] != -1 for r in rs]))
        ok = au >= 0.60 and pr >= 0.90 and nan <= 0.05
        d2["metrics"][s] = dict(gut_auroc=au, parse_rate=pr, nan_rate=nan, length_rate=float(np.mean([r["finish"] == "length" for r in rs])), passed=ok)
        (d2["kept"] if ok else d2["dropped"]).append(s)
    return {"grader_check": d1, "juror_check": d2}


# ── the analysis ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def _j(o):
    """Make the result JSON-ready the way the original script did: tuples become lists, non-finite floats become None."""
    if isinstance(o, dict): return {str(k): _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_j(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    return o


def summary(safeguard: bool = False) -> dict:
    """Every key number, with the same keys and values as the run's analysis output. safeguard=True adds gpt-oss-safeguard-20b as a
    fifth juror (it has no self-solve run, so it never votes in the self-solve jury)."""
    return _j(_analysis(safeguard)["key"])


def _analysis(safeguard: bool = False) -> dict:
    if ("analysis", safeguard) not in _MEMO:
        _MEMO[("analysis", safeguard)] = _analyze(safeguard)
    return _MEMO[("analysis", safeguard)]


def _analyze(ADD_SG: bool) -> dict:
    """The original analysis, step by step. Returns key (the summary) and tables (the rows of every results/ file)."""
    X = _ctx(); ORDER, GOLD, DS, QID, TURNS = X["order"], X["GOLD"], X["DS"], X["QID"], X["turns"]
    EXAMINEE, PAT, DISSENT = X["EXAMINEE"], X["PAT"], X["DISSENT"]
    boot = lambda ids, stat: _boot(ids, stat, QID)
    D2 = screening_decisions()["juror_check"]
    KEPT = [s for s in JURORS if s in D2["kept"]]
    SUB3 = [s for s in SUBSET3 if s in KEPT]
    IDS = list(ORDER); BFF = [i for i in IDS if DS[i] == "BFF"]; CMT = [i for i in IDS if DS[i] == "CMT"]
    G = GOLD; KEY = {}; T = collections.defaultdict(list)

    # load reads
    MG, V, FIN = collections.defaultdict(dict), collections.defaultdict(dict), collections.defaultdict(dict)
    for s in JURORS:
        for r in _jsonl(RUNS / f"reads/{NAME[s]}__gut.jsonl") + _jsonl(RUNS / f"reads/{NAME[s]}__reasoned.jsonl"):
            if r["mode"] == "gut": MG[r["juror"]][r["item_id"]] = r["margin"]
            else: V[r["juror"]][r["item_id"]] = r["v"]; FIN[r["juror"]][r["item_id"]] = r["finish"]
    if ADD_SG:
        sg = _jsonl(RUNS / f"reads/{NAME[SAFEGUARD]}__gut.jsonl") + _jsonl(RUNS / f"reads/{NAME[SAFEGUARD]}__reasoned.jsonl")
        assert sg, "the safeguard reads are missing from runs/reads/"
        for r in sg:
            if r["mode"] == "gut": MG[SAFEGUARD][r["item_id"]] = r["margin"]
            else: V[SAFEGUARD][r["item_id"]] = r["v"]; FIN[SAFEGUARD][r["item_id"]] = r["finish"]
        KEPT = KEPT + [SAFEGUARD]
    g5 = _jsonl(RUNS / "self_solve/grades__qwen3.5-397b.jsonl")
    ST = {(r["juror"], r["turn"]): r["status"] for r in g5}
    HAS_OWN = {(r["juror"], r["turn"]): r["has_own"] for r in g5}
    DUPG, DUPV = collections.defaultdict(dict), collections.defaultdict(dict); SR = collections.defaultdict(dict)
    for s in JURORS:
        for r in _jsonl(RUNS / f"duplicates/{NAME[s]}__gut.jsonl") + _jsonl(RUNS / f"duplicates/{NAME[s]}__reasoned.jsonl"):
            (DUPG if r["mode"] == "gut" else DUPV)[r["juror"]][r["item_id"]] = r["margin"] if r["mode"] == "gut" else r["v"]
        for r in _jsonl(RUNS / f"reads/{NAME[s]}__own_answer_reference.jsonl"):
            SR[r["juror"]][r["item_id"]] = r["margin"]

    fin = lambda x: x is not None and np.isfinite(x)

    def gutv(j, i, strict=True):
        m = MG[j].get(i); return (int(m < 0) if fin(m) else (0 if strict else None))

    def resv(j, i, strict=True):
        v = V[j].get(i, -1); return (int(v == 1) if (strict or v != -1) else None)

    def absm(j, i):
        m = MG[j].get(i); return abs(m) if fin(m) else -1.0

    def cert_c(j, i, literal=False):
        g = gutv(j, i, strict=literal); v = V[j].get(i, -1)
        if literal: return g == int(v == 1)
        return g is not None and v != -1 and g == v

    def cert_ss(j, i): return ST.get((j, turn_of(i))) == "solved"

    def conflict(j, i):
        m = MG[j].get(i)
        if not fin(m): return np.nan
        return m if resv(j, i) == 1 else -m

    # policies -> {answer: 1 accept, 0 reject, or None}
    def single(j, mode, strict=True):
        f = gutv if mode == "gut" else resv; return {i: f(j, i, strict) for i in IDS}

    def majority(js, mode="reasoned", strict=True, tie="reject", tiebreak=None):
        out = {}
        for i in IDS:
            f = gutv if mode == "gut" else resv; vs = [f(j, i, strict) for j in js]; vs = [v for v in vs if v is not None]
            if not vs: out[i] = 0 if strict else None; continue
            a = sum(vs); n = len(vs)
            if 2 * a > n: out[i] = 1
            elif 2 * a < n: out[i] = 0
            else: out[i] = 0 if tie == "reject" else resv(tiebreak, i)
        return out

    def dynamic(js, certf, fallback):
        out, ncert = {}, {}
        for i in IDS:
            cj = [j for j in js if certf(j, i)]; ncert[i] = len(cj)
            if not cj: out[i] = fallback[i]; continue
            vs = [resv(j, i) for j in cj]; a = sum(vs)
            if 2 * a > len(vs): out[i] = 1
            elif 2 * a < len(vs): out[i] = 0
            else: out[i] = resv(max(cj, key=lambda j: (absm(j, i), -js.index(j))), i)
        return out, ncert

    def kap(Vd, ids):
        ids = [i for i in ids if Vd.get(i) is not None]
        if len(ids) < 2: return np.nan
        return kappa([Vd[i] for i in ids], [G[i] for i in ids])

    def fr(Vd, ids):
        x = [1 - Vd[i] for i in ids if G[i] == 1 and Vd.get(i) is not None]; return np.mean(x) if x else np.nan

    def fa(Vd, ids):
        x = [Vd[i] for i in ids if G[i] == 0 and Vd.get(i) is not None]; return np.mean(x) if x else np.nan

    def bs(stat, ids=IDS): return boot(list(ids), stat)

    def build(js):
        pol = {}
        best_r = max(js, key=lambda j: kap(single(j, "reasoned"), IDS))
        for j in js:
            pol[f"{j} reasoned"] = single(j, "reasoned"); pol[f"{j} gut"] = single(j, "gut")
        n = len(js)
        pol[f"FULL{n}"] = majority(js); pol[f"FULL{n} tie->best ({best_r})"] = majority(js, tie="best", tiebreak=best_r)
        pol[f"GUT{n} majority"] = majority(js, "gut")
        dc, ncC = dynamic(js, cert_c, pol[f"FULL{n}"]); ds, ncS = dynamic(js, cert_ss, pol[f"FULL{n}"])
        dcl, _ = dynamic(js, lambda j, i: cert_c(j, i, literal=True), pol[f"FULL{n}"])
        pol["DYN-C"] = dc; pol["DYN-SS"] = ds; pol["DYN-C literal (unparsed=reject certifies)"] = dcl
        return pol, ncC, ncS, best_r

    def policy_table(pol, njur):
        tab = {}
        for nm, Vd in pol.items():
            cells = []
            for ids, set_name in ((BFF, "finance"), (CMT, "mt_bench"), (IDS, "all")):
                t = bs(lambda x: kap(Vd, x), ids); cells.append((t, fr(Vd, ids), fa(Vd, ids)))
                rule, juror = _rule_name(nm)
                T["results_by_rule"].append(dict(jurors=njur, rule=rule, juror=juror, answer_set=set_name, answers=len(ids), kappa=t[0],
                                                 kappa_lo=t[1], kappa_hi=t[2], false_reject=cells[-1][1], false_accept=cells[-1][2]))
            tab[nm] = cells
        return tab

    nK = len(KEPT)
    # 1. what ran
    for ids, set_name in ((BFF, "finance"), (CMT, "mt_bench"), (IDS, "all")):
        tk = {turn_of(i) for i in ids}
        T["answer_sets"].append(dict(answer_set=set_name, answers=len(ids), question_turns=len(tk), questions=len({QID[i] for i in ids}),
                                     label_correct=sum(G[i] for i in ids), examinees=len({EXAMINEE[i] for i in ids})))
    for j in KEPT:
        T["juror_reads"].append(dict(jurors=nK, juror=NAME[j], answers=len(IDS), no_verdict=sum(V[j][i] == -1 for i in IDS),
                                     hit_token_limit=sum(FIN[j][i] == "length" for i in IDS), gut_margin_missing=sum(not fin(MG[j].get(i)) for i in IDS),
                                     accept_rate_reasoned=np.mean([resv(j, i) for i in IDS]), accept_rate_gut=np.mean([gutv(j, i) for i in IDS]),
                                     agrees_with_itself_rate=np.mean([cert_c(j, i) for i in IDS]),
                                     solved_rate=np.mean([cert_ss(j, i) for i in IDS]) if j != SAFEGUARD else np.nan))
    SSJ = [j for j in KEPT if j != SAFEGUARD]
    for j in SSJ:
        for set_name, keep in (("all", None), ("finance", "BFF"), ("mt_bench", "CMT")):
            ts = [t for t in TURNS if keep is None or TURNS[t]["ds"] == keep]; c = collections.Counter(ST.get((j, t)) for t in ts)
            T["self_solve"].append(dict(juror=NAME[j], answer_set=set_name, question_turns=len(ts), solved=c["solved"], unsolved=c["unsolved"],
                                        contested=c["contested"], no_own_answer=sum(not HAS_OWN.get((j, t), False) for t in ts)))
    KEY["status"] = {j: dict(collections.Counter(ST.get((j, t)) for t in TURNS)) for j in SSJ}

    # 2. headline
    POL, NC_C, NC_S, BEST_R = build(KEPT)
    TAB = policy_table(POL, nK)
    singles = [k for k in POL if k.endswith(" reasoned") or k.endswith(" gut")]
    BEST1 = max(singles, key=lambda k: kap(POL[k], IDS)); KEY["best_single"] = BEST1
    n = len(KEPT); fpo = majority(KEPT, strict=False)
    po = []
    for j in KEPT:
        po.append(("reasoned read", j, single(j, "reasoned", False))); po.append(("gut read", j, single(j, "gut", False)))
    po += [("majority vote", None, fpo), ("gut majority vote", None, majority(KEPT, "gut", strict=False)),
           ("agreement jury", None, dynamic(KEPT, cert_c, fpo)[0]), ("self-solve jury", None, dynamic(KEPT, cert_ss, fpo)[0])]
    for rule, j, Vd in po:
        T["results_parsed_only"].append(dict(jurors=n, rule=rule, juror=NAME[j] if j else "", answer_set="all",
                                             answers=sum(Vd[i] is not None for i in IDS), kappa=kap(Vd, IDS)))

    # 3. primary contrasts
    FULL = POL[f"FULL{n}"]

    def dk(a, b): return lambda x: kap(a, x) - kap(b, x)
    J1 = bs(dk(POL["DYN-C"], POL["DYN-SS"])); J2s = bs(dk(POL["DYN-C"], POL[BEST1])); J2f = bs(dk(POL["DYN-C"], FULL))
    J2max = bs(lambda x: kap(POL["DYN-C"], x) - max(kap(POL[k], x) for k in singles))
    best_name = f"best single judge ({NAME[BEST1.split(' ')[0]]} {BEST1.split(' ')[1]} read)"

    def contrast(rule, minus, set_name, t, njur=n):
        T["contrasts"].append(dict(jurors=njur, rule=rule, minus=minus, answer_set=set_name, difference=t[0], lo=t[1], hi=t[2]))
    contrast("agreement jury", "self-solve jury", "all", J1); contrast("agreement jury", best_name, "all", J2s)
    contrast("agreement jury", "best single judge, chosen again in each resample", "all", J2max); contrast("agreement jury", "majority vote", "all", J2f)
    for ids, set_name in ((BFF, "finance"), (CMT, "mt_bench")):
        contrast("agreement jury", "self-solve jury", set_name, bs(dk(POL["DYN-C"], POL["DYN-SS"]), ids))
        contrast("agreement jury", best_name, set_name, bs(dk(POL["DYN-C"], POL[BEST1]), ids))
        contrast("agreement jury", "majority vote", set_name, bs(dk(POL["DYN-C"], FULL), ids))
    contrast("self-solve jury", "majority vote", "all", bs(dk(POL["DYN-SS"], FULL)))
    contrast("self-solve jury", best_name, "all", bs(dk(POL["DYN-SS"], POL[BEST1])))
    contrast("majority vote", best_name, "all", bs(dk(FULL, POL[BEST1])))
    contrast("gut majority vote", "majority vote", "all", bs(dk(POL[f"GUT{n} majority"], FULL)))
    cw = J1[0] >= 0.04 and J1[1] > 0; ssw = J1[0] <= -0.04 and J1[2] < 0
    djw = J2s[0] >= 0.03 and J2s[1] > 0 and J2f[0] >= 0
    KEY.update(J1=J1, J2a=J2s, J2a_max=J2max, J2b=J2f, cert_wins=cw, ss_wins=ssw, djw=djw)
    _decisions(T, n, J1, J2s, J2f, cw, ssw, djw, best_name)

    # 4. the answers no juror vouches for (no juror agrees with itself)
    UNC = [i for i in IDS if NC_C[i] == 0]; COV = [i for i in IDS if NC_C[i] > 0]

    def cov_row(measure, value, lo=np.nan, hi=np.nan, njur=n):
        T["coverage"].append(dict(jurors=njur, measure=measure, value=value, lo=lo, hi=hi))
    cov_row("answers where no juror agrees with itself", len(UNC)); cov_row("share of answers where no juror agrees with itself", len(UNC) / len(IDS))
    cov_row("finance answers where no juror agrees with itself", sum(DS[i] == "BFF" for i in UNC))
    cov_row("MT-Bench answers where no juror agrees with itself", sum(DS[i] == "CMT" for i in UNC))
    cov_row("questions among them", len({QID[i] for i in UNC}))
    cov_row("share labelled correct, no juror agrees", np.mean([G[i] for i in UNC]) if UNC else np.nan)
    cov_row("share labelled correct, some juror agrees", np.mean([G[i] for i in COV]))
    cov_row("share with expert dissent, no juror agrees", np.mean([DISSENT[i] for i in UNC]) if UNC else np.nan)
    cov_row("share with expert dissent, some juror agrees", np.mean([DISSENT[i] for i in COV]))
    if UNC:
        ratio = bs(lambda x: (np.mean([DISSENT[i] for i in x if NC_C[i] == 0]) / max(1e-9, np.mean([DISSENT[i] for i in x if NC_C[i] > 0])))
                   if any(NC_C[i] == 0 for i in x) else np.nan)
        cov_row("expert dissent rate, no juror agrees, divided by the rate where some juror agrees", *ratio)

    def loqo_best(ids_all):
        out = {}
        for q in sorted({QID[i] for i in ids_all}):
            other = [i for i in IDS if QID[i] != q]; b = max(singles, key=lambda k: kap(POL[k], other))
            for i in ids_all:
                if QID[i] == q: out[i] = POL[b][i]
        return out
    LOQO = loqo_best(IDS)
    o120 = "oss120"
    FSYN = {i: (int(SR[o120][i] < 0) if fin(SR[o120].get(i)) else None) for i in IDS}
    FSYN_FILL = {i: (FSYN[i] if FSYN[i] is not None else FULL[i]) for i in IDS}
    FB = {f"FULL{n}": FULL, f"GUT{n} majority": POL[f"GUT{n} majority"], "best single LOQO": LOQO, "F-SYN (120b gut, own answer as reference; FULL fill)": FSYN_FILL,
          "F-SYN where 120b has own answer": FSYN}
    FB_NAME = {f"FULL{n}": "majority vote", f"GUT{n} majority": "gut majority vote", "best single LOQO": "best single judge, chosen without the question",
               "F-SYN (120b gut, own answer as reference; FULL fill)": "own-answer reference (gpt-oss-120b gut read), majority vote where it has no own answer",
               "F-SYN where 120b has own answer": "own-answer reference, answers where gpt-oss-120b has its own answer"}
    if UNC:
        for nm, Vd in FB.items():
            ids = [i for i in UNC if Vd.get(i) is not None]
            t = bs(lambda x: kap(Vd, x), ids) if len(ids) > 5 else (kap(Vd, ids), np.nan, np.nan)
            T["uncovered_fallbacks"].append(dict(fallback=FB_NAME[nm], answers=len(ids), kappa=t[0], kappa_lo=t[1], kappa_hi=t[2],
                                                 false_reject=fr(Vd, ids), false_accept=fa(Vd, ids)))
        cov_row("share of answers where some juror agrees with itself (the rest go to a person)", len(COV) / len(IDS))
        t = bs(lambda x: kap(POL["DYN-C"], x), COV)
        cov_row("kappa of the agreement jury where some juror agrees with itself", *t)
        KEY["uncovered"] = dict(share=len(UNC) / len(IDS), n=len(UNC), fallbacks={nm: kap(Vd, UNC) for nm, Vd in FB.items()})
    cov_row("kappa of the agreement jury where no juror agrees with itself", kap(POL["DYN-C"], UNC) if len(UNC) > 1 else np.nan)
    cov_row("distinct sets of jurors that agree with themselves", len({tuple(j for j in KEPT if cert_c(j, i)) for i in IDS}))
    for k in range(0, len(KEPT) + 1):
        for count_of, NC, jury in (("agree with themselves", NC_C, "DYN-C"), ("solved the question", NC_S, "DYN-SS")):
            ids = [i for i in IDS if NC[i] == k]
            T["kappa_by_juror_count"].append(dict(jurors=n, count_of=count_of, count=k, answers=len(ids), kappa_jury=kap(POL[jury], ids) if ids else np.nan,
                                                  kappa_majority=kap(FULL, ids) if ids else np.nan,
                                                  accuracy_jury=np.mean([POL[jury][i] == G[i] for i in ids]) if ids else np.nan,
                                                  share_correct=np.mean([G[i] for i in ids]) if ids else np.nan))
    T["kappa_by_juror_count"].sort(key=lambda r: (r["count_of"] != "agree with themselves", r["count"]))

    # post hoc: what ranks the errors of the majority vote
    EF = {i: int(FULL[i] != G[i]) for i in IDS}
    SC = {"fewer self-consistent jurors (-n certified, DYN-C)": {i: -NC_C[i] for i in IDS},
          "fewer self-solvers (-n solved, DYN-SS)": {i: -NC_S[i] for i in IDS},
          "jury disagreement (-|accepts - rejects| of reasoned votes)": {i: -abs(2 * sum(resv(j, i) for j in KEPT) - len(KEPT)) for i in IDS},
          "weak summed gut confidence (-|sum of gut margins|)": {i: -abs(sum(MG[j][i] for j in KEPT if fin(MG[j].get(i)))) for i in IDS}}
    SC_NAME = ["fewer jurors agree with themselves", "fewer jurors solved the question", "jurors' reasoned votes are split",
               "weak summed gut margin"]
    for (nm, sc), plain in zip(SC.items(), SC_NAME):
        t = bs(lambda x: auroc([sc[i] for i in x], [EF[i] for i in x]))
        T["error_rankers"].append(dict(measure="auroc", score=plain, compared_with="", estimate=t[0], lo=t[1], hi=t[2]))
    d_ = bs(lambda x: auroc([SC[list(SC)[0]][i] for i in x], [EF[i] for i in x]) - auroc([SC[list(SC)[2]][i] for i in x], [EF[i] for i in x]))
    d2_ = bs(lambda x: auroc([SC[list(SC)[0]][i] for i in x], [EF[i] for i in x]) - auroc([SC[list(SC)[1]][i] for i in x], [EF[i] for i in x]))
    d3_ = bs(lambda x: auroc([SC[list(SC)[0]][i] for i in x], [EF[i] for i in x]) - auroc([SC[list(SC)[3]][i] for i in x], [EF[i] for i in x]))
    for t, k in ((d_, 2), (d2_, 1), (d3_, 3)):
        T["error_rankers"].append(dict(measure="auroc difference", score=SC_NAME[0], compared_with=SC_NAME[k], estimate=t[0], lo=t[1], hi=t[2]))
    KEY["ncert_minus_gutconf"] = d3_
    KEY["jury_rankers"] = {nm: auroc([sc[i] for i in IDS], [EF[i] for i in IDS]) for nm, sc in SC.items()}; KEY["ncert_minus_disagree"] = d_; KEY["ncert_minus_nsolved"] = d2_

    # 5. the self-solve gap test (latent solver)
    UN = {st: [(j, i) for j in KEPT for i in IDS if ST.get((j, turn_of(i))) == st] for st in ("solved", "unsolved", "contested")}

    def boot_units(units, stat, B=B, seed=BOOT_SEED):
        qs = sorted({QID[i] for _, i in units}); byq = collections.defaultdict(list)
        for u in units: byq[QID[u[1]]].append(u)
        rng = np.random.default_rng(seed); vals = []
        for _ in range(B):
            v = stat([u for q in rng.choice(qs, len(qs)) for u in byq[q]])
            if np.isfinite(v): vals.append(v)
        lo, hi = np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan); return float(stat(units)), float(lo), float(hi)

    def au_units(us):
        return auroc([conflict(j, i) for j, i in us], [int(resv(j, i) != G[i]) for j, i in us]) if us else np.nan
    nq_un = len({QID[i] for _, i in UN["unsolved"]}); KEY["latent_qids"] = nq_un

    def lat_row(juror, status, us, t):
        T["latent_solver"].append(dict(juror=juror, self_solve_status=status, units=len(us), questions=len({QID[i] for _, i in us}),
                                       error_rate=np.mean([resv(j, i) != G[i] for j, i in us]) if us else np.nan, auroc=t[0], auroc_lo=t[1], auroc_hi=t[2]))
    for st, us in UN.items():
        lat_row("all", st, us, boot_units(us, au_units) if len(us) > 10 else (au_units(us), np.nan, np.nan))
    SU = UN["solved"] + UN["unsolved"]

    def gapA(us): return au_units([u for u in us if ST[(u[0], turn_of(u[1]))] == "solved"]) - au_units([u for u in us if ST[(u[0], turn_of(u[1]))] == "unsolved"])
    A_u = boot_units(UN["unsolved"], au_units); A_gap = boot_units(SU, gapA)
    sens_us = [u for u in UN["unsolved"] if HAS_OWN.get((u[0], turn_of(u[1])))]
    lat_row("all", "unsolved, own answer present", sens_us, boot_units(sens_us, au_units))
    T["latent_solver"].append(dict(juror="all", self_solve_status="solved minus unsolved", units=len(SU), questions=len({QID[i] for _, i in SU}),
                                   error_rate=np.nan, auroc=A_gap[0], auroc_lo=A_gap[1], auroc_hi=A_gap[2]))
    for j in KEPT:
        if j == SAFEGUARD: continue
        for st in ("unsolved", "solved"):
            us = [u for u in UN[st] if u[0] == j]; lat_row(NAME[j], st, us, (au_units(us), np.nan, np.nan))
    if nq_un < 30:
        hsub = hlat = None
    else:
        hsub = A_u[0] >= 0.65 and A_u[1] >= 0.55; hlat = A_u[0] <= 0.60 and A_gap[0] >= 0.10
        KEY.update(hsub=hsub, hlat=hlat)
    KEY.update(A_unsolved=A_u, A_gap=A_gap)
    T["decisions"].append(dict(decision="self-solve gap test: does self-agreement still flag errors on questions the juror could not solve?",
                               jurors=n, outcome=("too few questions" if hsub is None else "holds" if hsub else "vanishes" if hlat else "in between"),
                               reads=f"{nq_un} questions with an unsolved unit, AUROC on unsolved units {A_u[0]:.3f} [{A_u[1]:.3f}, {A_u[2]:.3f}], "
                                     f"solved minus unsolved {A_gap[0]:+.3f} [{A_gap[1]:+.3f}, {A_gap[2]:+.3f}]",
                               needs="holds: AUROC on unsolved units >= 0.65 with lower bound >= 0.55. vanishes: AUROC on unsolved units <= 0.60 "
                                     "and solved minus unsolved >= +0.10. At least 30 questions with an unsolved unit."))
    for st in ("solved", "unsolved"):
        us = [(j, i) for j, i in UN[st] if fin(SR[j].get(i))]
        if not us: continue
        own_v = {u: int(SR[u[0]][u[1]] < 0) for u in us}
        a_own = np.mean([resv(j, i) == own_v[(j, i)] for j, i in us]); a_gold = np.mean([resv(j, i) == G[i] for j, i in us])
        g_own = np.mean([gutv(j, i) == own_v[(j, i)] for j, i in us]); g_gold = np.mean([gutv(j, i) == G[i] for j, i in us])
        d = boot_units(us, lambda x: np.mean([resv(j, i) == int(SR[j][i] < 0) for j, i in x]) - np.mean([resv(j, i) == G[i] for j, i in x]))
        T["own_answer_index"].append(dict(self_solve_status=st, units=len(us), reasoned_matches_own=a_own, reasoned_matches_label=a_gold,
                                          difference=d[0], lo=d[1], hi=d[2], gut_matches_own=g_own, gut_matches_label=g_gold))

    # matched coverage: each juror keeps the share of answers it solved, under each routing rule
    TIE = {i: k for k, i in enumerate(seeded_order(IDS, SALT_TIES))}

    def route(score, ids, c, high=False):
        ids = list(ids); k = int(round(c * len(ids)))

        def key(i):
            s = score(i); ok = np.isfinite(s); return (0 if ok else 1, (-s if high else s) if ok else 0, TIE[i])
        return sorted(ids, key=key)[:k]
    rng = np.random.default_rng(20261023); RT = {}
    for j in SSJ:
        Sj = single(j, "reasoned"); Gj = single(j, "gut")

        def cov(x): return np.mean([cert_ss(j, i) for i in x])

        def kSS(x): return kap(Sj, [i for i in x if cert_ss(j, i)])

        def kS(x): return kap(Sj, route(lambda i: conflict(j, i), x, cov(x)))

        def kCR(x): return kap(Sj, route(lambda i: absm(j, i), x, cov(x), high=True))

        def kCG(x): return kap(Gj, route(lambda i: absm(j, i), x, cov(x), high=True))
        c = cov(IDS); k = int(round(c * len(IDS)))
        rk = [kap(Sj, list(rng.choice(IDS, k, replace=False))) for _ in range(1000)]
        dB = bs(lambda x: kS(x) - kSS(x)); dR = bs(lambda x: kS(x) - kCR(x)); dG = bs(lambda x: kS(x) - kCG(x))
        RT[j] = dict(c=c, SS=kSS(IDS), s=kS(IDS), CR=kCR(IDS), CG=kCG(IDS), rand=float(np.mean(rk)), rand95=float(np.percentile(rk, 95)), dB=dB, dR=dR, dG=dG)
        T["matched_coverage"].append(dict(juror=NAME[j], coverage=c, answers_kept=k, kappa_self_solve=RT[j]["SS"], kappa_self_agreement=RT[j]["s"],
                                          kappa_reasoned_confidence=RT[j]["CR"], kappa_gut_confidence=RT[j]["CG"], kappa_random_mean=RT[j]["rand"],
                                          kappa_random_95th=RT[j]["rand95"],
                                          self_agreement_minus_self_solve=dB[0], self_agreement_minus_self_solve_lo=dB[1], self_agreement_minus_self_solve_hi=dB[2],
                                          self_agreement_minus_reasoned_confidence=dR[0], self_agreement_minus_reasoned_confidence_lo=dR[1],
                                          self_agreement_minus_reasoned_confidence_hi=dR[2],
                                          self_agreement_minus_gut_confidence=dG[0], self_agreement_minus_gut_confidence_lo=dG[1],
                                          self_agreement_minus_gut_confidence_hi=dG[2],
                                          kappa_unsolved=kap(Sj, [i for i in IDS if ST[(j, turn_of(i))] == "unsolved"]),
                                          auroc_unsolved_flag=auroc([int(ST[(j, turn_of(i))] == "unsolved") for jj, i in SU if jj == j],
                                                                    [int(resv(j, i) != G[i]) for jj, i in SU if jj == j])))
    KEY["route"] = RT
    for r in T["juror_reads"]:
        r["auroc_disagreement_error"] = au_units([(SHORT[r["juror"]], i) for i in IDS])

    # the three-juror jury
    if len(SUB3) >= 2:
        POL3, NC3, NS3, _ = build(SUB3)
        policy_table(POL3, len(SUB3))
        s3 = [k for k in POL3 if k.endswith(" reasoned") or k.endswith(" gut")]; b3 = max(s3, key=lambda k: kap(POL3[k], IDS)); F3 = [k for k in POL3 if k.startswith("FULL")][0]
        j1 = bs(dk(POL3["DYN-C"], POL3["DYN-SS"])); j2s = bs(dk(POL3["DYN-C"], POL3[b3])); j2f = bs(dk(POL3["DYN-C"], POL3[F3]))
        b3_name = f"best single judge ({NAME[b3.split(' ')[0]]} {b3.split(' ')[1]} read)"
        contrast("agreement jury", "self-solve jury", "all", j1, len(SUB3)); contrast("agreement jury", b3_name, "all", j2s, len(SUB3))
        contrast("agreement jury", "majority vote", "all", j2f, len(SUB3))
        _decisions(T, len(SUB3), j1, j2s, j2f, j1[0] >= 0.04 and j1[1] > 0, j1[0] <= -0.04 and j1[2] < 0,
                   j2s[0] >= 0.03 and j2s[1] > 0 and j2f[0] >= 0, b3_name)
        cov_row("share of answers where no juror agrees with itself", np.mean([NC3[i] == 0 for i in IDS]), njur=len(SUB3))
        KEY["sub3"] = dict(J1=j1, J2a=j2s, J2b=j2f, best=b3, dync=kap(POL3["DYN-C"], IDS), dynss=kap(POL3["DYN-SS"], IDS), full=kap(POL3[F3], IDS))

    # noise: repeat reads of the first 40 answers
    d40 = ORDER[:40]; flips_all = []
    for j in KEPT:
        if not DUPV[j]: continue
        fv = sum(int(DUPV[j][i] == 1) != resv(j, i) for i in d40); fg = sum((DUPG[j][i] < 0) != (MG[j][i] < 0) for i in d40 if fin(DUPG[j].get(i)) and fin(MG[j].get(i)))
        dm = [abs(DUPG[j][i] - MG[j][i]) for i in d40 if fin(DUPG[j].get(i)) and fin(MG[j].get(i))]
        cdup = sum(((int(DUPG[j][i] < 0) == int(DUPV[j][i] == 1) and DUPV[j][i] != -1) != cert_c(j, i)) for i in d40 if fin(DUPG[j].get(i)))
        flips_all.append(fv)
        T["duplicates"].append(dict(reader=NAME[j], answers=len(d40), verdict_flips=fv, gut_flips=fg, median_abs_margin_change=float(np.median(dm)),
                                    max_abs_margin_change=float(max(dm)), agreement_flips=cdup))
    if flips_all:
        def dyn_dup(i):
            cj = [j for j in KEPT if fin(DUPG[j].get(i)) and DUPV[j].get(i, -1) != -1 and int(DUPG[j][i] < 0) == DUPV[j][i]]
            if not cj:
                vs = [int(DUPV[j].get(i) == 1) for j in KEPT]; return int(2 * sum(vs) > len(vs))
            vs = [DUPV[j][i] for j in cj]; a = sum(vs)
            if 2 * a != len(vs): return int(2 * a > len(vs))
            return DUPV[max(cj, key=lambda j: abs(DUPG[j][i]))][i]
        if not ADD_SG:   # with the safeguard juror, which has no repeat reads, the jury-level count is not meaningful
            T["duplicates"].append(dict(reader="agreement jury", answers=len(d40), verdict_flips=sum(dyn_dup(i) != POL["DYN-C"][i] for i in d40)))
            T["duplicates"].append(dict(reader="majority vote", answers=len(d40),
                                        verdict_flips=sum(int(2 * sum(int(DUPV[j].get(i) == 1) for j in KEPT) > len(KEPT)) != FULL[i] for i in d40)))

    # examinees: pass rates and rankings by rule against the label
    from scipy.stats import kendalltau
    EXs = sorted({EXAMINEE[i] for i in IDS if EXAMINEE[i]})

    def exam_stats(Vd, ids):
        g, e = [], []
        for ex in EXs:
            x = [i for i in ids if EXAMINEE[i] == ex]
            if x: g.append(np.mean([G[i] for i in x])); e.append(np.mean([Vd[i] for i in x]))
        g, e = np.array(g), np.array(e); return np.mean(np.abs(e - g)), kendalltau(g, e)[0], e - g

    def turn_mae(Vd, ids):
        byt = collections.defaultdict(list)
        for i in ids: byt[turn_of(i)].append(i)
        return np.mean([abs(np.mean([Vd[i] for i in x]) - np.mean([G[i] for i in x])) for x in byt.values()])
    rule_of = {"DYN-C": "agreement jury", "DYN-SS": "self-solve jury", f"FULL{n}": "majority vote", BEST1: best_name}
    for ids, set_name in ((BFF, "finance"), (CMT, "mt_bench"), (IDS, "all")):
        for pn in ("DYN-C", "DYN-SS", f"FULL{n}", BEST1):
            mae, tau, dev = exam_stats(POL[pn], ids)
            T["examinee_ranking"].append(dict(jurors=n, answer_set=set_name, rule=rule_of[pn], pass_rate_mae=mae, kendall_tau=tau,
                                              turn_pass_rate_mae=turn_mae(POL[pn], ids)))
            for ex, d in zip(EXs, dev):
                x = [i for i in ids if EXAMINEE[i] == ex]
                T["examinee_pass_rates"].append(dict(jurors=n, answer_set=set_name, rule=rule_of[pn], examinee=ex, answers=len(x),
                                                     pass_rate_label=np.mean([G[i] for i in x]), pass_rate=np.mean([POL[pn][i] for i in x]), difference=d,
                                                     false_reject=np.mean([1 - POL[pn][i] for i in x if G[i] == 1])))
            x = [i for i in ids if EXAMINEE[i] not in (None, "gemma-2-2b")]
            T["examinee_pass_rates"].append(dict(jurors=n, answer_set=set_name, rule=rule_of[pn], examinee="all but gemma-2-2b", answers=len(x),
                                                 pass_rate_label=np.mean([G[i] for i in x]), pass_rate=np.mean([POL[pn][i] for i in x]),
                                                 difference=np.mean([POL[pn][i] for i in x]) - np.mean([G[i] for i in x]),
                                                 false_reject=np.mean([1 - POL[pn][i] for i in x if G[i] == 1])))

    KEY["headline"] = {nm: [[c[0][0], c[0][1], c[0][2], c[1], c[2]] for c in cells] for nm, cells in TAB.items()}
    # per answer and per read, for the notebook and the figures
    for i in IDS:
        T["answer_verdicts"].append(dict(item_id=i, jurors=n, jurors_agreeing=NC_C[i], jurors_agreeing_list=" ".join(NAME[j] for j in KEPT if cert_c(j, i)),
                                         jurors_solved=NC_S[i], agreement_jury=POL["DYN-C"][i], self_solve_jury=POL["DYN-SS"][i], majority_vote=FULL[i],
                                         gut_majority_vote=POL[f"GUT{n} majority"][i], best_single_judge=POL[BEST1][i], best_single_judge_held_out=LOQO[i],
                                         own_answer_reference=FSYN[i]))
        for j in KEPT:
            T["reads"].append(dict(item_id=i, juror=NAME[j], gut_margin=MG[j].get(i, np.nan), gut_verdict=gutv(j, i), reasoned_verdict=V[j].get(i, -1),
                                   reasoned_finish=FIN[j].get(i, ""), agrees_with_itself=int(cert_c(j, i)),
                                   self_solve_status=ST.get((j, turn_of(i)), "") if j != SAFEGUARD else "",
                                   own_answer_reference_margin=SR[j].get(i, np.nan), repeat_gut_margin=DUPG[j].get(i, np.nan),
                                   repeat_reasoned_verdict=DUPV[j].get(i, np.nan)))
    return dict(key=KEY, tables=T, best=BEST1)


def _rule_name(code: str) -> tuple[str, str]:
    """(rule, juror) in plain words for a policy name of the original script."""
    if code.endswith(" reasoned") or code.endswith(" gut"):
        j, mode = code.rsplit(" ", 1); return f"{mode} read", NAME[j]
    if code.startswith("FULL") and "tie->best" in code:
        return f"majority vote, a tie goes to {NAME[code.split('(')[1].rstrip(')')]}", ""
    if code.startswith("FULL"): return "majority vote", ""
    if code.startswith("GUT"): return "gut majority vote", ""
    return {"DYN-C": "agreement jury", "DYN-SS": "self-solve jury",
            "DYN-C literal (unparsed=reject certifies)": "agreement jury, a missing verdict counts as a reject"}[code], ""


def _decisions(T, n, J1, J2s, J2f, cw, ssw, djw, best_name):
    T["decisions"].append(dict(decision="rule 1: agreement jury against self-solve jury", jurors=n,
                               outcome="agreement jury wins" if cw else "self-solve jury wins" if ssw else "tie",
                               reads=f"agreement jury minus self-solve jury {J1[0]:+.3f} [{J1[1]:+.3f}, {J1[2]:+.3f}]",
                               needs="agreement jury wins: difference >= +0.04 with lower bound above 0. self-solve jury wins: difference <= -0.04 "
                                     "with upper bound below 0. Otherwise a tie."))
    T["decisions"].append(dict(decision="rule 2: the jury wins", jurors=n, outcome="met" if djw else "not met",
                               reads=f"agreement jury minus {best_name} {J2s[0]:+.3f} [{J2s[1]:+.3f}, {J2s[2]:+.3f}], "
                                     f"minus majority vote {J2f[0]:+.3f} [{J2f[1]:+.3f}, {J2f[2]:+.3f}]",
                               needs="agreement jury minus best single judge >= +0.03 with lower bound above 0, and agreement jury minus majority vote >= 0"))


# ── results/ ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _fmt(v):
    """CSV text of one value: floats at full precision (shortest exact form), so any later rounding is the exact rounding."""
    if v is None: return ""
    if isinstance(v, (bool, np.bool_)): return str(bool(v))
    if isinstance(v, (int, np.integer)): return str(int(v))
    if isinstance(v, (float, np.floating)):
        if not np.isfinite(v): return ""
        return repr(float(v) + 0.0)
    return str(v)


def _write_csv(path: Path, rows: list[dict]):
    cols = []
    for r in rows:
        cols += [c for c in r if c not in cols]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n"); w.writerow(cols)
        for r in rows: w.writerow([_fmt(r.get(c)) for c in cols])


def tables() -> dict:
    """Every results/ table as a list of rows (plain names), from the four-juror run, the five-juror run and the screening."""
    A, S = _analysis(False), _analysis(True); TA, TS = A["tables"], S["tables"]; X = _ctx(); sd = screening()
    out = {}
    av = {r["item_id"]: r for r in TA["answer_verdicts"]}
    out["answers"] = [dict(item_id=i, answer_set=SETS[X["DS"][i]], question_id=X["QID"][i], turn=X["items"][i]["turn"], order=k,
                           examinee=X["EXAMINEE"][i], label_correct=X["GOLD"][i], expert_votes=X["PAT"][i], experts_split=X["DISSENT"][i],
                           **{c: v for c, v in av[i].items() if c not in ("item_id", "jurors")}) for k, i in enumerate(X["order"], 1)]
    out["answer_sets"] = [dict(r, answer_key_turns=_answer_key_turns(r["answer_set"])) for r in TA["answer_sets"]]
    g1 = sd["grader_check"]; out["grader_check"] = []
    for g in GRADERS:
        rr = _jsonl(RUNS / f"checks/grader__{NAME[g]}.jsonl")
        out["grader_check"].append(dict(grader=NAME[g], answers=len(rr), kappa=g1["kappa"][g], kappa_with_verdict=g1["kappa_parsed"][g],
                                        no_verdict=g1["unparsed"][g], label_correct=sum(r["gold"] == 1 for r in rr),
                                        label_correct_rejected=sum(r["gold"] == 1 and r["v"] != 1 for r in rr), token_limit=TOKEN_LIMIT[g],
                                        chosen=g == g1["chosen"], passes=g1["kappa"][g] >= 0.80))
    g2 = sd["juror_check"]
    out["juror_check"] = [dict(juror=NAME[s], answers=len(_jsonl(RUNS / f"checks/juror__{NAME[s]}__gut.jsonl")), gut_auroc=m["gut_auroc"], verdict_rate=m["parse_rate"], gut_margin_missing_rate=m["nan_rate"],
                               token_limit_rate=m["length_rate"], token_limit=TOKEN_LIMIT[s], kept=m["passed"]) for s, m in g2["metrics"].items()]
    out["juror_reads"] = TA["juror_reads"] + [r for r in TS["juror_reads"] if r["juror"] == NAME[SAFEGUARD]]
    out["self_solve"] = TA["self_solve"]
    out["results_by_rule"] = TA["results_by_rule"] + TS["results_by_rule"][: 3 * len(S["key"]["headline"])]
    out["results_parsed_only"] = TA["results_parsed_only"] + TS["results_parsed_only"]
    out["contrasts"] = TA["contrasts"] + [r for r in TS["contrasts"] if r["jurors"] == 5]
    out["decisions"] = TA["decisions"] + [r for r in TS["decisions"] if r["jurors"] == 5 and r["decision"].startswith("rule")]
    out["coverage"] = TA["coverage"] + [r for r in TS["coverage"] if r["jurors"] == 5 and r["measure"] in (
        "answers where no juror agrees with itself", "share of answers where no juror agrees with itself")]
    for k in ("uncovered_fallbacks", "kappa_by_juror_count", "error_rankers", "latent_solver", "own_answer_index", "matched_coverage",
              "duplicates", "examinee_ranking", "examinee_pass_rates", "reads"):
        out[k] = TA[k]
    out["reads"] = TA["reads"] + [r for r in TS["reads"] if r["juror"] == NAME[SAFEGUARD]]
    return out


def _answer_key_turns(set_name: str) -> int:
    """Question turns with a hand-written final-answer key (MT-Bench only; the grader's 'exact' field is None on the others)."""
    g5 = _jsonl(RUNS / "self_solve/grades__qwen3.5-397b.jsonl"); keyed = collections.defaultdict(bool)
    for r in g5:
        keyed[(r["ds"], r["turn"])] |= r["exact"] is not None
    return sum(v for (ds, t), v in keyed.items() if set_name == "all" or SETS[ds] == set_name)


def hand_check_sample() -> str:
    """A blank sheet of 20 self-solve grades for a person to check by hand (fixed seeded sample of the solved and unsolved calls)."""
    X = _ctx(); turns_ = X["turns"]
    rows = _jsonl(RUNS / "self_solve/grades__qwen3.5-397b.jsonl")
    own = {}
    for s in JURORS:
        for t in (1, 2):
            for r in _jsonl(RUNS / f"self_solve/{NAME[s]}__turn{t}.jsonl"): own[(r["juror"], r["turn"])] = r["own"]
    grader = NAME[screening_decisions()["grader_check"]["chosen"]]
    pool = [r for r in rows if r["has_own"] and r["status"] in ("solved", "unsolved")]
    byk = {f"{r['juror']}|{r['turn']}": r for r in pool}; pick = [byk[x] for x in seeded_order(sorted(byk), SALT_HAND_CHECK)[:20]]
    out = ["# Hand check of the self-solve grades", "",
           f"20 of the jurors' own answers, solved or unsolved, in a fixed seeded order. The grader is {grader} ({MODELS[SHORT[grader]][1]}). "
           "For each answer: the final user question, the expert reference, the juror's own answer and the grader's call. "
           "Mark each call right or wrong. The run did not wait for this check.", ""]
    verdict = {1: "correct", 0: "incorrect", -1: "no verdict", None: "no call"}; key = {1: "found", 0: "not found", None: "none"}
    for n, r in enumerate(pick, 1):
        tr = turns_[r["turn"]]; q, t = r["turn"].split("|")
        out += [f"## {n}. {NAME[r['juror']]} on question {q}, turn {t[1:]} ({'finance' if r['ds'] == 'BFF' else 'MT-Bench'}): **{r['status']}** "
                f"(grader: {verdict[r['v']]}, answer key: {key[r['exact']]})", "",
                "**Question (final user turn):**", "", "> " + tr["users"][-1][:1500].replace("\n", "\n> "), "",
                "**Reference:**", "", "> " + tr["ref"][:1500].replace("\n", "\n> "), "",
                "**Own answer:**", "", "> " + (own[(r["juror"], r["turn"])] or "")[:2000].replace("\n", "\n> "), "",
                "**Grader call (final part):**", "", "> " + (r["final"] or r["text"][-800:])[:1200].replace("\n", "\n> "), "", "Hand verdict: ____", ""]
    return "\n".join(out)


# Where each file of results/ goes. The main tables sit at the top of results/, the supporting checks in checks/ and the
# one-row-per-answer tables in per_answer/. A name not listed here goes to the top.
RESULT_FOLDERS = {"answer_sets": "checks", "grader_check": "checks", "juror_check": "checks", "juror_reads": "checks",
                  "self_solve": "checks", "duplicates": "checks", "results_parsed_only": "checks",
                  "examinee_ranking": "checks", "examinee_pass_rates": "checks",
                  "hand_check_sample": "checks", "answers": "per_answer", "reads": "per_answer"}


def write_results(out: Path | str = RESULTS) -> list[Path]:
    """Write every results/ CSV and hand_check_sample.md, in the folders of RESULT_FOLDERS under out. Returns the paths written."""
    out = Path(out); written = []
    for name, rows in tables().items():
        p = out / RESULT_FOLDERS.get(name, "") / f"{name}.csv"; p.parent.mkdir(parents=True, exist_ok=True); _write_csv(p, rows); written.append(p)
    p = out / RESULT_FOLDERS["hand_check_sample"] / "hand_check_sample.md"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(hand_check_sample()); written.append(p)
    return written
