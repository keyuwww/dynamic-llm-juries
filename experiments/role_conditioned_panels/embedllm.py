"""EmbedLLM (Zhuang et al., arXiv 2410.02223) replicated on the judge pool.

Faithful to the authors' released code (github.com/richardzhuang0412/EmbedLLM, algorithm/mf.py, knn.py):
  * TextMF: P = trainable nn.Embedding(n_models, dim); Q = FROZEN precomputed question embeddings;
    text_proj = Linear(768, dim); forward adds Gaussian noise alpha*N(0,1) to Q in training only (alpha = 0.05);
    logits = Linear(dim, 2)(P(model) * text_proj(Q(prompt))); loss = cross-entropy; predict = argmax.
  * Adam, lr 1e-4, weight decay 1e-5, batch 2048, 50 epochs, shuffle=False, seed 42. Default dim 232.
  * Question embedding: all-mpnet-base-v2, not normalized by us, prompt text only (variant "q").
  * Router: per question pick the model with the highest logit(correct) - logit(incorrect); report route accuracy,
    single-best-model accuracy (best model accuracy on the evaluated set) and the weighted-random baseline
    sum_j share_j * acc_j. The released router evaluation leaves the training noise ON; we report it both ways.
  * KNN baseline: one sklearn KNeighborsClassifier per model on the question embeddings (Euclidean, majority vote).
Adaptations forced by our data (judges = models, judged items = questions), all marked in the output:
  * 8 "models" x ~460 items (80 questions) instead of 112 x 36,054, so 50 epochs of batch 2048 is ~100 gradient steps.
    We report the literal configuration AND the same recipe (lr 1e-4, wd 1e-5, alpha 0.05, batch 2048) trained longer,
    with only the embedding dim (the paper tunes it on validation) and the number of epochs chosen on validation.
  * Splits are 80/10/10 like the paper but by QUESTION (several responses share a question); 20 random repeats.
  * The "question" for a judge is the thing it judges, so variant "qr" also embeds the response; "q" is the literal one.
The target is the judge-correctness matrix (verdict == gold), built in audit.py."""
import argparse, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
import torch, torch.nn as nn
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import KNeighborsClassifier
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import match_matrix                      # the correctness matrix is the TARGET here, by design
from data import load_judgments
from evaluate import pooled_bootstrap
from splits import make_3way_splits

here = os.path.dirname(os.path.abspath(__file__))


class TextMF(nn.Module):
    def __init__(self, dim, n_models, Q, alpha=0.05):
        super().__init__()
        self.P = nn.Embedding(n_models, dim)
        self.Q = nn.Embedding(Q.shape[0], Q.shape[1]).requires_grad_(False)
        self.Q.weight.data.copy_(Q)
        self.alpha = alpha
        self.text_proj = nn.Linear(Q.shape[1], dim)
        self.classifier = nn.Linear(dim, 2)

    def forward(self, model, prompt, test_mode=False):
        p, q = self.P(model), self.Q(prompt)
        if not test_mode:
            q = q + torch.randn_like(q) * self.alpha
        return self.classifier(p * self.text_proj(q))

    @torch.no_grad()
    def score(self, model, prompt, test_mode=True):
        l = self(model, prompt, test_mode=test_mode)
        return (l[:, 1] - l[:, 0]).numpy()


def pairs(items, J):
    m = np.tile(np.arange(J), len(items)); p = np.repeat(items, J)       # item-major order, as one CSV row per pair
    return torch.tensor(m), torch.tensor(p)


def train_mf(Q, C, tr_items, dim, lr, epochs, alpha=0.05, batch=2048, seed=42, checkpoints=(), snap=None):
    """Train exactly like the released code. If `checkpoints` is given, call snap(net, epoch) after those epochs
    (the training RNG state is saved/restored around snap so the trajectory equals an uninterrupted run)."""
    torch.manual_seed(seed); np.random.seed(seed)
    J = C.shape[1]; net = TextMF(dim, J, Q, alpha)
    opt = torch.optim.Adam([p for p in net.parameters() if p.requires_grad], lr=lr, weight_decay=1e-5)
    m, p = pairs(tr_items, J); y = torch.tensor(C[tr_items].reshape(-1)).long(); lossf = nn.CrossEntropyLoss()
    for ep in range(1, epochs + 1):
        for s in range(0, len(y), batch):                              # shuffle=False, as in the released code
            opt.zero_grad(); loss = lossf(net(m[s:s + batch], p[s:s + batch]), y[s:s + batch]); loss.backward(); opt.step()
        if ep in checkpoints:
            st = torch.get_rng_state(); snap(net, ep); torch.set_rng_state(st)
    return net


def score_matrix(net, items, J, test_mode=True):
    m, p = pairs(items, J)
    return net.score(m, p, test_mode).reshape(len(items), J)


