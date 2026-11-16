#!/usr/bin/env python
"""One probe trained on both targets: 'is the verdict right?' and 'the judge's belief' (share of its 7 own solves reaching the candidate's answer).

Per saved layer: standardised activations -> shared linear map to 32 numbers -> two heads: correctness (logistic, all training items) and belief
(regression, only BFF training items that have a belief value). Loss = cross-entropy(correctness) + 1.0 * squared error(belief, where available);
Adam, lr 1e-3, weight decay 1e-3, 400 full-batch steps, fixed before running. Escalation score = correctness head, averaged over layers.
Compared with P = the better probe (logistic regression per layer, averaged), same pooled training over the three benchmarks, same 5-fold splits by
question, 3 seeds. BFF scored, accuracy with 10/20/30% escalated, unfinished answers first. Pre-registered pass bar: the two-target probe beats P at
20% with the 95% paired bootstrap CI above 0 for at least 1 of the 2 judges. Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, warnings
import numpy as np, pandas as pd, torch
from cascade_eval import gen, load_run, BENCH
from combo_probe import probe
warnings.filterwarnings("ignore")


def mt_layer(Xtr, ytr, btr, bmask, Xte, seed, k=32, steps=400):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6; Xtr = torch.tensor((Xtr - mu) / sd); Xte = torch.tensor((Xte - mu) / sd)
    torch.manual_seed(seed); W = torch.nn.Linear(Xtr.shape[1], k); hc = torch.nn.Linear(k, 1); hb = torch.nn.Linear(k, 1)
    opt = torch.optim.Adam(list(W.parameters()) + list(hc.parameters()) + list(hb.parameters()), lr=1e-3, weight_decay=1e-3)
    y = torch.tensor(ytr, dtype=torch.float32); b = torch.tensor(btr, dtype=torch.float32); m = torch.tensor(bmask, dtype=torch.float32)
    for _ in range(steps):
        z = W(Xtr); lc = torch.nn.functional.binary_cross_entropy_with_logits(hc(z)[:, 0], y)
        lb = ((torch.sigmoid(hb(z)[:, 0]) - b) ** 2 * m).sum() / m.sum().clamp(min=1); loss = lc + 1.0 * lb
        opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        return torch.sigmoid(hc(W(Xte))[:, 0]).numpy()


def esc_acc(trust, ol, oh, fin, tie, rate=0.2):
    n = len(ol); m = int(round(rate * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True
    return np.where(e, oh, ol).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True); ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json")
    ap.add_argument("--belief", default="targets/belief_rows_clean.json"); ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_multitask")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); torch.set_num_threads(a.threads); TG = json.load(open(a.targets)); j = a.judge
    BR = pd.DataFrame(json.load(open(a.belief))); BR = BR[(BR.bench == "bff") & (BR.judge == j.lower())].drop_duplicates("item").set_index("item")
    A, Y, G, B, FIN, IDS = [], [], [], [], [], []
    for b in BENCH:
        _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"]); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]
        A.append(np.load(f"{p}_acts.npy").astype(np.float32)); Y.append(L["correct"].values.astype(int)); FIN.append(L["verdict"].notna().values)
        G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(ids); IDS += ids
    A = np.concatenate(A); Y = np.concatenate(Y); FIN = np.concatenate(FIN); G = np.array(G); B = np.array(B); IDS = np.array(IDS); n = len(Y); nl = A.shape[1]
    BEL = np.array([float(BR.loc[i, "belief"]) if (b_ == "bff" and i in BR.index) else 0.0 for i, b_ in zip(IDS, B)]); HAS = np.array([b_ == "bff" and i in BR.index for i, b_ in zip(IDS, B)], dtype=float)
    SC = {v: np.zeros((a.seeds, n)) for v in ["P", "two-target"]}
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        for k in range(5):
            te, tr = np.where(f == k)[0], np.where(f != k)[0]
            SC["P"][seed, te] = probe(A, Y, tr, te, a.threads)
            SC["two-target"][seed, te] = np.mean([mt_layer(A[tr, l], Y[tr], BEL[tr], HAS[tr], A[te, l], seed * 100 + k * 10 + l) for l in range(nl)], 0)
            print(f"{j} seed {seed} fold {k} done", flush=True)
    m = B == "bff"; ol, fin, g = Y[m], FIN[m], G[m]; oh = np.array([TG[j]["bff"][i] for i in IDS[m]]); nb = m.sum(); tie = np.random.default_rng(12345).random(nb)
    def scores(idx, rate=0.2):
        o, h, fi, t = ol[idx], oh[idx], fin[idx], tie[idx]; return {v: np.mean([esc_acc(SC[v][s, m][idx], o, h, fi, t, rate) for s in range(a.seeds)]) for v in SC}
    rows = []
    for rate in [0.1, 0.2, 0.3]:
        full = scores(np.arange(nb), rate); row = dict(judge=j, escalated=int(rate * 100), **{k_: v_ * 100 for k_, v_ in full.items()})
        if rate == 0.2:
            gi = {x: np.where(g == x)[0] for x in np.unique(g)}; ugs = np.array(list(gi)); rb = np.random.default_rng(7)
            D = np.array([(lambda s_: s_["two-target"] - s_["P"])(scores(np.concatenate([gi[x] for x in rb.choice(ugs, len(ugs))]))) for _ in range(a.n_boot)]) * 100
            row["two_target_minus_P"] = f"{(full['two-target'] - full['P'])*100:+.1f} [{np.percentile(D, 2.5):+.1f},{np.percentile(D, 97.5):+.1f}]"
        rows.append(row)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, f"multitask_{j}.csv"), index=False); pd.set_option("display.width", 220); print(R.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
