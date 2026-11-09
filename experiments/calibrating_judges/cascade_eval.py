#!/usr/bin/env python
"""Dynamic-jury cascade experiment. A cheap reasoning judge L grades every item. A confidence signal ranks the items by how much L should be trusted; the least trusted fraction k is
escalated to a stronger judge / panel H, whose verdict replaces L's. System accuracy as a function of k, for each confidence signal, against random escalation (the line from
L-only to H-only accuracy) and an oracle (escalate exactly the items L got wrong first).

Signals for L (all computed from L's own runs; nothing sees the human label of the item it scores):
  probe          linear probe on L's last-token activations (arXiv 2512.22245 settings), out-of-fold: 5-fold cross-fitting by question over the pooled benchmarks; two layer choices:
                 the paper's fixed middle layer and the layer picked on a validation split inside each training fold
  verbalized     the 0-100 confidence L states (its own confidence-prompt run; that run's verdict is the system verdict)
  consistency    share of N=10 temperature-0.7 samples that agree with L's greedy verdict (costs 11x the generation)
  semantic_entropy   1 - H/ln2 of the verdict distribution over the N samples (binary verdicts: clusters = verdict values)
An item whose verdict did not parse (the judge was cut off or did not answer) is escalated first, for every signal. Escalation targets: a second reasoning judge from our runs
(all benchmarks) and, for BFF / RewardBench-2 Safety, the saved verdicts of the 8-judge pool (best single judge; top-3 majority vote).
Reports accuracy at several escalation rates, the gain over random escalation (area between the curve and the random line, as a share of the oracle's), question-bootstrap CIs, and the
generated tokens each signal needs per item. Writes tables and plots to --out."""
import argparse, json, os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from evaluate import train_probe, predict
from metrics import brier

BENCH = ["bff", "rb2safety", "judgebench"]
HOSTED = ["Qwen3.5-4B", "Qwen3.5-9B", "gpt-oss-20b"]
RATES = np.linspace(0, 1, 51)


def gen(path):
    return pd.read_json(path, lines=True, dtype={"item_id": str})


def load_run(R, model, bench, kind):
    d = f"{R}/{model}__{bench}__{kind}"; return d, f"{d}/{model}__{bench}__{kind}"


def oof_probe(R, model, layer_fixed, seed=0, folds=5, val_frac=0.15, epochs=10, fixed_only=False):
    """out-of-fold probe confidence for every item of every benchmark (pooled training, folds grouped by question). returns {bench: (conf_fixed, conf_val, ids)}"""
    A, Y, G, ids, bench_of = [], [], [], [], []
    for b in BENCH:
        d, p = load_run(R, model, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); g0 = gen(f"{p}_gen.jsonl").set_index("item_id")
        A.append(np.load(f"{p}_acts.npy").astype(np.float32)); Y.append(g0.loc[itm["item_id"], "correct"].values.astype(int)); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; ids += list(itm["item_id"]); bench_of += [b] * len(itm)
        layers = json.load(open(f"{p}_layers.json"))
    A = np.concatenate(A); Y = np.concatenate(Y); G = np.array(G); ids = np.array(ids); bench_of = np.array(bench_of); li_fix = layers.index(layer_fixed)
    rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % folds for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
    c_fix = np.zeros(len(Y)); c_val = np.zeros(len(Y)); chosen = []
    for k in range(folds):
        te = np.where(f == k)[0]; tr_all = np.where(f != k)[0]; tg = rng.permutation(np.unique(G[tr_all])); n_va = max(1, int(round(val_frac * len(tg)))); va_g = set(tg[:n_va])
        va = tr_all[np.array([g in va_g for g in G[tr_all]])]; tr = tr_all[np.array([g not in va_g for g in G[tr_all]])]; vb = []
        if fixed_only:
            c_fix[te] = predict(train_probe(A[tr_all][:, li_fix], Y[tr_all], epochs=epochs, seed=seed + k), A[te][:, li_fix]); continue
        for li in range(len(layers)):
            lin = train_probe(A[tr][:, li], Y[tr], epochs=epochs, seed=seed + k); vb.append(brier(predict(lin, A[va][:, li]), Y[va]))
            if li == li_fix:
                c_fix[te] = predict(train_probe(A[tr_all][:, li], Y[tr_all], epochs=epochs, seed=seed + k), A[te][:, li])
        lv = int(np.argmin(vb)); chosen.append(layers[lv]); c_val[te] = predict(train_probe(A[tr_all][:, lv], Y[tr_all], epochs=epochs, seed=seed + k), A[te][:, lv]); print(f"  fold {k}: validation layer {layers[lv]}", flush=True)
    return {b: (c_fix[bench_of == b], c_val[bench_of == b], ids[bench_of == b]) for b in BENCH}


