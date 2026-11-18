"""Every number the paper quotes, from out_paper/results.json, authorship.json and out_allpairs/*.json.

  python3 experiments/beyond_capability/paper_tables.py -> papers/judge_direction/numbers.tex, tab_*.tex
In the text: \\R{key}, e.g. \\R{sm.math.qwen.direct.rank} = pooled ranking gain of the direction over the verdict.
"""
import json
from collections import defaultdict

import numpy as np

import allpairs_analyze as A
from paper_data import BIG

P = A.HERE.parents[1] / "papers" / "judge_direction"
R = json.load(open(A.HERE / "out_paper" / "results.json"))
AU = json.load(open(A.HERE / "out_paper" / "authorship.json"))
AP = json.load(open(A.D / "allpairs.json"))
SPL = {(r["judge"], r["bench"]): r for r in json.load(open(A.D / "knows_splits.json"))}
for _f in A.D.glob("*/splits_*.json"):  # pairs run on Cannon (direct_local.py)
    _j, _b = _f.parent.name.rsplit("_", 1)
    SPL[(_j, _b)] = dict(json.load(open(_f)), judge=_j, bench=_b)
NAME = dict(A.NAME)
BN = {"mmlu": "MMLU-Redux", "math": "MATH", "bbeh": "BBEH"}
WHO = {"qwen3.5-4b": "qwen", "olmo2-7b": "olmo", "qwen3.5-4b strict": "strict"}
WHON = {"qwen3.5-4b": "Qwen3.5-4B", "olmo2-7b": "OLMo-2-7B"}
WHOB = lambda b, who: "4 pool models" if b == "bbeh" else WHON[who]  # noqa: E731  (BBEH same-model sets)
MS = ["cot", "x4", "x11", "direct", "sum", "cot_sum"]
num = {}


def g(x, sign=True, ci=False):
    if not x:
        return "--"
    s = f"{x['g']:+.1f}" if sign else f"{x['g']:.1f}"
    s = s.replace("-", "$-$") if s.startswith("-") else s
    if ci:
        s += f" [{x['lo']:+.1f}, {x['hi']:+.1f}]".replace("-", "$-$")
    return s


def bold(x, s):
    return f"\\textbf{{{s}}}" if x and (x["lo"] > 0) else s


def put(k, v):
    num[k] = v


