"""Extension of the EmbedLLM replication with ideas from IRT-Router (ACL 2025, arXiv/aclanthology 2025.acl-long.761) and
RouteLLM (ICLR 2025, arXiv 2406.18665), on our 8 judges. Same data, same 80/10/10-by-question splits as embedllm.py.

From IRT-Router (details taken from the authors' code, router/MIRT.py and test_router.py):
  * MIRT decoder:  P(judge j right on question i) = sigmoid(a_i . theta_j - b_i),  a_i = softplus(W_a q_i) (discrimination),
    b_i = w_b . q_i (difficulty),  theta_j = W_theta e_j (ability, e_j = text embedding of a judge PROFILE) -- 'profile' variant;
    'free' variant learns theta_j directly like EmbedLLM learns its judge vectors. N = 25 latent dims, BCE loss, Adam,
    lr 2e-3 (paper), batch 512, shuffled.
  * Cost-aware routing: pick argmax_j alpha * P_j - (1 - alpha) * C_j with C_j = price_j / max price; Reward = alpha * Performance
    - (1 - alpha) * normalised cost (paper Eq. 12).
From RouteLLM (authors' code, routers/matrix_factorization):
  * Binary strong-vs-weak routing evaluated with PGR / APGR / CPT against a random router; pairwise MF router trained on
    (winner, loser) pairs with L2-normalised model embeddings, bias-free classifier, noise alpha, lr 3e-4, wd 1e-5, batch 64.
Adaptations: strong judge = most accurate judge on the training questions, weak judge = the cheapest judge; a 'win' is derived from
correctness (strong right & weak wrong = strong wins; ties dropped as in their code); questions are embedded with all-mpnet-base-v2
(they use OpenAI / BERT embeddings); judge profiles are short texts written from the model names; training length is chosen
in gradient steps on the validation split because our data is tiny."""
import argparse, json, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd, torch, torch.nn as nn, torch.nn.functional as F
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels"))
from audit import match_matrix
from data import load_judgments
from embedllm import knn_models, score_matrix, train_mf, here
from splits import make_3way_splits

FRACS = np.linspace(0, 1, 11)
ALPHAS = [1.0, 0.8, 0.5, 0.2]


# ------------------------------------------------------------------ models
class TextIRT(nn.Module):
    """IRT-Router's MIRT with frozen question embeddings Q. theta_feat=None -> free ability vectors; else theta = W e_profile."""
    def __init__(self, Q, N, n_judges, theta_feat=None):
        super().__init__()
        self.Q = nn.Embedding(Q.shape[0], Q.shape[1]).requires_grad_(False); self.Q.weight.data.copy_(Q)
        self.a = nn.Linear(Q.shape[1], N, bias=False); self.b = nn.Linear(Q.shape[1], 1, bias=False)
        self.free = theta_feat is None
        if self.free:
            self.theta = nn.Embedding(n_judges, N)
        else:
            self.register_buffer("feat", theta_feat); self.theta = nn.Linear(theta_feat.shape[1], N, bias=False)

    def theta_all(self):
        return self.theta.weight if self.free else self.theta(self.feat)

    def forward(self, j, i):
        q = self.Q(i); th = self.theta_all()[j]
        return (F.softplus(self.a(q)) * th).sum(-1) - self.b(q).squeeze(-1)   # logit of P(right)

    @torch.no_grad()
    def difficulty(self, i):
        return self.b(self.Q(i)).squeeze(-1).numpy()


class PairMF(nn.Module):
    """RouteLLM's TextMF router: logit(a beats b | q) = w . ((norm(P_a) - norm(P_b)) * proj(q + noise))."""
    def __init__(self, Q, dim, alpha=0.1):
        super().__init__()
        self.P = nn.Embedding(2, dim)
        self.Q = nn.Embedding(Q.shape[0], Q.shape[1]).requires_grad_(False); self.Q.weight.data.copy_(Q)
        self.text_proj = nn.Linear(Q.shape[1], dim, bias=False); self.classifier = nn.Linear(dim, 1, bias=False); self.alpha = alpha

    def forward(self, win, loss, i, test=False):
        q = self.Q(i)
        if not test:
            q = q + torch.randn_like(q) * self.alpha
        return self.classifier((F.normalize(self.P(win), dim=1) - F.normalize(self.P(loss), dim=1)) * self.text_proj(q)).squeeze(-1)


