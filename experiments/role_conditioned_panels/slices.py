"""Pre-registered slices, computable from prompt/response text alone (before any judge is called).

Feature regexes are Ingrid's hand_feats() (notebook cell 9). Only thresholds are new, and the two
median thresholds are frozen on the construction-fit split of each repeat.
"""
import re

import numpy as np

_NUM = re.compile(r"\d[\d,]*\.?\d*")


def q_features(prompt):
    return dict(dollar=prompt.count("$"), percent=prompt.count("%"), equals=prompt.count("="),
                numbers=len(_NUM.findall(prompt)), digit_frac=sum(c.isdigit() for c in prompt) / max(len(prompt), 1))


def hand_feats(prompt, response):
    f = {f"q_{k}": v for k, v in q_features(prompt or "").items()}
    f["r_words"] = len((response or "").split())
    return f


def fit_slice_thresholds(prompts, responses):
    """Frozen medians from the fit rows only."""
    F = [hand_feats(p, r) for p, r in zip(prompts, responses)]
    return dict(digit_frac_median=float(np.median([f["q_digit_frac"] for f in F])),
                r_words_median=float(np.median([f["r_words"] for f in F])))


def calc_heavy(prompt, response, thr):
    f = hand_feats(prompt, response)
    return bool(f["q_dollar"] > 0 or f["q_percent"] > 0 or f["q_digit_frac"] > thr["digit_frac_median"])


def long_response(prompt, response, thr):
    return bool(hand_feats(prompt, response)["r_words"] > thr["r_words_median"])


def numeric_prompt(prompt, response, thr):
    f = hand_feats(prompt, response)
    return bool(f["q_equals"] > 0 or f["q_numbers"] >= 2)


SLICES = {"calc_heavy": calc_heavy, "long_response": long_response, "numeric_prompt": numeric_prompt}


def slice_masks(prompts, responses, thr):
    """{slice name: bool array over all given rows}."""
    return {name: np.array([fn(p, r, thr) for p, r in zip(prompts, responses)], dtype=bool)
            for name, fn in SLICES.items()}


def slice_prevalence(mask, idx):
    return float(mask[idx].mean()) if len(idx) else float("nan")


def usable_slices(masks, fit_idx, val_idx, lo=0.10, hi=0.80, min_n=30):
    """Gate slices per repeat: prevalence on fit in [lo, hi], and >= min_n items in both fit and val.
    Returns (kept names, {name: reason dropped})."""
    keep, dropped = [], {}
    for name, m in masks.items():
        prev = slice_prevalence(m, fit_idx)
        nf, nv = int(m[fit_idx].sum()), int(m[val_idx].sum())
        if not lo <= prev <= hi:
            dropped[name] = f"prevalence {prev:.0%} outside [{lo:.0%}, {hi:.0%}]"
        elif nf < min_n or nv < min_n:
            dropped[name] = f"too few items (fit {nf}, val {nv}; need >= {min_n})"
        else:
            keep.append(name)
    return keep, dropped