def numbers():
    S = R["summary"]
    for key, s in S.items():
        part, *rest = key.split("|")
        tag = part if rest == ["all"] else f"{part}.{rest[0]}.{WHO[rest[1]]}"
        put(f"{tag}.k", str(s["k"]))
        put(f"{tag}.verdict.rank", f"{s['verdict_rank_mean']:.1f}")
        put(f"{tag}.verdict.bon", f"{s['verdict_bon_mean']:.1f}")
        put(f"{tag}.random.bon", f"{s['random_bon_mean']:.1f}")
        for m in MS:
            for met in ("rank", "bon"):
                x = s.get(m, {}).get(met) if s.get(m) else None
                put(f"{tag}.{m}.{met}", g(x))
                put(f"{tag}.{m}.{met}.ci", g(x, ci=True))
    x = R["sm"].get("llama3.1-8b|math|qwen3.5-4b strict")
    if x:
        put("strict.nq", str(x["nq"]))
        put("strict.verdict.rank", f"{x['verdict']['rank']:.1f}")
        for m in MS:
            if m in x:
                put(f"strict.{m}.rank", g(x[m]["d_rank"]))
                put(f"strict.{m}.rank.ci", g(x[m]["d_rank"], ci=True))
    # gaps and pools
    small = lambda k: k.split("|")[0] not in BIG  # noqa: E731
    pool = {k: v for k, v in R["pool"].items() if small(k)}
    d = [AP[k]["gap"] for k in pool]  # best layer's direction minus verdict, on the pair's split
    put("pool.npairs", str(len(pool)))
    put("gap.lo", f"{min(d):.1f}"), put("gap.hi", f"{max(d):.1f}")
    nall = sum(1 for k, o in AP.items() if not k.startswith("extra") and "gap" in o and small(k))
    put("pairs.all", str(nall))
    sds = [100 * r["knows_sd"] for (j, _), r in SPL.items() if j not in BIG]
    put("split.sd.lo", f"{min(sds):.1f}"), put("split.sd.hi", f"{max(sds):.1f}")
    au = {k: v for k, v in AU.items() if not k.endswith("bbeh") and small(k)}
    put("auth.dir.lo", f"{100 * min(v['direct'] for v in au.values()):.0f}")
    put("auth.dir.hi", f"{100 * max(v['direct'] for v in au.values()):.0f}")
    put("auth.ver.lo", f"{100 * min(v['verdict'] for v in au.values()):.0f}")
    put("auth.ver.hi", f"{100 * max(v['verdict'] for v in au.values()):.0f}")
    put("auth.dir.med", f"{100 * np.median([v['direct'] for v in au.values()]):.0f}")
    # responding = the revised rule (verdict-score sensitivity >= 0.05 at the stretched layer), for every pair
    st = [k for k, o in AP.items() if not k.startswith(("extra", "sweep")) and "layer" in o and small(k)]
    resp = [k for k in st if AP[k].get("sensitivity", 0) >= 0.05]
    nores = [k for k in st if k not in resp]
    sig = lambda ks: [k for k in ks if (AP[k].get("all | x11") or {"lo": -1})["lo"] > 0]  # noqa: E731
    put("pairs.stretched", str(len(st)))
    put("pairs.respond", str(len(resp))), put("pairs.respond.sig", str(len(sig(resp))))
    put("pairs.norespond", str(len(nores))), put("pairs.norespond.sig", str(len(sig(nores))))
    toks = []
    for f in sorted(A.D.glob("*/cot_main.jsonl")):
        if f.parent.name.rsplit("_", 1)[0] not in BIG:
            toks += [json.loads(l)["n_reason"] for l in open(f)]
    if toks:
        put("cot.tok.median", f"{np.median(toks):.0f}")
        reached = [json.loads(l)["reached"] for f in A.D.glob("*/cot_*.jsonl") for l in open(f)
                   if f.parent.name.rsplit("_", 1)[0] not in BIG]
        put("cot.reached", f"{100 * np.mean(reached):.1f}")
    big_numbers()
    lines = ["% generated by paper_tables.py", "\\newcommand{\\R}[1]{\\ifcsname r@#1\\endcsname\\csname r@#1\\endcsname\\else\\textbf{??}\\fi}"]
    lines += [f"\\expandafter\\def\\csname r@{k}\\endcsname{{{v}}}" for k, v in sorted(num.items())]
    (P / "numbers.tex").write_text("\n".join(lines) + "\n")


POOLQ = {b: {json.loads(l)["qid"] for l in open(A.D / f"llama3.1-70b_{b}" / f"meta_{b}.jsonl")} for b in BN}


def solve_rate(j, b):
    """share of the main pool's questions the judge solves (its own single answer)."""
    lab = A.labels(j, b)
    v = [lab[q] for q in POOLQ[b] if q in lab]
    return 100 * np.mean(v) if v else None


def chance_numbers():
    """per same-model set: judges whose verdict ranking is significantly above / below chance (question resamples)."""
    for k_b in ("math", "bbeh", "mmlu"):
        for who in ("qwen3.5-4b", "olmo2-7b"):
            xs = [v for k, v in R["sm"].items() if k.split("|")[1:] == [k_b, who] and k.split("|")[0] not in BIG]
            if not xs:
                continue
            t = f"chance.{k_b}.{WHO[who]}"
            put(f"{t}.n", str(len(xs)))
            put(f"{t}.above", str(sum(x["verdict"]["rank_ci"]["lo"] > 50 for x in xs)))
            put(f"{t}.below", str(sum(x["verdict"]["rank_ci"]["hi"] < 50 for x in xs)))


