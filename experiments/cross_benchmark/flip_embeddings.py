"""C3: semantic controls and text-only flip prediction (stored verdicts + a local embedding model, no LLM calls).

Embeds question, answer A and answer B with sentence-transformers/all-MiniLM-L6-v2 (cached in data/emb_<bench>.npz).
1. Semantic controls: cos(A,B), cos(A,q), cos(B,q), |cos(A,q) - cos(B,q)|. Do they explain the flip signal?
   (correlation with flip count; AUROC gain of flips over lexical + semantic controls)
2. Can flips be predicted from text alone? Ridge regression of the others' flip count on [q, |A-B|, A*B] embeddings
   (grouped CV). If predicted flips catch the best judge's errors as well as real flips, the checker calls are
   unnecessary.
Usage: python flip_embeddings.py -> results/flips/c3_embeddings.md
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from flip_analysis import boot_auc, boot_gain, cv_pred, load  # noqa: E402
from order_consistency import auroc  # noqa: E402

OUT = HERE / "results" / "flips"
BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]


def embed(bench, idx):
    p = HERE / "data" / f"emb_{bench}.npz"
    it = pd.read_pickle(HERE / "data" / f"{bench}_items.pkl")
    it = it[it.order == 0].drop_duplicates("pair_id").set_index("pair_id").loc[idx]
    if p.exists():
        z = np.load(p, allow_pickle=True)
        if list(z["ids"]) == list(idx):
            return z["q"], z["a"], z["b"]
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    enc = lambda s: m.encode([str(x)[:4000] for x in s], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    q, a, b = enc(it.question), enc(it.resp_a), enc(it.resp_b)
    np.savez(p, ids=np.array(list(idx), dtype=object), q=q, a=a, b=b)
    return q, a, b


def grouped_ridge(X, y, g, alpha=10.0):
    ug = np.unique(g)
    fold = dict(zip(np.random.default_rng(0).permutation(ug), np.arange(len(ug)) % 5))
    f = np.array([fold[x] for x in g])
    p = np.zeros(len(y))
    for k in range(5):
        tr, te = f != k, f == k
        p[te] = Ridge(alpha=alpha).fit(X[tr], y[tr]).predict(X[te])
    return p


def main():
    L = ["# C3: semantic controls and text-only flip prediction", "",
         "Embeddings: all-MiniLM-L6-v2 on question, answer A, answer B. Target and outcome as in Stage A "
         "(best judge's confident errors on its consistent pairs). AUROC with 95% bootstrap CI over questions.", ""]
    for bench in BENCHES:
        df, target, J = load(bench)
        F = pd.read_csv(OUT / f"features_{bench}.csv", index_col=0).loc[df.index]
        q, a, b = embed(bench, df.index)
        S = pd.DataFrame({"cos_ab": (a * b).sum(1), "cos_aq": (a * q).sum(1), "cos_bq": (b * q).sum(1)}, index=df.index)
        S["rel_gap"] = (S.cos_aq - S.cos_bq).abs()
        cons = (df.t_flip == 0).values
        y = df.t_conf_err.values[cons].astype(int)
        g = F.group.values[cons]
        lex = [c for c in F.columns if c not in ("group", "category")]
        Xl = pd.get_dummies(F[lex + ["category"]], columns=["category"], drop_first=True).values.astype(float)
        Xs = np.c_[Xl, S.values]
        p_ls = cv_pred(Xs[cons], y, g)
        p_lsf = cv_pred(np.c_[Xs, df.n_flip.values][cons], y, g)
        corr = {c: float(np.corrcoef(df.n_flip, S[c])[0, 1]) for c in S.columns}
        # text-only flip prediction (trained on all pairs, scored on consistent ones)
        X_emb = np.c_[q, np.abs(a - b), a * b]
        pred_flip = grouped_ridge(X_emb, df.n_flip.values.astype(float), F.group.values)
        r_pred = float(np.corrcoef(pred_flip, df.n_flip)[0, 1])
        L += [f"## {bench} (best judge {target})", "",
              "| Signal | AUROC |", "|---|---|",
              f"| Semantic similarity cos(A,B) alone | {auroc(y, -S.cos_ab.values[cons]):.2f} |",
              f"| Lexical + semantic controls | {boot_auc(y, p_ls, g)[0]:.2f} [{boot_auc(y, p_ls, g)[1]:.2f}, {boot_auc(y, p_ls, g)[2]:.2f}] |",
              f"| Controls + real flips | {boot_auc(y, p_lsf, g)[0]:.2f} |",
              f"| Real flip count | {boot_auc(y, df.n_flip.values[cons].astype(float), g)[0]:.2f} |",
              f"| Flip count predicted from text only | {boot_auc(y, pred_flip[cons], g)[0]:.2f} |", "",
              f"- Gain from real flips over lexical + semantic controls: "
              f"{'{:.2f} [{:.2f}, {:.2f}]'.format(*boot_gain(y, p_ls, p_lsf, g))}.",
              "- Correlation of flip count with semantic features: " + ", ".join(f"{k} {v:+.2f}" for k, v in corr.items()) + ".",
              f"- Text-only prediction of the flip count: r = {r_pred:.2f} with the real count (grouped CV).", ""]
    (OUT / "c3_embeddings.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
