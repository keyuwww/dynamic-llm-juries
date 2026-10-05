"""Oracle predictor eta-hat_S(z), oracle risk, conditional gain and slice gain.

Everything here works on Z (verdicts) and Y (gold) only -- no match indicator."""
import numpy as np


def _codes(Z, S):
    """Integer code of each row's verdict pattern restricted to columns S."""
    if len(S) == 0:
        return np.zeros(len(Z), dtype=np.int64)
    return (Z[:, list(S)].astype(np.int64) * (1 << np.arange(len(S)))).sum(1)


class EtaTable:
    """Laplace-smoothed frequency table over verdict patterns; unseen patterns fall back to the prior."""

    def __init__(self, table, prior, S):
        self.table, self.prior, self.S = table, prior, list(S)

    def predict(self, Z):
        c = _codes(Z, self.S)
        return np.array([self.table.get(int(x), self.prior) for x in c])


def fit_eta_table(Z_S_fit, Y_fit, m=2.0):
    """Z_S_fit: (n, |S|) verdicts of the panel judges on the fit rows. eta(z) = (sum Y + m*ybar)/(n_z + m)."""
    n, k = Z_S_fit.shape
    ybar = float(Y_fit.mean())
    codes = _codes(Z_S_fit, range(k))
    table = {}
    for c in np.unique(codes):
        sel = codes == c
        table[int(c)] = (float(Y_fit[sel].sum()) + m * ybar) / (sel.sum() + m)
    return EtaTable(table, ybar, range(k))


def oracle_risk(eta_table, Z_S_val, Y_val):
    return float(np.mean((Y_val - eta_table.predict(Z_S_val)) ** 2))


def _risk(S, Z, Y, fit_idx, val_idx, m=2.0):
    S = list(S)
    eta = fit_eta_table(Z[np.ix_(fit_idx, S)], Y[fit_idx], m)
    return oracle_risk(eta, Z[np.ix_(val_idx, S)], Y[val_idx])


def conditional_gain(j, S, Z, Y, fit_idx, val_idx, m=2.0):
    """g(j|S) = R*(S) - R*(S + j), eta fit on fit_idx, risk measured on val_idx."""
    return _risk(S, Z, Y, fit_idx, val_idx, m) - _risk(list(S) + [j], Z, Y, fit_idx, val_idx, m)


def slice_gain(j, S, f, Z, Y, fit_idx, val_idx, slice_mask, m=2.0):
    """A_f(j|S): same, but eta and validation risk restricted to rows with slice_mask True.
    `f` is the slice name (kept for the call signature / logging)."""
    fi, vi = fit_idx[slice_mask[fit_idx]], val_idx[slice_mask[val_idx]]
    if len(fi) == 0 or len(vi) == 0:
        return 0.0
    return _risk(S, Z, Y, fi, vi, m) - _risk(list(S) + [j], Z, Y, fi, vi, m)


def specialization_ratio(slice_g, global_g, eps0=0.01):
    return slice_g / (global_g + eps0)