def auth_numbers():
    """where the direction's advantage comes from (paper_authorship.py) and the authorship directions
    (authorship_dir_modal.py)."""
    C = json.load(open(A.HERE / "out_paper" / "authorship_check.json"))
    for name in ("same", "diff"):
        x = C["pooled"][f"{name}_gap"]
        put(f"auth.{name}.ci", g(x, ci=True)), put(f"auth.{name}", g(x)), put(f"auth.{name}.k", str(x["k"]))
        gs = [v["split"][name] for v in C["pairs"].values() if name in v["split"]]
        put(f"auth.{name}.lo", g(min((x["gap"] for x in gs), key=lambda z: z["g"])))
        put(f"auth.{name}.hi", g(max((x["gap"] for x in gs), key=lambda z: z["g"])))
        put(f"auth.{name}.sig", str(sum(x["gap"]["lo"] > 0 for x in gs)))
        put(f"auth.{name}.verdict", f"{np.mean([x['verdict'] for x in gs]):.1f}")
        put(f"auth.{name}.direct", f"{np.mean([x['direct'] for x in gs]):.1f}")
    for key, tag in (("src_direct", "dir"), ("src_verdict", "ver")):
        xs = [v[key] for v in C["pairs"].values() if key in v]
        put(f"src.{tag}.n", str(len(xs)))
        put(f"src.{tag}.lo", f"{min(x['g'] for x in xs):.0f}"), put(f"src.{tag}.hi", f"{max(x['g'] for x in xs):.0f}")
        put(f"src.{tag}.above", str(sum(x["lo"] > 50 for x in xs))), put(f"src.{tag}.below", str(sum(x["hi"] < 50 for x in xs)))
    x = C["pooled"]["diff_gap_matched"]
    put("auth.diffm.ci", g(x, ci=True)), put("auth.diffm.k", str(x["k"]))
    sh = [v["shares"] for v in C["pairs"].values() if "shares" in v]
    for k in ("null", "gold", "verdict", "direct"):
        put(f"share.{k}.lo", f"{100 * min(x[k] for x in sh):.0f}"), put(f"share.{k}.hi", f"{100 * max(x[k] for x in sh):.0f}")
    D = json.load(open(A.HERE / "out_paper" / "authorship_dir.json"))
    for b in ("mmlu", "math"):
        xs = [r[b] for r in D.values() if b in r]
        t = f"adir.{b}"
        put(f"{t}.n", str(len(xs)))
        for k, f in (("auth", lambda x: x["auth_auc"]), ("xfer", lambda x: x["pair_transfer"]),
                     ("cos", lambda x: x["cos"]["c_atop"]), ("cosaa", lambda x: x["cos"]["atop_amid"])):
            v = [f(x) for x in xs]
            fmt = (lambda z: f"{z:+.2f}".replace("-", "$-$")) if k.startswith("cos") else (lambda z: f"{z:.0f}")
            put(f"{t}.{k}.lo", fmt(min(v))), put(f"{t}.{k}.hi", fmt(max(v)))
        rem = [(x["rank"]["c"]["all"] - x["rank"]["c_perp"]["all"]) / (x["rank"]["c"]["all"] - x["rank"]["verdict"]["all"])
               for x in xs]
        put(f"{t}.removed.lo", f"{100 * min(rem):.0f}"), put(f"{t}.removed.hi", f"{100 * max(rem):.0f}")
        put(f"{t}.removed.mean", f"{100 * np.mean(rem):.0f}"), put(f"{t}.removed.half", str(sum(r > 0.5 for r in rem)))
        ac = [abs(x["cos"]["c_atop"]) for x in xs]
        put(f"{t}.abscos.hi", f"{max(ac):.2f}")
        for m, mk in (("verdict", "verdict"), ("c", "dir"), ("c_perp", "perp")):
            for part in ("all", "same", "diff"):
                put(f"{t}.{mk}.{part}", f"{np.mean([x['rank'][m][part] for x in xs]):.1f}")
    cr = [r["cross"] for r in D.values() if "cross" in r]
    put("adir.cross.n", str(len(cr)))
    for k, f in (("cos", lambda c: c["cos_a"]), ("m2t", lambda c: c["a_mmlu_on_math"]), ("t2m", lambda c: c["a_math_on_mmlu"])):
        v = [f(c) for c in cr]
        fmt = (lambda z: f"{z:.2f}") if k == "cos" else (lambda z: f"{z:.0f}")
        put(f"adir.cross.{k}.lo", fmt(min(v))), put(f"adir.cross.{k}.hi", fmt(max(v)))