def knn_models(E, C, tr, te, k):
    """One KNeighborsClassifier per model (Euclidean, uniform majority vote). Returns hard predictions and P(correct)."""
    pred, prob = np.zeros((len(te), C.shape[1]), int), np.zeros((len(te), C.shape[1]))
    for j in range(C.shape[1]):
        y = C[tr, j]
        if len(set(y)) < 2:
            pred[:, j] = y[0]; prob[:, j] = float(y[0]); continue
        nb = KNeighborsClassifier(n_neighbors=min(k, len(tr))).fit(E[tr], y)
        pred[:, j] = nb.predict(E[te]); prob[:, j] = nb.predict_proba(E[te])[:, 1]
    return pred, prob


def one_repeat(args):
    r, split, E, Z, Y, C, grid = args
    torch.set_num_threads(1)
    fit, val, test = split; J = C.shape[1]; Qt = torch.tensor(E)
    snaps = {}                                                          # (dim, epochs) -> val acc, test scores noise off/on
    for dim in grid["dims"]:
        def snap(net, ep, dim=dim):
            Sv = score_matrix(net, val, J, True)
            torch.manual_seed(42)
            snaps[(dim, ep)] = dict(vacc=((Sv > 0).astype(int) == C[val]).mean(), off=score_matrix(net, test, J, True),
                                    on=score_matrix(net, test, J, False))
        train_mf(Qt, C, fit, dim, 1e-4, max(grid["epochs"]), checkpoints=set(grid["epochs"]), snap=snap)
    best = max([k for k in snaps if k != (232, 50)], key=lambda k: snaps[k]["vacc"])
    cfgs = {"literal": (232, 50), "tuned": best}
    vacc = {k: v["vacc"] for k, v in snaps.items()}
    knn_val = {k: (knn_models(E, C, fit, val, k)[0] == C[val]).mean() for k in grid["ks"]}
    kbest = max(knn_val, key=knn_val.get)
    acc_tr = C[fit].mean(0); best_tr = int(acc_tr.argmax()); top3 = [int(j) for j in np.argsort(-acc_tr, kind="stable")[:3]]
    const = np.tile((C[fit].mean(0) >= 0.5).astype(int), (len(test), 1))
    res = dict(repeat=r, best_cfg=f"d{best[0]}_e{best[1]}", kbest=kbest, n_test=len(test))
    res["acc_const"] = (const == C[test]).mean()
    kp, kpr = knn_models(E, C, fit, test, kbest); res["acc_knn_tuned"] = (kp == C[test]).mean()
    kp131, _ = knn_models(E, C, fit, test, 131); res["acc_knn131"] = (kp131 == C[test]).mean()
    res["auc_knn_tuned"] = roc_auc_score(C[test].reshape(-1), kpr.reshape(-1)) if len(set(C[test].reshape(-1))) > 1 else np.nan
    pooled = {}
    def route(S, name):
        ch = S.argmax(1); pooled[name] = (test, C[test][np.arange(len(test)), ch].astype(int))
    for tag in ("literal", "tuned"):
        sn = snaps[cfgs[tag]]; S0 = sn["off"]
        res[f"acc_mf_{tag}"] = ((S0 > 0).astype(int) == C[test]).mean()
        res[f"auc_mf_{tag}"] = roc_auc_score(C[test].reshape(-1), S0.reshape(-1)) if len(set(C[test].reshape(-1))) > 1 else np.nan
        route(S0, f"mf_{tag}_route_noise_off")
        route(sn["on"], f"mf_{tag}_route_noise_on")                    # released-code behaviour: noise left on at routing
        if tag == "tuned":
            top3_mf = np.argsort(-S0, axis=1)[:, :3]
            vote = (np.take_along_axis(Z[test], top3_mf, 1).mean(1) > 0.5).astype(int)
            pooled["mf_tuned_top3_majority"] = (test, (vote == Y[test]).astype(int))
            sh = np.bincount(S0.argmax(1), minlength=J) / len(test); res["weighted_random"] = float((sh * C[test].mean(0)).sum())
            res["weighted_random_shares_top"] = int(S0.argmax(1).max() == S0.argmax(1).min())
    res["single_best_test_determined"] = float(C[test].mean(0).max())            # the paper's single-best router
    pooled["single_best_train_determined"] = (test, C[test][:, best_tr].astype(int))
    pooled["static_top3_majority"] = (test, ((Z[test][:, top3].mean(1) > 0.5).astype(int) == Y[test]).astype(int))
    pooled["single_best_test_determined"] = (test, C[test][:, int(C[test].mean(0).argmax())].astype(int))
    for k, (te, c) in pooled.items():
        res["route_" + k] = c.mean()
    return res, pooled


