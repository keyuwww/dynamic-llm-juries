"""C2: controlled BFF pairs where we set the quality gap ourselves.

From BFF pairwise (kensho/VERDICTSPairwise, BFF half) take the human-preferred answer for up to 100 distinct question
turns and build three kinds of pair, each shown in both orders:
  identical  the same answer in both slots. Any consistent position preference is pure order bias.
  corrupt    the answer vs the same answer with its last number changed by +10% (a small, hard-to-see error).
             gold = the original answer.
  pad        the answer vs the same answer plus a neutral closing paragraph (longer, no new content).
             no gold; measures a length preference.
Writes data/bffctrl_items.json for run_confidence.py --bench bffctrl.
"""
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))
from data import load_pairwise_items  # noqa: E402

NUM = re.compile(r"(?<![\w.])(\$?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(%?)")
PAD = ("\n\nPlease note that these figures are based only on the information provided in the question. Small "
       "differences can arise from rounding at intermediate steps, and the same approach applies if any of the inputs "
       "change. It is good practice to double-check each input against the original source before relying on the "
       "result for a decision.")


def corrupt(text):
    """Change the last number in the text by +10%, keeping its format. None if there is no usable number."""
    def real_quantity(m):     # money, percent, decimal, thousands separator or >= 100; never a list marker
        s, e = m.start(), m.end()
        line_start = s == 0 or text[s - 1] == "\n" or text[max(0, s - 2):s].strip() == ""
        list_marker = line_start and text[e:e + 1] == "." and not m.group(3)
        val = float(m.group(2).replace(",", "") + (m.group(3) or ""))
        return not list_marker and (m.group(1) or m.group(4) or m.group(3) or "," in m.group(2) or val >= 100)
    ms = [m for m in NUM.finditer(text) if real_quantity(m)]
    if not ms:
        return None
    m = ms[-1]
    val = float(m.group(2).replace(",", "") + (m.group(3) or ""))
    new = val * 1.1
    dec = len(m.group(3)) - 1 if m.group(3) else 0
    body = f"{new:,.{dec}f}" if "," in m.group(2) else f"{new:.{dec}f}"
    return text[:m.start()] + m.group(1) + body + m.group(4) + text[m.end():]


def main():
    items = load_pairwise_items()
    base = {}
    for it in items:
        if it["order"] != "ab":
            continue
        key = (it["uid"], it["turn"])
        if key in base:
            continue
        win = it["conv_a"] if it["gold"] == 1 else it["conv_b"]
        base[key] = dict(win=win, model=it["model_first"] if it["gold"] == 1 else it["model_second"])
    keys = sorted(base)
    random.Random(0).shuffle(keys)
    out = []
    for uid, turn in keys[:100]:
        win = base[(uid, turn)]["win"]
        final = win[-1]["content"]
        bad = corrupt(final)
        variants = {"identical": (win, win, -1),
                    "pad": (win[:-1] + [dict(win[-1], content=final + PAD)], win, -1)}
        if bad:
            variants["corrupt"] = (win, win[:-1] + [dict(win[-1], content=bad)], 1)
        for cond, (x, y, g) in variants.items():
            pid = f"{uid}-t{turn}-{cond}"
            out.append(dict(id=f"{pid}|ab", pair_id=pid, order="ab", condition=cond, conv_a=x, conv_b=y,
                            gold=g, examinee=base[(uid, turn)]["model"]))
            out.append(dict(id=f"{pid}|ba", pair_id=pid, order="ba", condition=cond, conv_a=y, conv_b=x,
                            gold=(1 - g) if g >= 0 else -1, examinee=base[(uid, turn)]["model"]))
    p = HERE / "data" / "bffctrl_items.json"
    p.write_text(json.dumps(out))
    from collections import Counter
    print(len(out), "items", Counter(o["condition"] for o in out))


if __name__ == "__main__":
    main()