def train_steps(net, tensors, fwd, y, lr, wd, batch, ckpts, snap, seed=42):
    """Adam on BCE-with-logits; shuffled mini-batches; calls snap(net, step) at the checkpoint steps."""
    torch.manual_seed(seed)
    opt = torch.optim.Adam([p for p in net.parameters() if p.requires_grad], lr=lr, weight_decay=wd)
    lossf = nn.BCEWithLogitsLoss(); n = len(y); step = 0; last = max(ckpts)
    while step < last:
        perm = torch.randperm(n)
        for s in range(0, n, batch):
            idx = perm[s:s + batch]
            opt.zero_grad(); lossf(fwd(net, *[t[idx] for t in tensors]), y[idx]).backward(); opt.step(); step += 1
            if step in ckpts:
                snap(net, step)
            if step >= last:
                break


def irt_logits(net, items, J):
    i = torch.tensor(np.repeat(items, J)); j = torch.tensor(np.tile(np.arange(J), len(items)))
    with torch.no_grad():
        return net(j, i).numpy().reshape(len(items), J)


# ------------------------------------------------------------------ RouteLLM-style evaluation
def pgr_curve(score, s_ok, w_ok):
    """Send the top-c fraction of questions (highest score) to the strong judge, the rest to the weak one."""
    order = np.argsort(-score, kind="stable"); n = len(score); rs, rw = s_ok.mean(), w_ok.mean(); out = []
    for c in FRACS:
        k = int(round(c * n)); perf = (s_ok[order[:k]].sum() + w_ok[order[k:]].sum()) / n
        out.append((perf - rw) / (rs - rw) if rs - rw > 1e-9 else np.nan)
    return np.array(out)


def apgr(pgr):
    return float(np.trapz(pgr, FRACS))


def cpt(pgr, x):
    for i, v in enumerate(pgr):
        if v >= x:
            return float(FRACS[0]) if i == 0 else float(FRACS[i - 1] + (x - pgr[i - 1]) / (v - pgr[i - 1]) * (FRACS[i] - FRACS[i - 1]))
    return 1.0


def sig(x):
    return 1 / (1 + np.exp(-x))