def tab_auth():
    """appendix: authorship directions per judge and benchmark."""
    D = json.load(open(A.HERE / "out_paper" / "authorship_dir.json"))
    rows = []
    for b in ("mmlu", "math"):
        for j in A.JUDGES:
            x = D.get(j, {}).get(b)
            if not x:
                continue
            rk = x["rank"]
            cells = [f"{x['layer']}", f"{x['auth_auc']:.1f}", f"{x['pair_transfer']:.1f}", f"{x['cos']['c_atop']:+.2f}",
                     f"{rk['verdict']['all']:.1f}", f"{rk['c']['all']:.1f}", f"{rk['c_perp']['all']:.1f}",
                     f"{rk['c']['same']:.1f}", f"{rk['c_perp']['same']:.1f}"]
            rows.append(f"{BN[b]} & {NAME[j]} & " + " & ".join(c.replace("-", "$-$") for c in cells) + " \\\\")
        rows.append("\\midrule")
    rows = rows[:-1]
    t = ["\\begin{tabular}{ll r rr r rrr rr}", "\\toprule",
         "& & & \\multicolumn{2}{c}{Authorship dir.} & & \\multicolumn{3}{c}{Ranking, all pairs} & \\multicolumn{2}{c}{Same-model pairs} \\\\",
         "\\cmidrule(lr){4-5}\\cmidrule(lr){7-9}\\cmidrule(l){10-11}",
         "Bench & Judge & Layer & Own pair & Other pair & cos & Verdict & Dir. & Dir.$\\perp$ & Dir. & Dir.$\\perp$ \\\\", "\\midrule"]
    t += rows + ["\\bottomrule", "\\end{tabular}"]
    (P / "tab_auth.tex").write_text("\n".join(t) + "\n")


def big_numbers():
    """the scale check (Llama-3.1-70B), keyed big.<bench>.*, next to the Llama judges it is compared with."""
    for j in sorted(BIG):
        for b in ("mmlu", "math", "bbeh"):
            sp, o = SPL.get((j, b)), AP.get(f"{j}|{b}", {})
            t = f"big.{b}"
            if sp:
                put(f"{t}.says", f"{100 * sp['says']:.1f}")
                put(f"{t}.knows", f"{100 * sp['knows_mean']:.1f}")
                put(f"{t}.gap", f"{100 * (sp['knows_mean'] - sp['says']):+.1f}")
            if "gap" in o:
                put(f"{t}.gap0", f"{o['gap']:+.1f}")
            put(f"{t}.solved", f"{solve_rate(j, b):.0f}")
            v = R["pool"].get(f"{j}|{b}")
            if v:
                for m in MS:
                    if m in v:
                        put(f"{t}.pool.{m}.rank.ci", g(v[m]["d_rank"], ci=True))
            au = AU.get(f"{j}|{b}")
            if au:
                put(f"{t}.auth.dir", f"{100 * au['direct']:.0f}"), put(f"{t}.auth.ver", f"{100 * au['verdict']:.0f}")
            for who in ("qwen3.5-4b", "olmo2-7b"):
                x = R["sm"].get(f"{j}|{b}|{who}")
                if not x:
                    continue
                w = f"{t}.sm.{WHO[who]}"
                put(f"{w}.nq", str(x["nq"]))
                put(f"{w}.verdict.rank", f"{x['verdict']['rank']:.1f}")
                for m in MS:
                    if m in x:
                        put(f"{w}.{m}.rank.ci", g(x[m]["d_rank"], ci=True))
                        put(f"{w}.{m}.rank.abs", f"{x[m]['rank']:.1f}")


def tab_scale():
    """Llama judges by size: verdict and direction on the main pools, and the verdict on same-model MATH pairs."""
    rows = []
    for j in ("llama3.2-1b", "llama3.2-3b", "llama3.1-8b", "llama3.1-70b"):
        cells = []
        for b in ("mmlu", "math", "bbeh"):
            o = AP.get(f"{j}|{b}", {})
            sr = solve_rate(j, b)
            cells += [f"{sr:.0f}" if sr is not None else "--"]
            pv = R["pool"].get(f"{j}|{b}")
            says = pv["verdict"]["rank"] if pv else 100 * o["says"] if "gap" in o else None
            cells += [f"{says:.1f}", f"{o['gap']:+.1f}"] if "gap" in o else ["--", "--"]
            sj = j.split("-")[1]  # 1b, 3b, 8b, 70b
            if sr is not None:
                put(f"scale.{sj}.{b}.solved", f"{sr:.0f}")
            if "gap" in o:
                put(f"scale.{sj}.{b}.says", f"{says:.1f}"), put(f"scale.{sj}.{b}.gap", f"{o['gap']:+.1f}")
        for b in ("math", "mmlu"):
            x = R["sm"].get(f"{j}|{b}|qwen3.5-4b")
            cells.append(f"{x['verdict']['rank']:.1f}" if x else "--")
            if x:
                put(f"scale.{j.split('-')[1]}.sm.{b}", f"{x['verdict']['rank']:.1f}")
        rows.append(f"{NAME[j]} & " + " & ".join(c if c == "--" else c.replace("-", "$-$") for c in cells) + " \\\\")
    t = ["\\begin{tabular}{l rrr rrr rrr rr}", "\\toprule",
         "& \\multicolumn{3}{c}{MMLU-Redux} & \\multicolumn{3}{c}{MATH} & \\multicolumn{3}{c}{BBEH} & \\multicolumn{2}{c}{Same model} \\\\",
         "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\\cmidrule(lr){8-10}\\cmidrule(l){11-12}",
         "Judge & Solves & Verdict & Gap & Solves & Verdict & Gap & Solves & Verdict & Gap & MATH & MMLU \\\\", "\\midrule"]
    t += rows + ["\\bottomrule", "\\end{tabular}"]
    (P / "tab_scale.tex").write_text("\n".join(t) + "\n")