def run_setting(label, d, E, args):
    Z, Y = d.Z, d.Y; C = match_matrix(Z, Y).astype(int)
    splits = make_3way_splits(d.groups, args.seed, args.n_repeats, frac=(0.8, 0.1, 0.1))
    grid = dict(dims=args.dims, epochs=args.epochs, ks=args.ks)
    jobs = [(r, sp, E, Z, Y, C, grid) for r, sp in enumerate(splits)]
    with Pool(args.procs) as pool:
        outs = pool.map(one_repeat, jobs)
    R = pd.DataFrame([o[0] for o in outs]); pooled = {}
    for _, pl in outs:
        for k, (te, c) in pl.items():
            pooled.setdefault(k, []).append((te, c))
    print(f"\n################ {label}: {len(Y)} items, {d.groups.max() + 1} questions, 20 repeats of 80/10/10 by question")
    print("Correctness forecasting on unseen questions (mean per-model accuracy, test):")
    cols = [("constant (each judge's majority label)", "acc_const"), ("KNN, k tuned on val", "acc_knn_tuned"), ("KNN, k=131 (paper's)", "acc_knn131"),
            ("MF literal (dim 232, 50 epochs)", "acc_mf_literal"), ("MF same recipe, dim/epochs tuned on val", "acc_mf_tuned")]
    print(pd.DataFrame({"model": [c[0] for c in cols], "acc": [R[c[1]].mean() for c in cols], "sd": [R[c[1]].std() for c in cols]}).round(4).to_string(index=False))
    print(f"AUROC (pooled over judges): MF tuned {R.auc_mf_tuned.mean():.3f} | MF literal {R.auc_mf_literal.mean():.3f} | KNN tuned {R.auc_knn_tuned.mean():.3f}   (0.5 = chance)")
    print("MF tuned config chosen on val (count):", R.best_cfg.value_counts().to_dict(), "| KNN k:", R.kbest.value_counts().to_dict())
    G = d.groups.max() + 1
    print("Routing: route accuracy = share of test questions where the routed judge's verdict is correct:")
    names = ["mf_literal_route_noise_off", "mf_literal_route_noise_on", "mf_tuned_route_noise_off", "mf_tuned_route_noise_on",
             "mf_tuned_top3_majority", "single_best_train_determined", "single_best_test_determined", "static_top3_majority"]
    rows = [(n, R["route_" + n].mean(), R["route_" + n].std()) for n in names] + [("weighted_random (paper baseline, MF tuned shares)", R.weighted_random.mean(), R.weighted_random.std())]
    print(pd.DataFrame(rows, columns=["router", "acc", "sd"]).round(4).to_string(index=False))
    for a_, b_ in (("mf_tuned_route_noise_off", "single_best_train_determined"), ("mf_tuned_route_noise_off", "static_top3_majority"),
                   ("mf_literal_route_noise_off", "single_best_train_determined")):
        b = pooled_bootstrap(pooled, d.groups, a_, b_)
        print(f"  {a_} minus {b_}: {b['diff']:+.4f}  95% CI [{b['lo']:+.4f}, {b['hi']:+.4f}]")
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bff", required=True); ap.add_argument("--rb2", required=True)
    ap.add_argument("--variant", default="q", choices=["q", "qr"]); ap.add_argument("--settings", nargs="*", default=["bff_none", "bff_human", "rb2"])
    ap.add_argument("--n-repeats", type=int, default=20); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dims", type=int, nargs="*", default=[8, 232]); ap.add_argument("--epochs", type=int, nargs="*", default=[50, 200, 500, 1000, 2000])
    ap.add_argument("--ks", type=int, nargs="*", default=[5, 15, 31, 65, 131])
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args(); pd.set_option("display.width", 200)
    cfg = {"bff_none": ("BFF no reference", a.bff, "bff", "none", "bff"), "bff_human": ("BFF reference given", a.bff, "bff", "human", "bff"),
           "rb2": ("RewardBench-2 Safety", a.rb2, "rb2safety", "none", "rb2safety")}
    print(f"EmbedLLM replication, question text variant = {a.variant!r} ({'prompt only, as in the paper' if a.variant == 'q' else 'prompt + response'})")
    for key in a.settings:
        label, path, bench, cond, ek = cfg[key]
        d = load_judgments(path, bench, condition=cond)
        E_all = np.load(os.path.join(here, "data_cache", f"mpnet_{ek}_{a.variant}.npy"))
        ids = pd.read_parquet(os.path.join(here, "data_cache", f"mpnet_{ek}_{a.variant}_ids.parquet")).item_id.tolist()
        pos = {i: k for k, i in enumerate(ids)}; E = E_all[[pos[i] for i in d.item_ids]]
        run_setting(f"{label} [{a.variant}]", d, E, a)


if __name__ == "__main__":
    main()