# ------------------------------------------------------------------ one repeat
def one_repeat(args):
    r, split, E, Z, Y, C, price, prof, grid = args
    torch.set_num_threads(1)
    fit, val, test = split; J = C.shape[1]; Qt = torch.tensor(E); ytest = Y[test]
    weak = int(np.argmin(price)); accf = C[fit].mean(0)
    strong = int(np.argmax(np.where(np.arange(J) == weak, -1, accf)))
    res = dict(repeat=r, weak=weak, strong=strong); curves = {}; scores = {}; P = {}

    # --- EmbedLLM MF (identical recipe to embedllm.py)
    snaps = {}; b = -(-len(fit) * J // 2048); ep_of = {-(-S // b): S for S in grid["steps"]}
    for dim in grid["dims"]:
        def snap(net, ep, dim=dim):
            Sv = score_matrix(net, val, J, True); torch.manual_seed(42)
            snaps[(dim, ep_of[ep])] = dict(vacc=((Sv > 0).astype(int) == C[val]).mean(), te=score_matrix(net, test, J, True))
        train_mf(Qt, C, fit, dim, 1e-4, max(ep_of), checkpoints=set(ep_of), snap=snap)
    bm = max(snaps, key=lambda k: snaps[k]["vacc"]); P["EmbedLLM (MF)"] = snaps[bm]["te"]; res["cfg_mf"] = f"d{bm[0]}_s{bm[1]}"

    # --- IRT-Router MIRT, two ability variants
    jj = torch.tensor(np.tile(np.arange(J), len(fit))); ii = torch.tensor(np.repeat(fit, J)); yy = torch.tensor(C[fit].reshape(-1)).float()
    feat = torch.tensor(prof)
    for mode in ("free", "profile"):
        sn = {}
        for N in grid["irt_dims"]:
            torch.manual_seed(42); net = TextIRT(Qt, N, J, None if mode == "free" else feat)
            def snap(net, st, N=N):
                sn[(N, st)] = dict(vacc=((irt_logits(net, val, J) > 0).astype(int) == C[val]).mean(), te=irt_logits(net, test, J), b=net.difficulty(torch.tensor(test)))
            train_steps(net, [jj, ii], lambda n_, j, i: n_(j, i), yy, 2e-3, 0.0, 512, set(grid["steps"]), snap)
        bi = max(sn, key=lambda k: sn[k]["vacc"]); name = f"IRT-Router ({mode} ability)"; P[name] = sn[bi]["te"]; res[f"cfg_irt_{mode}"] = f"N{bi[0]}_s{bi[1]}"
        if mode == "free":
            bdiff = sn[bi]["b"]

    # --- kNN baseline (probabilities)
    kv = {k: (knn_models(E, C, fit, val, k)[0] == C[val]).mean() for k in grid["ks"]}; kb = max(kv, key=kv.get)
    kp, kprob = knn_models(E, C, fit, test, kb)
    const = np.tile((C[fit].mean(0) >= 0.5).astype(int), (len(test), 1))
    res["acc_const"] = (const == C[test]).mean(); res["acc_knn"] = (kp == C[test]).mean()
    flat = C[test].reshape(-1); aucf = lambda s: roc_auc_score(flat, s.reshape(-1)) if len(set(flat)) > 1 else np.nan
    res["auc_knn"] = aucf(kprob)
    for name, S in P.items():
        k = {"EmbedLLM (MF)": "mf", "IRT-Router (free ability)": "irt_free", "IRT-Router (profile ability)": "irt_profile"}[name]
        res[f"acc_{k}"] = ((S > 0).astype(int) == C[test]).mean(); res[f"auc_{k}"] = aucf(S)

    # --- interpretability (IRT-Router Figures 4-5 idea)
    Sfree = P["IRT-Router (free ability)"]; mean_ok = C[test].mean(1)
    res["rho_ability"] = spearmanr(Sfree.mean(0), C[test].mean(0)).correlation
    res["rho_difficulty_irt"] = spearmanr(bdiff, 1 - mean_ok).correlation
    res["rho_difficulty_mf"] = spearmanr(-P["EmbedLLM (MF)"].mean(1), 1 - mean_ok).correlation

    # --- RouteLLM-style pairwise MF on (strong, weak) comparisons derived from correctness
    dis = fit[C[fit, strong] != C[fit, weak]]; vdis = val[C[val, strong] != C[val, weak]]
    if len(dis) >= 4:
        win = torch.tensor(np.where(C[dis, strong] == 1, 1, 0)); los = 1 - win; di = torch.tensor(dis)
        ones = torch.ones(len(dis)); ps = {}
        for dim in grid["pair_dims"]:
            torch.manual_seed(42); net = PairMF(Qt, dim)
            def snap(net, st, dim=dim):
                vacc = 0.0
                if len(vdis):
                    lg = net(torch.ones(len(vdis), dtype=torch.long), torch.zeros(len(vdis), dtype=torch.long), torch.tensor(vdis), test=True).detach().numpy()
                    vacc = ((lg > 0) == (C[vdis, strong] == 1)).mean()
                cp = PairMF(Qt, dim); cp.load_state_dict(net.state_dict()); ps[(dim, st)] = dict(vacc=vacc, net=cp)
            train_steps(net, [win, los, di], lambda n_, w, l, i: n_(w, l, i), ones, 3e-4, 1e-5, 64, set(grid["steps"]), snap)
        bp = max(ps, key=lambda k: ps[k]["vacc"]); pn = ps[bp]["net"]; res["cfg_pair"] = f"d{bp[0]}_s{bp[1]}"
        with torch.no_grad():
            scores["RouteLLM MF (pairwise)"] = pn(torch.ones(len(test), dtype=torch.long), torch.zeros(len(test), dtype=torch.long), torch.tensor(test), test=True).numpy()
    # --- scores (higher -> send to the strong judge)
    s_ok, w_ok = C[test, strong], C[test, weak]
    for name, S in P.items():
        scores[name] = sig(S[:, strong]) - sig(S[:, weak])
    scores["IRT-Router difficulty b"] = bdiff
    scores["kNN"] = kprob[:, strong] - kprob[:, weak]
    scores["random"] = np.random.default_rng(r).random(len(test)); scores["oracle"] = s_ok.astype(float) - w_ok
    for name, s in scores.items():
        c = pgr_curve(s, s_ok, w_ok); curves[name] = c
        res[f"apgr|{name}"] = apgr(c); res[f"cpt50|{name}"] = cpt(c, 0.5); res[f"cpt80|{name}"] = cpt(c, 0.8); res[f"cpt90|{name}"] = cpt(c, 0.9)
    res["r_weak"], res["r_strong"] = float(w_ok.mean()), float(s_ok.mean())

    # --- IRT-Router cost-aware routing score
    Cn = price / price.max(); rows = []
    accfit = C[fit].mean(0); top3 = np.argsort(-accfit)[:3]
    for a in ALPHAS:
        for name, S in P.items():
            ch = np.argmax(a * sig(S) - (1 - a) * Cn[None, :], axis=1)
            perf = C[test][np.arange(len(test)), ch].mean(); cost = price[ch].mean(); rows.append((name, a, perf, cost, a * perf - (1 - a) * Cn[ch].mean()))
        for name, js in (("small judge (cheapest)", [weak]), ("large judge (best single)", [int(np.argmax(accfit))]), ("static top-3 vote", list(top3))):
            perf = C[test][:, js[0]].mean() if len(js) == 1 else ((Z[test][:, js].mean(1) > 0.5).astype(int) == ytest).mean()
            rows.append((name, a, perf, price[js].sum(), a * perf - (1 - a) * Cn[js].sum()))
    res["cost_rows"] = rows; res["curves"] = curves
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bff", required=True); ap.add_argument("--rb2", required=True)
    ap.add_argument("--settings", nargs="*", default=["bff_none", "bff_human", "rb2"]); ap.add_argument("--variant", default="q")
    ap.add_argument("--n-repeats", type=int, default=10); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dims", type=int, nargs="*", default=[8, 232]); ap.add_argument("--irt-dims", type=int, nargs="*", default=[8, 25])
    ap.add_argument("--pair-dims", type=int, nargs="*", default=[8, 128]); ap.add_argument("--steps", type=int, nargs="*", default=[200, 1000, 3000])
    ap.add_argument("--ks", type=int, nargs="*", default=[5, 15, 31, 65, 131]); ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args(); pd.set_option("display.width", 220)
    cfg = {"bff_none": ("BFF no reference", a.bff, "bff", "none", "bff"), "bff_human": ("BFF reference given", a.bff, "bff", "human", "bff"),
           "rb2": ("RewardBench-2 Safety", a.rb2, "rb2safety", "none", "rb2safety")}
    grid = dict(dims=a.dims, irt_dims=a.irt_dims, pair_dims=a.pair_dims, steps=a.steps, ks=a.ks)
    prof_all = np.load(os.path.join(here, "data_cache", "judge_profiles_mpnet.npy"))
    os.makedirs(os.path.join(here, "results", "embedllm"), exist_ok=True)
    for key in a.settings:
        label, path, bench, cond, ek = cfg[key]
        d = load_judgments(path, bench, condition=cond)
        E_all = np.load(os.path.join(here, "data_cache", f"mpnet_{ek}_{a.variant}.npy"))
        ids = pd.read_parquet(os.path.join(here, "data_cache", f"mpnet_{ek}_{a.variant}_ids.parquet")).item_id.tolist()
        pos = {i: k for k, i in enumerate(ids)}; E = E_all[[pos[i] for i in d.item_ids]]
        C = match_matrix(d.Z, d.Y).astype(int); price = np.array([d.cost[j] for j in d.judge_names])
        splits = make_3way_splits(d.groups, a.seed, a.n_repeats, frac=(0.8, 0.1, 0.1))
        with Pool(a.procs) as pool:
            outs = pool.map(one_repeat, [(r, sp, E, d.Z, d.Y, C, price, prof_all, grid) for r, sp in enumerate(splits)], chunksize=1)
        R = pd.DataFrame([{k: v for k, v in o.items() if k not in ("cost_rows", "curves")} for o in outs]); names = d.judge_names
        print(f"\n################ {label} [{a.variant}]  ({a.n_repeats} splits; strong = most accurate on training questions, weak = cheapest judge {names[int(R.weak.iloc[0])]})", flush=True)
        print("strong judge per split:", {names[k]: int(v) for k, v in R.strong.value_counts().items()}, f"| weak judge accuracy {R.r_weak.mean():.3f}, strong {R.r_strong.mean():.3f}")
        print("\n(1) Predicting whether a judge is right (mean accuracy; AUROC) -- EmbedLLM decoder vs IRT-Router decoder:")
        T = pd.DataFrame({"accuracy": [R.acc_const.mean(), R.acc_knn.mean(), R.acc_mf.mean(), R.acc_irt_free.mean(), R.acc_irt_profile.mean()],
                          "AUROC": [0.5, R.auc_knn.mean(), R.auc_mf.mean(), R.auc_irt_free.mean(), R.auc_irt_profile.mean()]},
                         index=["constant", "kNN", "EmbedLLM (MF)", "IRT-Router (free ability)", "IRT-Router (profile ability)"]); print(T.round(4).to_string())
        print("\n(2) Interpretability (Spearman, mean over splits): judge ability vs judge accuracy %+.2f | item difficulty vs share of judges wrong: IRT b %+.2f, MF-implied %+.2f"
              % (R.rho_ability.mean(), R.rho_difficulty_irt.mean(), R.rho_difficulty_mf.mean()))
        print("\n(3) IRT-Router cost-aware routing: alpha * P(right) - (1-alpha) * normalised price. Performance = verdict accuracy; cost = $/item; reward = alpha*perf - (1-alpha)*normalised cost")
        cr = pd.DataFrame([row for o in outs for row in o["cost_rows"]], columns=["strategy", "alpha", "performance", "cost_$", "reward"])
        print(cr.groupby(["alpha", "strategy"], sort=False)[["performance", "cost_$", "reward"]].mean().round(4).to_string())
        print("\n(4) RouteLLM-style strong-vs-weak routing: APGR (area under PGR vs share of strong calls; random = 0.5, higher is better) and CPT = share of strong calls needed for 50/80/90% of the gap")
        srcs = ["EmbedLLM (MF)", "IRT-Router (free ability)", "IRT-Router (profile ability)", "IRT-Router difficulty b", "RouteLLM MF (pairwise)", "kNN", "random", "oracle"]
        rows4 = [(s, R[f"apgr|{s}"].mean(), R[f"cpt50|{s}"].mean(), R[f"cpt80|{s}"].mean(), R[f"cpt90|{s}"].mean()) for s in srcs if f"apgr|{s}" in R]
        print(pd.DataFrame(rows4, columns=["router score", "APGR", "CPT(50%)", "CPT(80%)", "CPT(90%)"]).round(3).to_string(index=False), flush=True)
        R.to_csv(os.path.join(here, "results", "embedllm", f"ext_{key}_{a.variant}.csv"), index=False)
        try:
            import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6.5, 4.8))
            for s in ["EmbedLLM (MF)", "IRT-Router (free ability)", "RouteLLM MF (pairwise)", "kNN", "random"]:
                cs = np.nanmean([o["curves"][s] for o in outs if s in o["curves"]], axis=0); ax.plot(FRACS * 100, cs * 100, marker="o", ms=3, label=s)
            ax.set_xlabel("% of questions sent to the strong judge"); ax.set_ylabel("% of the weak-to-strong accuracy gap recovered"); ax.legend(fontsize=8)
            ax.set_title(f"{label}: strong vs weak routing"); fig.tight_layout(); fig.savefig(os.path.join(here, "results", "embedllm", f"ext_curve_{key}_{a.variant}.png"), dpi=120); plt.close(fig)
        except Exception as e:
            print("plot failed:", e)


if __name__ == "__main__":
    main()
