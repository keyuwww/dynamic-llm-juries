import numpy as np


def make_3way_splits(groups, seed, n_repeats=20, frac=(0.50, 0.25, 0.25)):
    """groups: length-N array of question ids. Returns a list of (fit_idx, val_idx, test_idx)
    item-index arrays, one tuple per repeat. Whole questions land in one part."""
    rng = np.random.default_rng(seed)
    ug = np.unique(groups)
    splits = []
    for r in range(n_repeats):
        perm = rng.permutation(ug)
        n_fit = int(round(frac[0] * len(ug)))
        n_val = int(round(frac[1] * len(ug)))
        fit_g, val_g, test_g = perm[:n_fit], perm[n_fit:n_fit + n_val], perm[n_fit + n_val:]
        splits.append((
            np.where(np.isin(groups, fit_g))[0],
            np.where(np.isin(groups, val_g))[0],
            np.where(np.isin(groups, test_g))[0],
        ))
    return splits


def make_item_splits(n_items, seed, n_repeats=20, frac=(0.50, 0.25, 0.25)):
    """Leaky control: same 50/25/25 partition but over ITEMS, so responses to one question straddle parts."""
    rng = np.random.default_rng(seed)
    splits = []
    for _ in range(n_repeats):
        perm = rng.permutation(n_items)
        a, b = int(round(frac[0] * n_items)), int(round((frac[0] + frac[1]) * n_items))
        splits.append((np.sort(perm[:a]), np.sort(perm[a:b]), np.sort(perm[b:])))
    return splits