def curve(conf, ok_low, ok_high):
    """accuracy of the system when the fraction k with the lowest confidence is escalated (ties broken randomly but reproducibly)"""
    order = np.argsort(conf + 1e-9 * np.random.default_rng(0).random(len(conf)), kind="stable"); n = len(conf); acc = []
    for k in RATES:
        m = int(round(k * n)); esc = np.zeros(n, bool); esc[order[:m]] = True; acc.append(np.where(esc, ok_high, ok_low).mean())
    return np.array(acc)


def gain(acc, a_low, a_high):                                   # area between the curve and the random-escalation line, per unit of escalation rate
    f = getattr(np, "trapezoid", None) or np.trapz
    return float(f(acc - (a_low + RATES * (a_high - a_low)), RATES))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", default="Qwen3.5-4B"); ap.add_argument("--high", default="Qwen3.5-9B"); ap.add_argument("--results", default="local_results"); ap.add_argument("--layer", type=int, default=16)
    ap.add_argument("--judgments-bff", default="../tinker_pool_8models_judgments_bff.jsonl"); ap.add_argument("--judgments-rb2", default="../tinker_pool_8models_judgments.jsonl")
    ap.add_argument("--seeds", type=int, default=1, help="number of probe trainings (fold assignment + initialisation); the extra seeds use the fixed layer only"); ap.add_argument("--n-boot", type=int, default=300); ap.add_argument("--out", default="results_cascade"); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); pd.set_option("display.width", 220)
    print("out-of-fold probe confidences (pooled BFF + RewardBench-2 Safety + JudgeBench, 5 folds by question)", flush=True)
    P = oof_probe(a.results, a.low, a.layer, a.seed)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels")); from data import load_judgments; from audit import match_matrix
    rows, tok_rows, ctx, curve_rows = [], [], {}, []
    for b in BENCH:
        _, pl = load_run(a.results, a.low, b, "uncertainty__n1_t0.0"); _, pv = load_run(a.results, a.low, b, "confidence__n1_t0.0"); _, ps = load_run(a.results, a.low, b, "uncertainty__n10_t0.7")
        _, ph = load_run(a.results, a.high, b, "uncertainty__n1_t0.0")
        L = gen(f"{pl}_gen.jsonl").set_index("item_id"); V = gen(f"{pv}_gen.jsonl").set_index("item_id"); S = gen(f"{ps}_gen.jsonl"); H = gen(f"{ph}_gen.jsonl").set_index("item_id")
        conf_fix, conf_val, ids = P[b]; ids = list(ids); L = L.loc[ids]; H = H.loc[ids]; V = V.reindex(ids); groups = L["group"].astype(str).values
        gv = L["verdict"]; parsed = gv.notna().values
        # consistency / semantic entropy from the N samples, relative to the greedy verdict
        cons, sem, samp_tok = np.full(len(ids), np.nan), np.full(len(ids), np.nan), np.zeros(len(ids)); pos = {i: k for k, i in enumerate(ids)}
        for iid, d in S.groupby("item_id"):
            if iid not in pos: continue
            k = pos[iid]; n = len(d); vs = [x for x in d["verdict"].tolist() if x is not None and not (isinstance(x, float) and np.isnan(x))]; samp_tok[k] = d["n_tokens"].sum()
            if parsed[k]: cons[k] = sum(1 for x in vs if x == gv.iloc[k]) / n
            cl = [c for c in list(pd.Series(vs).value_counts().values) + [n - len(vs)] if c > 0]; pr = np.array(cl) / n; sem[k] = 1 - float(-(pr * np.log(pr)).sum()) / np.log(2)
        ok_l = L["correct"].values.astype(int); ok_v = V["correct"].fillna(0).values.astype(int); vconf = V["confidence"].values.astype(float); vparsed = V["verdict"].notna().values & ~np.isnan(vconf)
        sig = {"probe (layer %d, paper)" % a.layer: (conf_fix, ok_l, parsed), "probe (validation layer)": (conf_val, ok_l, parsed), "verbalized": (np.nan_to_num(vconf), ok_v, vparsed),
               "consistency (N=10)": (np.nan_to_num(cons), ok_l, parsed), "semantic entropy (N=10)": (np.nan_to_num(sem), ok_l, parsed)}
        sig["cut-off only (free rule)"] = (np.zeros(len(ids)), ok_l, parsed)             # no information beyond "the judge did not finish"; ties are broken at random
        tk = f"{pl}_tokstats.csv"
        if os.path.exists(tk):                                                         # single-pass token-probability signals (token_stats.py), 1x cost
            T_ = pd.read_csv(tk, dtype={"item_id": str}).set_index("item_id").reindex(ids)
            for nm, col, sg in (("token log-prob (perplexity)", "mean_logprob", 1), ("token entropy", "mean_entropy", -1), ("MaxProb (mean over tokens)", "mean_maxprob", 1),
                                ("energy (log-sum-exp)", "mean_lse", 1), ("verdict-token prob", "verdict_prob", 1)):
                sig[nm] = (np.nan_to_num(sg * T_[col].values.astype(float), nan=-1e9), ok_l, parsed)
        lv = L["verdict"].values; lkey = a.low.lower(); disc = None
        if b == "judgebench":                                                          # the other hosted reasoning judges (greedy verdicts on the same pairs)
            oth = [m_ for m_ in HOSTED if m_ != a.low]; cols = []
            for m_ in oth:
                _, po = load_run(a.results, m_, b, "uncertainty__n1_t0.0"); cols.append(gen(f"{po}_gen.jsonl").set_index("item_id").reindex(ids)["verdict"].values)
            O = np.array(cols, dtype=object).T; disc = np.array([np.nan if not len([x for x in row if isinstance(x, str)]) else np.mean([x != lv[i] for x in row if isinstance(x, str)]) for i, row in enumerate(O)], dtype=float)
        targets = {f"{a.high} (reasoning judge)": H["correct"].values.astype(int)}
        if b in ("bff", "rb2safety"):
            d = load_judgments(a.judgments_bff if b == "bff" else a.judgments_rb2, b, condition="none"); C = match_matrix(d.Z, d.Y).astype(int); jn = list(d.judge_names); idx = {i: k for k, i in enumerate(d.item_ids)}
            sel = np.array([idx.get(i, -1) for i in ids]); assert (sel >= 0).all(), "item ids of the judge pool do not cover our items"; C = C[sel]; acc = C.mean(0); top3 = list(np.argsort(-acc)[:3]); best = int(np.argmax(acc))
            Zs0 = d.Z[sel]; oth = [k for k, n_ in enumerate(jn) if n_.lower() != lkey]; disc = np.array([np.nan if np.isnan(lv[i]) else np.mean(Zs0[i, oth] != lv[i]) for i in range(len(ids))], dtype=float)
            print(f"  [{b}] sanity: L's verdict agrees with the saved pool's majority on {np.nanmean((lv == (Zs0[:, oth].mean(1) > 0.5)).astype(float)[parsed]):.3f} of finished items; L is excluded from its own pool", flush=True)
            targets[f"best saved judge: {jn[best]}"] = C[:, best]; Zs = d.Z[sel]; vote = (Zs[:, top3].sum(1) * 2 > 3).astype(int); targets["saved top-3 vote: " + ", ".join(jn[i] for i in top3)] = (vote == d.Y[sel]).astype(int)
        if disc is not None:
            sig["other judges disagree" + (" (%d saved judges)" % len(oth) if b != "judgebench" else " (2 hosted judges)")] = (np.nan_to_num(1 - disc, nan=0.5), ok_l, parsed)
        ctx[b] = dict(ids=ids, ok_l=ok_l, parsed=parsed, groups=groups, targets=targets, a_low=ok_l.mean())
        for tname, ok_h in targets.items():
            fig, ax = plt.subplots(figsize=(7.2, 4.6)); a_low, a_high = ok_l.mean(), ok_h.mean(); ax.plot(RATES, a_low + RATES * (a_high - a_low), "k--", lw=1, label="random escalation")
            curve_rows += [dict(bench=b, target=tname, signal="random escalation", rate=float(k), acc=float(a_low + k * (a_high - a_low))) for k in RATES]; order = np.argsort(ok_l, kind="stable"); oracle = np.array([np.where(np.isin(np.arange(len(ok_l)), order[:int(round(k * len(ok_l)))]), ok_h, ok_l).mean() for k in RATES]); ax.plot(RATES, oracle, ":", color="0.5", label="oracle (escalate L's errors first)"); curve_rows += [dict(bench=b, target=tname, signal="oracle", rate=float(k), acc=float(v)) for k, v in zip(RATES, oracle)]
            g_or = gain(oracle, a_low, a_high); rng = np.random.default_rng(a.seed); ug = np.unique(groups); idx_g = {g: np.where(groups == g)[0] for g in ug}
            boots = [np.concatenate([idx_g[g] for g in rng.choice(ug, len(ug))]) for _ in range(a.n_boot)]
            for name, (c, okl_s, ps_) in sig.items():
                conf = np.where(ps_, c, -1.0); okx = okl_s; acc_c = curve(conf, okx, ok_h); g = gain(acc_c, okx.mean(), a_high)
                gb = [gain(curve(conf[bi], okx[bi], ok_h[bi]), okx[bi].mean(), ok_h[bi].mean()) for bi in boots[:a.n_boot]]
                ax.plot(RATES, acc_c, label=f"{name}  (gain {g:+.3f})"); curve_rows += [dict(bench=b, target=tname, signal=name, rate=float(k), acc=float(v)) for k, v in zip(RATES, acc_c)]
                r = lambda f: float(acc_c[int(round(f * 50))])
                rows.append(dict(bench=b, target=tname, signal=name, L_only=okx.mean(), H_only=a_high, acc_at_10=r(.1), acc_at_20=r(.2), acc_at_30=r(.3), acc_at_50=r(.5), gain_over_random=g,
                                 gain_ci_lo=np.percentile(gb, 2.5), gain_ci_hi=np.percentile(gb, 97.5), oracle_gain=g_or, share_of_oracle=g / g_or if g_or > 0 else np.nan, n=len(ok_l)))
            ax.set_xlabel("share of items escalated to the stronger judge"); ax.set_ylabel("system accuracy"); ax.set_title(f"{b}: {a.low} -> {tname}", fontsize=9); ax.legend(fontsize=6.5, loc="lower right"); fig.tight_layout()
            fig.savefig(os.path.join(a.out, f"cascade_{b}_{tname.split(':')[0].split(' (')[0].replace(' ', '_')}.png"), dpi=130); plt.close(fig)
        tok_rows.append(dict(bench=b, probe_or_verbalized_tokens=L["n_tokens"].mean(), verbalized_run_tokens=V["n_tokens"].mean(), consistency_tokens=(L["n_tokens"].values + samp_tok).mean(), high_tokens=H["n_tokens"].mean()))
    pd.DataFrame(curve_rows).to_csv(os.path.join(a.out, "cascade_curves.csv"), index=False); R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "cascade_results.csv"), index=False); T = pd.DataFrame(tok_rows); T.to_csv(os.path.join(a.out, "tokens_per_item.csv"), index=False)
    print("\n== accuracy at escalation rates; gain over random escalation (95% question-bootstrap CI), as a share of the oracle's gain"); show = R.copy(); show["gain"] = show.apply(lambda r: f"{r.gain_over_random:+.3f} [{r.gain_ci_lo:+.3f},{r.gain_ci_hi:+.3f}]", axis=1)
    for (b, t), d in show.groupby(["bench", "target"], sort=False):
        print(f"\n{b} | L = {a.low}, escalate to: {t}   (n={d.n.iloc[0]}, L only {d.L_only.iloc[0]:.3f}, H only {d.H_only.iloc[0]:.3f}, oracle gain {d.oracle_gain.iloc[0]:+.3f})")
        print(d[["signal", "acc_at_10", "acc_at_20", "acc_at_30", "acc_at_50", "gain", "share_of_oracle"]].round(3).to_string(index=False))
    if a.seeds > 1:
        print(f"\n== probe (paper layer) over {a.seeds} seeds: share of the oracle's gain (mean +- sd over seeds)")
        sh = {(b, t): [R[(R.bench == b) & (R.target == t) & R.signal.str.startswith("probe (layer")].share_of_oracle.iloc[0]] for b in BENCH for t in ctx[b]["targets"]}
        for sd in range(1, a.seeds):
            Ps = oof_probe(a.results, a.low, a.layer, a.seed + sd, fixed_only=True)
            for b in BENCH:
                c = ctx[b]; conf = np.where(c["parsed"], Ps[b][0], -1.0); assert list(Ps[b][2]) == list(c["ids"])
                for t, ok_h in c["targets"].items():
                    order = np.argsort(c["ok_l"], kind="stable"); orc = np.array([np.where(np.isin(np.arange(len(order)), order[:int(round(k * len(order)))]), ok_h, c["ok_l"]).mean() for k in RATES])
                    go = gain(orc, c["a_low"], ok_h.mean()); sh[(b, t)].append(gain(curve(conf, c["ok_l"], ok_h), c["a_low"], ok_h.mean()) / go if go > 0 else np.nan)
        SD = pd.DataFrame([dict(bench=b, target=t[:60], mean=np.nanmean(v), sd=np.nanstd(v), seeds=len(v)) for (b, t), v in sh.items()]); print(SD.round(3).to_string(index=False)); SD.to_csv(os.path.join(a.out, "probe_seeds.csv"), index=False)
    print("\n== generated tokens per item needed to obtain each signal"); print(T.round(0).to_string(index=False))


if __name__ == "__main__":
    main()
