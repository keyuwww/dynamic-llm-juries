#!/usr/bin/env python3
"""
How similar are the judges' verdicts, where do their errors overlap, and how much room is there for a
judge router or a jury to recover the best judge's mistakes? Builds results/similarity_report.html (one tab per
benchmark plus an overview) and results/similarity_report.json from data/<bench>_decisions.pkl.

Room for recovery, per benchmark (8 Tinker judges, no reference answer):
  best judge         the single judge with the highest agreement with the gold label (hindsight)
  jury ceiling       the best possible rule that sees only the 8 verdicts: for every verdict pattern, answer with
                     the gold label most common under that pattern (in-sample, so an upper bound); the
                     cross-validated version learns the pattern table on training folds (unseen patterns fall back
                     to majority vote)
  router ceiling     pick the right judge for every item: correct whenever any judge is right
  decomposition      of the best judge's errors: a majority of the other judges is right (a vote can fix it), only
                     a minority is right (a router needs item-level information to find them), or no judge is right
                     (nothing inside the pool can fix it)
  achieved           the best cross-validated rule from analysis.json (top-k, threshold, majority)

  uv run python experiments/cross_benchmark/similarity_report.py
"""
import html
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
JUDGES = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
          "nemotron3-super-120b", "nemotron3-nano-30b"]
SHORT = {"gpt-oss-120b": "gpt-oss-120b", "gpt-oss-20b": "gpt-oss-20b", "deepseek-v3.1": "DeepSeek-V3.1",
         "qwen3.6-35b-a3b": "Qwen3.6-35B", "qwen3.5-9b": "Qwen3.5-9B", "qwen3.5-4b": "Qwen3.5-4B",
         "nemotron3-super-120b": "Nemotron-S-120B", "nemotron3-nano-30b": "Nemotron-N-30B"}
FAMILY = {"gpt-oss-120b": "gpt-oss", "gpt-oss-20b": "gpt-oss", "deepseek-v3.1": "DeepSeek", "qwen3.6-35b-a3b": "Qwen",
          "qwen3.5-9b": "Qwen", "qwen3.5-4b": "Qwen", "nemotron3-super-120b": "Nemotron", "nemotron3-nano-30b": "Nemotron"}
ORDER = ["bff", "mtb", "bffpair", "safety", "bbeh", "judgebench", "rb2", "alpacafarm", "mtbhuman"]
TITLE = {"bff": "BFF-Bench", "mtb": "(C)MT-Bench", "bffpair": "BFF pairwise", "safety": "RB2 Safety", "bbeh": "BBEH Mini",
         "judgebench": "JudgeBench", "rb2": "RB2 other", "alpacafarm": "AlpacaFarm", "mtbhuman": "MT-Bench human"}
FMT = {"bffpair": "pair", "judgebench": "pair", "alpacafarm": "pair", "mtbhuman": "pair"}