def tab_sm():
    """main table: same-model pairs on questions the judge cannot solve."""
    S = R["summary"]
    rows = []
    for b in ("math", "bbeh", "mmlu"):
        for who in ("qwen3.5-4b", "olmo2-7b"):
            s = S.get(f"sm|{b}|{who}")
            if not s:
                continue
            cells = [bold(s[m]["rank"], g(s[m]["rank"])) if s.get(m) and s[m]["rank"] else "--"
                     for m in ("cot", "x11", "direct", "sum")]
            rows.append(f"{BN[b]} & {WHOB(b, who)} & {s['k']} & {s['verdict_rank_mean']:.1f} & " + " & ".join(cells) + " \\\\")
    x = R["sm"].get("llama3.1-8b|math|qwen3.5-4b strict")
    if x:
        cells = [bold(x[m]["d_rank"], g(x[m]["d_rank"])) if m in x else "--" for m in ("cot", "x11", "direct", "sum")]
        rows.append("\\midrule\nMATH, failed 9/9$^\\dagger$ & Qwen3.5-4B & 1 & " + f"{x['verdict']['rank']:.1f} & " + " & ".join(cells) + " \\\\")
    t = ["\\begin{tabular}{llr r rrrr}", "\\toprule",
         "& & & & \\multicolumn{4}{c}{Gain over the verdict} \\\\ \\cmidrule(l){5-8}",
         "Benchmark & Answers by & Judges & Verdict & Reason & Stretch & Direction & Verdict \\\\",
         "& & & & first & $\\times$11 & & + dir. \\\\", "\\midrule"] + rows + ["\\bottomrule", "\\end{tabular}"]
    (P / "tab_sm.tex").write_text("\n".join(t) + "\n")


def tab_readout():
    """full answer pool: ranking and best-of-n gains of every readout."""
    S = R["summary"]
    rows = []
    for key, lab in (("pool|all", "All questions"), ("pool_unsolved|all", "Judge cannot solve")):
        s = S[key]
        cells = []
        for m in ("cot", "x11", "direct", "sum"):
            for met in ("rank", "bon"):
                x = s.get(m, {}).get(met) if s.get(m) else None
                cells.append(bold(x, g(x)))
        rows.append(f"{lab} & {s['verdict_rank_mean']:.1f} / {s['verdict_bon_mean']:.1f} & " + " & ".join(cells) + " \\\\")
    t = ["\\begin{tabular}{l c rr rr rr rr}", "\\toprule",
         "& Verdict & \\multicolumn{2}{c}{Reason first} & \\multicolumn{2}{c}{Stretch $\\times$11} & "
         "\\multicolumn{2}{c}{Direction} & \\multicolumn{2}{c}{Verdict + dir.} \\\\",
         "\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\\cmidrule(lr){7-8}\\cmidrule(l){9-10}",
         "& Rank / BoN & Rank & BoN & Rank & BoN & Rank & BoN & Rank & BoN \\\\", "\\midrule"] + rows + ["\\bottomrule", "\\end{tabular}"]
    (P / "tab_readout.tex").write_text("\n".join(t) + "\n")


