"""The paper's one pooled estimand: equal-weight mean over the observed judge-benchmark pairs, with a synchronised
question bootstrap (questions resampled within benchmark; every judge and every method gets the same resampled
multiplicities, so dependence between judges that share questions is kept).

  pairs = {(judge, bench): {name: (qids, array[n_questions, k])}}   per-question sums (e.g. AUROC numerator/denominator)
  stats = {key: f(T) -> float | None}, T = {name: summed vector over the (resampled) questions} for one pair
  boot(pairs, stats) -> {key: dict(g, lo, hi, k)}, draws {key: array[n]}
"""
import numpy as np


def boot(pairs, stats, n=2000, seed=0):
    benches = sorted({b for _, b in pairs})
    uni = {b: sorted({q for (_, bb), d in pairs.items() if bb == b for qs, _ in d.values() for q in qs}) for b in benches}
    pos = {b: {q: i for i, q in enumerate(u)} for b, u in uni.items()}
    idx = {(p, name): np.array([pos[p[1]][q] for q in qs], int) for p, d in pairs.items() for name, (qs, _) in d.items()}
    rng = np.random.default_rng(seed)
    est, draws, kk = {}, {k: [] for k in stats}, {}
    for it in range(n + 1):
        W = {b: np.ones(len(u)) if it == 0 else rng.multinomial(len(u), np.full(len(u), 1 / len(u))).astype(float)
             for b, u in uni.items()}
        per = {k: [] for k in stats}
        for p, d in pairs.items():
            T = {name: W[p[1]][idx[(p, name)]] @ arr for name, (_, arr) in d.items()}
            for k, f in stats.items():
                v = f(T)
                if v is not None and np.isfinite(v):
                    per[k].append(v)
        for k in stats:
            m = float(np.mean(per[k])) if per[k] else np.nan
            if it == 0:
                est[k], kk[k] = m, len(per[k])
            else:
                draws[k].append(m)
    out = {}
    for k in stats:
        d = np.array(draws[k])
        d = d[np.isfinite(d)]
        out[k] = dict(g=est[k], lo=float(np.percentile(d, 2.5)), hi=float(np.percentile(d, 97.5)), k=kk[k]) if len(d) else None
        draws[k] = np.array(draws[k])
    return out, draws


def ratio(draws, num, den, est):
    """ratio of two pooled means with a percentile interval from the same draws."""
    r = draws[num] / draws[den]
    r = r[np.isfinite(r)]
    return dict(g=est[num]["g"] / est[den]["g"], lo=float(np.percentile(r, 2.5)), hi=float(np.percentile(r, 97.5)))


def auc_gain(m, base="verdict", col=(0, 1)):
    """100 x (AUROC of method m - AUROC of base), from summed [numerator, denominator, ...] vectors."""
    a, b = col

    def f(T):
        if m not in T or base not in T or T[m][b] == 0 or T[base][b] == 0:
            return None
        return 100 * (T[m][a] / T[m][b] - T[base][a] / T[base][b])
    return f


def level(m, col=(0, 1)):
    a, b = col
    return lambda T: 100 * T[m][a] / T[m][b] if m in T and T[m][b] else None