def kappa(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def phi(x, y):
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def load(bench):
    d = pd.read_pickle(HERE / "data" / f"{bench}_decisions.pkl")
    d = d[(d.condition == "none") & d.judge.isin(JUDGES)]
    cov = d.groupby("judge").key.nunique()
    pool = [j for j in JUDGES if j in cov and cov[j] >= 0.95 * cov.median()]
    V = d[d.judge.isin(pool)].pivot_table(index="key", columns="judge", values="verdict").dropna()[pool].astype(int)
    info = d.drop_duplicates("key").set_index("key").loc[V.index]
    return V, info.gold.astype(int).values, info.group.astype(str).values, pool


def pattern_jury(Vm, y, tr, te, min_n=3):
    """Learn verdict pattern -> most common gold label on tr; predict te (fallback: majority vote)."""
    keys = [tuple(r) for r in Vm]
    tab = {}
    for i in tr:
        c = tab.setdefault(keys[i], [0, 0])
        c[y[i]] += 1
    out = np.empty(len(te), int)
    for n, i in enumerate(te):
        c = tab.get(keys[i])
        if c and sum(c) >= min_n and c[0] != c[1]:
            out[n] = int(c[1] > c[0])
        else:
            out[n] = int(Vm[i].mean() > 0.5)
    return out


def position_bias(bench, pool, n_perm=20000):
    """Pairwise benchmarks only. Each pair is shown in both orders; for each judge and pair the two verdicts are
    consistent (same answer both times), 'first' both times, or 'second' both times. Unparsed verdicts are dropped.
    Per judge: exact binomial test of first vs second among the switching pairs (H0: order has no effect),
    Holm-corrected; pooled: sign-flip permutation test on (first - second) summed per conversation / prompt group."""
    from scipy.stats import binomtest
    d = pd.read_pickle(HERE / "data" / f"{bench}_decisions.pkl")
    d = d[(d.condition == "none") & d.judge.isin(pool) & (d.parsed == 1)]
    w = d.pivot_table(index=["pair_id", "judge"], columns="order", values="verdict").dropna().reset_index()
    if w.empty or 0 not in w.columns or 1 not in w.columns:
        return None
    g0 = d[d.order == 0].drop_duplicates(["pair_id", "judge"]).set_index(["pair_id", "judge"])
    w["gold0"] = [g0.gold.get((p, j)) for p, j in zip(w.pair_id, w.judge)]
    w["group"] = [g0.group.get((p, j)) for p, j in zip(w.pair_id, w.judge)]
    w["first"] = (w[0] == 1) & (w[1] == 1)
    w["second"] = (w[0] == 0) & (w[1] == 0)
    w["switch"] = w["first"] | w["second"]
    w["errors"] = (w[0] != w.gold0).astype(int) + (w[1] != (1 - w.gold0)).astype(int)
    rows, ps = [], []
    for j in pool:
        x = w[w.judge == j]
        if not len(x):
            continue
        F, S = int(x["first"].sum()), int(x["second"].sum())
        p = binomtest(F, F + S, 0.5).pvalue if F + S else 1.0
        err = int(x.errors.sum())
        rows.append(dict(judge=j, n=int(len(x)), consistent=float(1 - x.switch.mean()), first=F / len(x), second=S / len(x),
                         F=F, S=S, p=float(p), err_from_switch=float((x.errors * x.switch).sum() / err) if err else 0.0))
        ps.append(p)
    order = np.argsort(ps)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        rows[i]["holm"] = float(run)
    D = (w["first"].astype(int) - w["second"].astype(int)).groupby(w.group).sum().values
    T = D.sum()
    rng = np.random.default_rng(0)
    sims = np.abs((rng.choice([-1, 1], size=(n_perm, len(D))) * D).sum(1))
    return dict(rows=rows, pooled_first=int(w["first"].sum()), pooled_second=int(w["second"].sum()),
                pooled_p=float((np.sum(sims >= abs(T)) + 1) / (n_perm + 1)), groups=int(len(D)),
                pooled_consistent=float(1 - w.switch.mean()))


def analyse(bench):
    V, y, groups, pool = load(bench)
    Vm = V.values
    A = (Vm == y[:, None]).astype(int)
    E = 1 - A
    J = len(pool)
    acc = A.mean(0)
    best = int(np.argmax(acc))
    # similarity matrices
    agree = np.eye(J)
    kap = np.eye(J)
    ephi = np.eye(J)
    cond = np.zeros((J, J))       # P(col wrong | row wrong)
    rescue = np.zeros((J, J))     # share of row's errors that col gets right
    for i in range(J):
        for j in range(J):
            if i == j:
                continue
            agree[i, j] = (Vm[:, i] == Vm[:, j]).mean()
            kap[i, j] = kappa(Vm[:, i], Vm[:, j])
            ephi[i, j] = phi(E[:, i], E[:, j])
            if E[:, i].sum():
                cond[i, j] = E[E[:, i] == 1, j].mean()
                rescue[i, j] = A[E[:, i] == 1, j].mean()
    # error count distribution vs independence
    k = E.sum(1)
    rng = np.random.default_rng(0)
    p = E.mean(0)
    sim = np.concatenate([(rng.random((len(E), J)) < p).sum(1) for _ in range(200)])
    hist = [dict(k=int(i), seen=float((k == i).mean()), indep=float((sim == i).mean())) for i in range(J + 1)]
    # recovery decomposition of the best judge's errors
    eb = E[:, best] == 1
    right_others = A[:, [j for j in range(J) if j != best]].sum(1)
    n_o = J - 1
    maj_fix = eb & (right_others > n_o / 2)
    min_fix = eb & (right_others >= 1) & (right_others <= n_o / 2)
    none_fix = eb & (right_others == 0)
    # jury ceiling (in-sample pattern oracle) and cross-validated pattern jury
    keys = [tuple(r) for r in Vm]
    tab = {}
    for kk, yy in zip(keys, y):
        c = tab.setdefault(kk, [0, 0])
        c[yy] += 1
    jury_ceiling = sum(max(c) for c in tab.values()) / len(y)
    ug = np.unique(groups)
    cv = []
    for rep in range(5):
        r = np.random.default_rng(rep)
        fo = dict(zip(r.permutation(ug), np.arange(len(ug)) % 5))
        f = np.array([fo[g] for g in groups])
        pred = np.zeros(len(y), int)
        for kf in range(5):
            tr, te = np.where(f != kf)[0], np.where(f == kf)[0]
            pred[te] = pattern_jury(Vm, y, tr, te)
        cv.append((pred == y).mean())
    majority = ((Vm.mean(1) > 0.5).astype(int) == y).mean()
    # leniency
    pos = y == 1
    len_ = [dict(judge=pool[j], acc=float(acc[j]), fpr=float(((Vm[:, j] == 1) & ~pos).sum() / max((~pos).sum(), 1)),
                 fnr=float(((Vm[:, j] == 0) & pos).sum() / max(pos.sum(), 1))) for j in range(J)]
    # achieved (from analysis.json)
    ach = None
    ap = HERE / "results" / bench / "analysis.json"
    if ap.exists():
        an = json.loads(ap.read_text())
        rules = (an.get("juries") or {}).get("rules", [])
        if rules:
            r = max(rules, key=lambda x: x["acc"])
            base = next((x for x in rules if x["rule"] == "best_single"), None)
            ach = dict(rule=r["rule"], acc=r["acc"], size=r["size"], cv_best=base["acc"] if base else None)
    tri = list(combinations(range(J), 2))
    return dict(
        bench=bench, n=int(len(y)), fmt=FMT.get(bench, "single"), judges=pool, acc=[float(a) for a in acc], best=pool[best],
        agree=agree.round(4).tolist(), kappa=kap.round(4).tolist(), err_phi=ephi.round(4).tolist(),
        cond=cond.round(4).tolist(), rescue=rescue.round(4).tolist(),
        mean_agree=float(np.mean([agree[i, j] for i, j in tri])), mean_kappa=float(np.mean([kap[i, j] for i, j in tri])),
        mean_phi=float(np.mean([ephi[i, j] for i, j in tri])), kish=float(J / (1 + (J - 1) * np.mean([ephi[i, j] for i, j in tri]))),
        p_wrong=float(E.mean()), p_wrong_given=float(np.mean([cond[i, j] for i in range(J) for j in range(J) if i != j])),
        hist=hist, best_acc=float(acc[best]), majority=float(majority), jury_ceiling=float(jury_ceiling),
        jury_cv=float(np.mean(cv)), router_ceiling=float((A.max(1) == 1).mean()),
        fix=dict(majority=float(maj_fix.mean()), minority=float(min_fix.mean()), none=float(none_fix.mean()),
                 minority_one=float((eb & (right_others == 1)).mean())),
        leniency=len_, achieved=ach, position=position_bias(bench, pool) if FMT.get(bench) == "pair" else None,
        family=dict(within=float(np.mean([ephi[i, j] for i, j in tri if FAMILY[pool[i]] == FAMILY[pool[j]]])),
                    across=float(np.mean([ephi[i, j] for i, j in tri if FAMILY[pool[i]] != FAMILY[pool[j]]]))),
    )


# ----------------------------------------------------------------------------- HTML
def e(s):
    return html.escape(str(s))


def pct(x, d=1):
    return "–" if x is None else f"{100 * x:.{d}f}%"


def cell(v, lo, hi, ramp):
    t = 0 if v is None else max(0.0, min(1.0, (v - lo) / (hi - lo or 1)))
    k = int(round(t * 6))
    return f"background:var(--{ramp}{k});color:var({'--on-dark' if k >= 4 else '--ink'})"


def tri_table(r, lower_key, lower_lo, lower_hi, lower_fmt, ramp, diag_label, diag_key="acc"):
    js = r["judges"]
    M = r[lower_key]
    h = ['<div class="scroll"><table class="hm"><thead><tr><th></th>' + "".join(f'<th><span>{e(SHORT[j])}</span></th>' for j in js) + '</tr></thead><tbody>']
    for i, j in enumerate(js):
        h.append(f'<tr><th class="rh">{e(SHORT[j])}</th>')
        for c in range(len(js)):
            if c == i:
                v = r[diag_key][i]
                h.append(f'<td class="dg" style="{cell(v, 0.5, 1.0, "a")}" title="{e(SHORT[j])}: {diag_label} {pct(v)}">{100 * v:.0f}</td>')
            elif c < i:
                v = M[i][c]
                h.append(f'<td style="{cell(v, lower_lo, lower_hi, ramp)}" title="{e(SHORT[j])} × {e(SHORT[js[c]])}: {lower_fmt(v)}">{lower_fmt(v)}</td>')
            else:
                h.append('<td class="up"></td>')
        h.append('</tr>')
    h.append('</tbody></table></div>')
    return "".join(h)


def rescue_table(r):
    js = r["judges"]
    h = ['<div class="scroll"><table class="hm"><thead><tr><th class="rh">When this judge is wrong…</th>' +
         "".join(f'<th><span>{e(SHORT[j])}</span></th>' for j in js) + '</tr></thead><tbody>']
    for i, j in enumerate(js):
        h.append(f'<tr><th class="rh">{e(SHORT[j])}</th>')
        for c in range(len(js)):
            if c == i:
                h.append('<td class="up"></td>')
            else:
                v = r["rescue"][i][c]
                h.append(f'<td style="{cell(v, 0, 0.6, "g")}" title="When {e(SHORT[j])} is wrong, {e(SHORT[js[c]])} is right {pct(v, 0)} of the time">{100 * v:.0f}</td>')
        h.append('</tr>')
    h.append('</tbody></table></div>')
    return "".join(h)


def recovery_bar(r):
    """Stacked bar from best judge to router ceiling."""
    best, f = r["best_acc"], r["fix"]
    segs = [("best", best, "var(--seg0)", "Best judge right"), ("maj", f["majority"], "var(--seg1)", "Fixable by a majority of the others"),
            ("min", f["minority"], "var(--seg2)", "Only a minority of judges right"), ("none", f["none"], "var(--seg3)", "No judge right")]
    h = ['<div class="stack" role="img" aria-label="' + e(", ".join(f"{s[3]} {pct(s[1])}" for s in segs)) + '">']
    for k, v, c, lab in segs:
        h.append(f'<i style="width:{100 * v:.2f}%;background:{c}" title="{e(lab)}: {pct(v)}"></i>')
    h.append('</div>')
    return "".join(h)


def hist_svg(r):
    W, H, L, B = 520, 200, 40, 34
    J = len(r["judges"])
    ys = [max(h["seen"], h["indep"]) for h in r["hist"]]
    ym = max(ys) * 1.1
    bw = (W - L - 12) / (J + 1)
    X = lambda i: L + i * bw
    Y = lambda v: H - B - (H - B - 12) * v / ym
    s = [f'<svg viewBox="0 0 {W} {H}" class="hist" role="img" aria-label="Share of items by number of judges wrong, observed vs independent errors">']
    for t in np.linspace(0, ym, 4):
        s.append(f'<line class="gl" x1="{L}" x2="{W - 12}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/><text x="{L - 6}" y="{Y(t) + 4:.1f}" text-anchor="end">{100 * t:.0f}%</text>')
    for h in r["hist"]:
        i = h["k"]
        s.append(f'<rect x="{X(i) + 4:.1f}" y="{Y(h["seen"]):.1f}" width="{bw * 0.45:.1f}" height="{Y(0) - Y(h["seen"]):.1f}" fill="var(--s1)" rx="2"><title>{i} judges wrong: {pct(h["seen"])} of items (independent: {pct(h["indep"])})</title></rect>')
        s.append(f'<rect x="{X(i) + 4 + bw * 0.45:.1f}" y="{Y(h["indep"]):.1f}" width="{bw * 0.35:.1f}" height="{Y(0) - Y(h["indep"]):.1f}" fill="var(--s2)" rx="2"/>')
        s.append(f'<text x="{X(i) + bw / 2:.1f}" y="{H - B + 15}" text-anchor="middle">{i}</text>')
    s.append(f'<text x="{(L + W) / 2:.0f}" y="{H - 4}" text-anchor="middle">judges wrong on the item (of {J})</text></svg>')
    return "".join(s)


CSS = """
:root{--bg:#f6f6f3;--surface:#fff;--ink:#1b2129;--ink-2:#4d5662;--ink-3:#707a85;--line:#dfe2e4;--accent:#2b5c8a;--on-dark:#fff;
--a0:#eef3f8;--a1:#d4e2ef;--a2:#adc8e1;--a3:#7fa8cf;--a4:#4f86bb;--a5:#2f679f;--a6:#1b4878;
--r0:#f8efe9;--r1:#f2d9c9;--r2:#e8b597;--r3:#d98a61;--r4:#c4643a;--r5:#a04a25;--r6:#783416;
--g0:#ecf5ef;--g1:#cfe8d7;--g2:#a3d2b2;--g3:#6fb68a;--g4:#3f9765;--g5:#26784c;--g6:#165a37;
--s1:#2a78d6;--s2:#b9c2cb;--seg0:#b9c2cb;--seg1:#3f9765;--seg2:#e0a43a;--seg3:#c4643a;--pf:#c4502a;--pc:#eceef0;--ps:#1d8a69;
--display:"Fraunces",Georgia,serif;--body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121518;--surface:#1a1e23;--ink:#e8ebee;--ink-2:#b7bfc7;--ink-3:#8f99a3;--line:#2d343b;--accent:#7fb0e0;--on-dark:#0f1316;
--a0:#1c2530;--a1:#1f3449;--a2:#24476a;--a3:#2d5e8c;--a4:#4a80b5;--a5:#7aa6d3;--a6:#b4cfea;
--r0:#2a201b;--r1:#4a2c1d;--r2:#6d3a22;--r3:#94502e;--r4:#c06b42;--r5:#de9a76;--r6:#f2c9b2;
--g0:#18241d;--g1:#1d3a28;--g2:#225236;--g3:#2d6e48;--g4:#3f9765;--g5:#77c193;--g6:#b5e2c4;
--s1:#4f95e6;--s2:#4a535c;--seg0:#4a535c;--seg1:#3f9765;--seg2:#d49a35;--seg3:#c06b42;--pf:#d0653d;--pc:#262c32;--ps:#2a9d79;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#121518;--surface:#1a1e23;--ink:#e8ebee;--ink-2:#b7bfc7;--ink-3:#8f99a3;--line:#2d343b;--accent:#7fb0e0;--on-dark:#0f1316;
--a0:#1c2530;--a1:#1f3449;--a2:#24476a;--a3:#2d5e8c;--a4:#4a80b5;--a5:#7aa6d3;--a6:#b4cfea;
--r0:#2a201b;--r1:#4a2c1d;--r2:#6d3a22;--r3:#94502e;--r4:#c06b42;--r5:#de9a76;--r6:#f2c9b2;
--g0:#18241d;--g1:#1d3a28;--g2:#225236;--g3:#2d6e48;--g4:#3f9765;--g5:#77c193;--g6:#b5e2c4;
--s1:#4f95e6;--s2:#4a535c;--seg0:#4a535c;--seg1:#3f9765;--seg2:#d49a35;--seg3:#c06b42;--pf:#d0653d;--pc:#262c32;--ps:#2a9d79;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.6 var(--body)}
.wrap{max-width:1060px;margin:0 auto;padding-block:36px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:26px}
.eyebrow{font:500 12px/1.4 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
h1{font:600 clamp(28px,4.6vw,40px)/1.1 var(--display);margin:6px 0 10px;text-wrap:balance}
h2{font:600 22px/1.25 var(--display);margin:0;text-wrap:balance}
h3{font:600 15px/1.35 var(--body);margin:0}
p{margin:0;max-width:72ch}.sub{color:var(--ink-2)}.note{font-size:13px;color:var(--ink-3);max-width:80ch}
.tabs{display:flex;gap:6px;overflow-x:auto;padding-bottom:6px;border-bottom:1px solid var(--line)}
.tabs button{flex:none;font:500 13px var(--body);padding:7px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink-2);cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.tabs button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.panel{display:grid;gap:24px}.panel[hidden]{display:none}
section{display:grid;gap:10px}
.grid2{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr))}
.grid2>*{min-width:0;display:grid;gap:8px;align-content:start}
.scroll{overflow-x:auto}
table{border-collapse:collapse;font-variant-numeric:tabular-nums}
table.t{width:100%;font-size:14px}
table.t th{text-align:left;font:500 11px/1.4 var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);padding:7px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
table.t td{padding:8px;border-bottom:1px solid var(--line);white-space:nowrap}
table.t td.n,table.t th.n{text-align:right}
table.hm{font:12px var(--mono);border-collapse:separate;border-spacing:2px}
table.hm th{font-weight:500;color:var(--ink-2);padding:2px 4px}
table.hm thead th{height:96px;vertical-align:bottom}
table.hm thead th span{display:inline-block;writing-mode:vertical-rl;transform:rotate(180deg);white-space:nowrap}
table.hm th.rh{text-align:right;white-space:nowrap;font-family:var(--body);font-size:12.5px}
table.hm td{width:46px;height:30px;text-align:center;border-radius:4px}
table.hm td.dg{outline:1.5px solid var(--ink);outline-offset:-1.5px;font-weight:600}
table.hm td.up{background:transparent}
.stack{display:flex;height:22px;border-radius:5px;overflow:hidden;background:var(--line);min-width:220px}
.stack i{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12.5px;color:var(--ink-2)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend b{display:inline-block;width:12px;height:12px;border-radius:3px}
.tiles{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(min(100%,170px),1fr))}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile .v{font:600 24px/1.1 var(--display);font-variant-numeric:tabular-nums}.tile .l{font-size:13px;color:var(--ink-2);margin-top:3px}
.callout{border-left:3px solid var(--accent);background:var(--surface);padding:12px 16px;font-size:14.5px;max-width:86ch}
ul.k{margin:0;padding-left:20px;display:grid;gap:6px;max-width:86ch}
svg.hist{width:100%;max-width:560px;height:auto}
svg text{font:11px var(--mono);fill:var(--ink-3)} svg .gl{stroke:var(--line)}
.pb{display:grid;gap:6px}
.pb-row{display:grid;grid-template-columns:130px minmax(0,1fr) 180px;gap:10px;align-items:center;font-size:13px}
.pb-nm{text-align:right;color:var(--ink)}
.pb-bar{display:flex;height:22px;border-radius:4px;overflow:hidden;background:var(--pc)}
.pb-bar i{display:block;height:100%;font:normal 11px/22px var(--mono);text-align:center;white-space:nowrap;overflow:hidden}
.pf{background:var(--pf);color:#fff}.pc{background:var(--pc);color:var(--ink-2)}.ps{background:var(--ps);color:#fff}
.pb-p{font:12px var(--mono);color:var(--ink-2);white-space:nowrap}.pb-p b{color:var(--pf);font-weight:600}
@media (max-width:560px){.pb-row{grid-template-columns:90px minmax(0,1fr)}.pb-p{grid-column:2}}
.ramp{display:inline-flex;border-radius:3px;overflow:hidden;vertical-align:middle}.ramp i{width:16px;height:10px}
"""

JS = """
const tabs=[...document.querySelectorAll('.tabs button')];
function show(id){tabs.forEach(b=>b.setAttribute('aria-selected',b.dataset.t===id));document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==id);}
tabs.forEach(b=>b.addEventListener('click',()=>show(b.dataset.t)));
const h=(location.hash||'').slice(1);show(tabs.some(b=>b.dataset.t===h)?h:'overview');
"""


def ramp(name):
    return '<span class="ramp">' + "".join(f'<i style="background:var(--{name}{k})"></i>' for k in range(7)) + '</span>'


def pfmt(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}" if p < 0.995 else "1.00"


def position_section(r):
    P = r.get("position")
    if not P:
        return ""
    rows = sorted(P["rows"], key=lambda x: -x["consistent"])
    bars = []
    for x in rows:
        sig = x["holm"] < 0.05
        lab = lambda v: f"{100 * v:.0f}%" if v >= 0.06 else ""
        bars.append(
            f'<div class="pb-row"><span class="pb-nm">{e(SHORT[x["judge"]])}</span>'
            f'<div class="pb-bar" role="img" aria-label="{e(SHORT[x["judge"]])}: first-shown both times {pct(x["first"])}, same answer both orders {pct(x["consistent"])}, second-shown both times {pct(x["second"])}">'
            f'<i class="pf" style="width:{100 * x["first"]:.2f}%" title="first-shown both times: {pct(x["first"])} ({x["F"]} pairs)">{lab(x["first"])}</i>'
            f'<i class="pc" style="width:{100 * x["consistent"]:.2f}%" title="same answer in both orders: {pct(x["consistent"])}">{100 * x["consistent"]:.0f}%</i>'
            f'<i class="ps" style="width:{100 * x["second"]:.2f}%" title="second-shown both times: {pct(x["second"])} ({x["S"]} pairs)">{lab(x["second"])}</i></div>'
            f'<span class="pb-p">{x["F"]} vs {x["S"]} · {"<b>" if sig else ""}p {pfmt(x["holm"])}{"</b>" if sig else ""}</span></div>')
    tab = "".join(f'<tr><td>{e(SHORT[x["judge"]])}</td><td class="n">{pct(x["consistent"], 0)}</td><td class="n">{x["F"]}</td><td class="n">{x["S"]}</td>'
                  f'<td class="n">{pfmt(x["p"])}</td><td class="n">{"<b>" if x["holm"] < 0.05 else ""}{pfmt(x["holm"])}{"</b>" if x["holm"] < 0.05 else ""}</td>'
                  f'<td class="n">{pct(x["err_from_switch"], 0)}</td></tr>' for x in rows)
    F, S = P["pooled_first"], P["pooled_second"]
    lead = (f'Pooled over all judges, a judge whose pick switches with the order lands on the first-shown answer {F} times vs {S} for the second '
            f'({pct(F / max(F + S, 1), 0)} / {pct(S / max(F + S, 1), 0)}; conversation-level permutation test p {pfmt(P["pooled_p"])}).')
    return ('<section><h3>Does the order of the two answers change the verdict?</h3>'
            f'<p class="sub">{lead} Every pair was shown in both orders, so a judge without position bias lands on "first" and "second" equally often when it switches.</p>'
            '<div class="legend"><span><b style="background:var(--pf)"></b>picked the first-shown answer both times</span>'
            '<span><b style="background:var(--pc);outline:1px solid var(--line)"></b>same answer in both orders</span>'
            '<span><b style="background:var(--ps)"></b>picked the second-shown answer both times</span></div>'
            '<div class="pb">' + "".join(bars) + '</div>'
            '<div class="scroll"><table class="t"><thead><tr><th>Judge</th><th class="n">Same answer both orders</th><th class="n">First both times</th>'
            '<th class="n">Second both times</th><th class="n">Binomial p</th><th class="n">Holm p</th><th class="n">Errors on order-switching pairs</th></tr></thead>'
            f'<tbody>{tab}</tbody></table></div>'
            '<p class="note">Test: exact binomial test of "first both times" vs "second both times" per judge (H0: order has no effect), Holm-corrected across judges; '
            'pooled: sign-flip permutation test with whole conversations or prompts as units. Unparsed verdicts are dropped. Each verdict is one sample at temperature 0.7, '
            'so some switching may be sampling noise rather than order; repeating each order twice would separate the two. '
            '"Errors on order-switching pairs" = share of the judge\'s errors that fall on pairs where its pick changed with the order: those verdicts are free to flag for escalation, since both orders are already judged.</p></section>')


def panel(r):
    f = r["fix"]
    ach = r["achieved"] or {}
    pair = r["fmt"] == "pair"
    out = [f'<div class="panel" id="{r["bench"]}" hidden>',
           f'<section><h2>{e(TITLE[r["bench"]])}</h2><p class="sub">{r["n"]:,} {"presentations (each pair in both orders)" if pair else "graded responses"}, 8 judges, no reference answer. Best judge: {e(SHORT[r["best"]])} ({pct(r["best_acc"])}).</p></section>',
           '<section><h3>Room for recovery</h3>',
           '<div class="tiles">'
           f'<div class="tile"><div class="v">{pct(r["best_acc"])}</div><div class="l">best single judge</div></div>'
           f'<div class="tile"><div class="v">{pct(r["jury_cv"])}</div><div class="l">best verdict-pattern jury, cross-validated</div></div>'
           f'<div class="tile"><div class="v">{pct(r["jury_ceiling"])}</div><div class="l">jury ceiling: any rule on the 8 verdicts (in-sample)</div></div>'
           f'<div class="tile"><div class="v">{pct(r["router_ceiling"])}</div><div class="l">router ceiling: any judge right</div></div></div>',
           recovery_bar(r),
           '<div class="legend"><span><b style="background:var(--seg0)"></b>best judge right</span><span><b style="background:var(--seg1)"></b>best wrong, majority of the others right</span>'
           '<span><b style="background:var(--seg2)"></b>best wrong, only a minority right</span><span><b style="background:var(--seg3)"></b>no judge right</span></div>',
           f'<p class="note">Of all items: the best judge is wrong on {pct(1 - r["best_acc"])}. A vote of the others could fix {pct(f["majority"])}; '
           f'{pct(f["minority"])} are right only for a minority ({pct(f["minority_one"])} for a single judge), which a router could reach only by knowing whom to trust on that item; '
           f'{pct(f["none"])} no judge gets right. Best tested rule so far: {e(ach.get("rule", "–"))} at {pct(ach.get("acc"))}.</p></section>',
           '<div class="grid2"><div><h3>Accuracy and verdict agreement</h3>' +
           tri_table(r, "kappa", 0, 1, lambda v: f"{v:.2f}", "a", "agreement with gold") +
           f'<p class="note">Diagonal: each judge\'s agreement with the gold label (%). Lower triangle: Cohen\'s κ between two judges\' verdicts (1 = always the same verdict, 0 = chance). {ramp("a")} Mean κ {r["mean_kappa"]:.2f}; raw agreement {pct(r["mean_agree"], 0)}.</p></div>',
           '<div><h3>Error overlap</h3>' + tri_table(r, "err_phi", 0, 0.7, lambda v: f"{v:.2f}", "r", "agreement with gold") +
           f'<p class="note">Lower triangle: φ correlation of the two judges\' errors (0 = independent mistakes). {ramp("r")} Mean φ {r["mean_phi"]:.2f}; within family {r["family"]["within"]:.2f} vs across {r["family"]["across"]:.2f}. '
           f'These 8 judges are worth about {r["kish"]:.1f} independent votes.</p></div></div>',
           '<div class="grid2"><div><h3>Who rescues whom</h3>' + rescue_table(r) +
           '<p class="note">Row: the judge that is wrong. Cell: % of that judge\'s errors the column judge gets right. High values mark complementary pairs; a router can only gain where these are high.</p></div>',
           '<div><h3>How many judges are wrong together</h3>' + hist_svg(r) +
           f'<div class="legend"><span><b style="background:var(--s1)"></b>observed</span><span><b style="background:var(--s2)"></b>if errors were independent</span></div>'
           f'<p class="note">On average a judge is wrong on {pct(r["p_wrong"], 0)} of items, but on {pct(r["p_wrong_given"], 0)} of the items where another given judge is wrong. Observed counts pile up at 0 and at "most judges wrong".</p></div></div>',
           '<section><h3>Error direction per judge</h3><div class="scroll"><table class="t"><thead><tr><th>Judge</th><th class="n">Agreement</th><th class="n">' +
           ("Picks the worse answer when the first is better" if pair else "Accepts a bad answer (FPR)") + '</th><th class="n">' +
           ("Picks the worse answer when the second is better" if pair else "Rejects a good answer (FNR)") + '</th></tr></thead><tbody>' +
           "".join(f'<tr><td>{e(SHORT[x["judge"]])}</td><td class="n">{pct(x["acc"])}</td><td class="n">{pct(x["fpr"])}</td><td class="n">{pct(x["fnr"])}</td></tr>' for x in r["leniency"]) +
           '</tbody></table></div></section>', position_section(r), '</div>']
    return "".join(out)


def position_overview(R):
    P = [r for r in R if r.get("position")]
    if not P:
        return ""
    rows = []
    for r in P:
        p = r["position"]
        sig = [x for x in p["rows"] if x["holm"] < 0.05]
        F, S = p["pooled_first"], p["pooled_second"]
        rows.append(f'<tr><td><a href="#{r["bench"]}" data-go="{r["bench"]}">{e(TITLE[r["bench"]])}</a></td><td class="n">{pct(p["pooled_consistent"], 0)}</td>'
                    f'<td class="n">{F} vs {S}</td><td class="n">{pct(F / max(F + S, 1), 0)}</td><td class="n">{pfmt(p["pooled_p"])}</td>'
                    f'<td>{", ".join(e(SHORT[x["judge"]]) for x in sig) or "none"}</td></tr>')
    return ('<section><h3>Order of the answers (pairwise benchmarks)</h3>'
            '<p class="sub">Each pair was judged in both orders. When a judge\'s pick switches with the order, does it favour the first-shown answer? Per-benchmark charts are in each pairwise tab.</p>'
            '<div class="scroll"><table class="t"><thead><tr><th>Benchmark</th><th class="n">Same answer both orders</th><th class="n">First vs second both times</th>'
            '<th class="n">Share first</th><th class="n">Pooled p</th><th>Judges with significant bias (Holm p &lt; 0.05)</th></tr></thead><tbody>' + "".join(rows) +
            '</tbody></table></div></section>')


def overview(R):
    rows = []
    for r in R:
        f, a = r["fix"], r["achieved"] or {}
        rows.append(f'<tr><td><a href="#{r["bench"]}" data-go="{r["bench"]}">{e(TITLE[r["bench"]])}</a></td><td class="n">{r["n"]:,}</td><td class="n">{pct(r["best_acc"])}</td>'
                    f'<td class="n">{pct(a.get("acc"))}</td><td class="n">{pct(r["jury_cv"])}</td><td class="n">{pct(r["jury_ceiling"])}</td><td class="n">{pct(r["router_ceiling"])}</td>'
                    f'<td>{recovery_bar(r)}</td><td class="n">{r["mean_phi"]:.2f}</td><td class="n">{r["kish"]:.1f}</td></tr>')
    m = lambda key: np.mean([r[key] for r in R])
    mf = lambda key: np.mean([r["fix"][key] for r in R])
    gap = m("router_ceiling") - m("best_acc")
    h = ['<div class="panel" id="overview" hidden><section><h2>How much can choosing or combining judges recover?</h2>',
         f'<p class="sub">Averaged over {len(R)} benchmarks: the best single judge is right {pct(m("best_acc"))} of the time and "any judge right" {pct(m("router_ceiling"))}, a gap of {100 * gap:.1f} points. '
         f'Only {100 * mf("majority"):.1f} points of it are errors a majority of the other judges gets right; {100 * mf("minority"):.1f} points are right only for a minority, and {100 * mf("none"):.1f} points for no judge.</p>',
         '<div class="callout">'
         f'A jury that only sees the 8 verdicts can reach at most {pct(m("jury_ceiling"))} even in-sample ({100 * (m("jury_ceiling") - m("best_acc")):+.1f} points over the best judge), and {pct(m("jury_cv"))} cross-validated. '
         'Everything above that sits on items where most judges are wrong: a router can only win it with item-level information that tells it which minority judge to trust, and on single-judge rescues that is mostly a lucky guess on a yes/no verdict.</div></section>',
         '<section><h3>Benchmark by benchmark</h3><div class="scroll"><table class="t"><thead><tr><th>Benchmark</th><th class="n">Items</th><th class="n">Best judge</th><th class="n">Best tested rule</th>'
         '<th class="n">Pattern jury (CV)</th><th class="n">Jury ceiling</th><th class="n">Router ceiling</th><th>Where the best judge\'s errors fall</th><th class="n">Mean error φ</th><th class="n">Indep. votes of 8</th></tr></thead><tbody>',
         "".join(rows), '</tbody></table></div>',
         '<div class="legend"><span><b style="background:var(--seg0)"></b>best judge right</span><span><b style="background:var(--seg1)"></b>majority of others right</span>'
         '<span><b style="background:var(--seg2)"></b>only a minority right</span><span><b style="background:var(--seg3)"></b>no judge right</span></div>',
         '<p class="note">Best tested rule: the most accurate cross-validated rule from the jury experiments (best single judge, majority vote, top-k or threshold jury). '
         'Pattern jury: a lookup from the 8-verdict pattern to the most common gold label, learned on training folds. Jury ceiling: the same lookup fitted on all items, an upper bound for any rule that sees only verdicts. '
         'Router ceiling: correct whenever any judge is right. Independent votes: Kish effective number from the mean error correlation.</p></section>',
         position_overview(R),
         '<section><h3>Definitions and data</h3><ul class="k">'
         '<li>8 Tinker judges (gpt-oss-120b/20b, DeepSeek-V3.1, Qwen3.6-35B, Qwen3.5-9B/4B, Nemotron-3 Super-120B / Nano-30B), one sample each at temperature 0.7, no reference answer.</li>'
         '<li>Gold labels: human labels (2-of-3 majority where three votes exist), human choices, or verified answers, as in the cross-benchmark report.</li>'
         '<li>Raw verdicts: <code>experiments/tinker_pool/*_results*/judgments.jsonl</code> and <code>experiments/cross_benchmark/results/&lt;benchmark&gt;/judgments.jsonl</code>; this page is built by <code>similarity_report.py</code>.</li></ul></section></div>']
    return "".join(h)


def main():
    R = []
    for b in ORDER:
        if (HERE / "data" / f"{b}_decisions.pkl").exists():
            try:
                R.append(analyse(b))
            except Exception as ex:  # keep the page buildable while some benchmarks are still running
                print("skip", b, ex)
    (HERE / "results" / "similarity_report.json").write_text(json.dumps(R, indent=1))
    nav = '<div class="tabs" role="tablist"><button role="tab" data-t="overview">Overview</button>' + "".join(
        f'<button role="tab" data-t="{r["bench"]}">{e(TITLE[r["bench"]])}</button>' for r in R) + '</div>'
    page = ('<meta charset="utf-8"><title>Judge Agreement Atlas</title><meta name="claude:viewport-fit-sides" content="cover">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
            f'<style>{CSS}</style><div class="wrap"><header><div class="eyebrow">AC 297r · Dynamic LLM Juries · judge similarity</div>'
            '<h1>Judge Agreement Atlas</h1><p class="sub">Where the 8 judges agree, where their errors overlap, and how much of the gap to "any judge right" a judge router or a jury could actually recover.</p></header>'
            f'{nav}{overview(R)}{"".join(panel(r) for r in R)}</div>'
            '<script>' + JS + 'document.querySelectorAll("[data-go]").forEach(a=>a.addEventListener("click",ev=>{ev.preventDefault();show(a.dataset.go);}));</script>')
    (HERE / "results" / "similarity_report.html").write_text(page)
    print("built", [r["bench"] for r in R])
    for r in R:
        f = r["fix"]
        print(f'{r["bench"]:10s} best {r["best_acc"]:.3f} jury_cv {r["jury_cv"]:.3f} jury_ceiling {r["jury_ceiling"]:.3f} router {r["router_ceiling"]:.3f} | '
              f'fix maj {f["majority"]:.3f} min {f["minority"]:.3f} (one {f["minority_one"]:.3f}) none {f["none"]:.3f} | phi {r["mean_phi"]:.2f} kish {r["kish"]:.1f}')


if __name__ == "__main__":
    main()