def tab_pairs():
    """appendix: every judge x benchmark."""
    rows, prev = [], None
    for b in ("mmlu", "math", "bbeh"):
        for j in A.JUDGES:
            o = AP.get(f"{j}|{b}", {})
            if "gap" not in o:
                continue
            sp = SPL.get((j, b))
            gm = f"{100 * (sp['knows_mean'] - sp['says']):+.1f} $\\pm$ {100 * sp['knows_sd']:.1f}" if sp else "--"
            if prev and prev != b:
                rows.append("\\midrule")
            prev = b
            if "layer" not in o:
                rows.append(f"{BN[b]} & {NAME[j]} & {o['gap']:+.1f} & {gm} & \\multicolumn{{6}}{{l}}{{gap $\\le$ 5: not stretched}} \\\\")
                continue
            v = R["pool"][f"{j}|{b}"]
            au = AU.get(f"{j}|{b}", {}).get("direct")
            st = "" if o.get("sensitivity", 0) >= 0.05 else "$^*$"
            c = lambda m: f"{v[m]['rank']:.1f}" if m in v else "--"  # noqa: E731
            rows.append(f"{BN[b]} & {NAME[j]} & {o['gap']:+.1f} & {gm} & {o['layer']}{st} & {o.get('sensitivity', float('nan')):.2f} & "
                        f"{c('verdict')} & {c('cot')} & {c('x11')} & {c('direct')} \\\\")
    t = ["\\begin{tabular}{ll rr rr rrrr}", "\\toprule",
         "Bench & Judge & Gap & Gap, 20 splits & Layer & Sens. & Verdict & Reason & Stretch & Direction \\\\", "\\midrule"]
    t += [r.replace("-", "$-$") if r.startswith("x") else r for r in rows] + ["\\bottomrule", "\\end{tabular}"]
    (P / "tab_pairs.tex").write_text("\n".join(t) + "\n")


def tab_sm_pairs():
    """appendix: same-model sets per judge."""
    rows = []
    for k, v in sorted(R["sm"].items(), key=lambda kv: ({"math": 0, "bbeh": 1, "mmlu": 2}[kv[0].split("|")[1]], kv[0])):
        j, b, who = k.split("|")
        lab = "4 pool models" if b == "bbeh" else WHON.get(who, "Qwen3.5-4B, failed 9/9")
        c = lambda m: f"{v[m]['rank']:.1f}" if m in v else "--"  # noqa: E731
        rows.append(f"{BN[b]} & {NAME[j]} & {lab} & {v['nq']} & {c('verdict')} & {c('cot')} & {c('x4')} & {c('x11')} & {c('direct')} & {c('sum')} \\\\")
    t = ["\\begin{tabular}{lll r rrrrrr}", "\\toprule",
         "Bench & Judge & Answers by & Groups & Verdict & Reason & Str.\\,$\\times$4 & Str.\\,$\\times$11 & Direction & Verd.+dir. \\\\",
         "\\midrule"] + rows + ["\\bottomrule", "\\end{tabular}"]
    (P / "tab_sm_pairs.tex").write_text("\n".join(t) + "\n")


def tab_bon():
    S = R["summary"]
    order = [("pool|all", "All questions"), ("pool_unsolved|all", "Judge cannot solve")]
    for b in ("math", "bbeh", "mmlu"):
        for who in ("qwen3.5-4b", "olmo2-7b"):
            order.append((f"sm|{b}|{who}", f"Same model, {BN[b]}, {WHOB(b, who)}"))
    rows = []
    for key, lab in order:
        s = S.get(key)
        if not s:
            continue
        cells = [bold(s[m]["bon"], g(s[m]["bon"])) if s.get(m) and s[m]["bon"] else "--" for m in ("cot", "x11", "direct", "sum")]
        rows.append(f"{lab} & {s['k']} & {s['random_bon_mean']:.1f} & {s['verdict_bon_mean']:.1f} & " + " & ".join(cells) + " \\\\")
    t = ["\\begin{tabular}{lr rr rrrr}", "\\toprule",
         "Answers & Judges & Random & Verdict & Reason first & Stretch $\\times$11 & Direction & Verdict + dir. \\\\", "\\midrule"]
    t += rows + ["\\bottomrule", "\\end{tabular}"]
    (P / "tab_bon.tex").write_text("\n".join(t) + "\n")


if __name__ == "__main__":
    tab_bon()
    tab_scale()
    auth_numbers()
    chance_numbers()
    tab_auth()
    numbers()
    tab_sm()
    tab_readout()
    tab_pairs()
    tab_sm_pairs()
    print(len(num), "numbers ->", P)
