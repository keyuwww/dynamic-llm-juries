"""Where to cut a judging transcript for early answering. Shared by the Tinker readouts (tinker_jobs.py) and the
GPU readouts of open models (probe_steer.py), so every judge is cut the same way.

Non-thinking judges: A (nothing written yet), 25/50/75% of the text before the verdict line, C (at the verdict word).
Thinking judges (OLMo-3 Think): the thinking is cut at 25/50/75% and closed with </think>; E = the whole thinking,
right after </think>; C = at the verdict word in the visible answer.
"""
import re

FRACS = [0.25, 0.5, 0.75]
FINAL_RE = re.compile(r"VERDICT:\s*\**\s*(CORRECT|INCORRECT|A|B)\b", re.I)


def checkpoints(transcript, pairwise):
    """[(name, assistant_prefix, (option_1, option_2))]. option_1 is CORRECT (or A)."""
    space = (" A", " B") if pairwise else (" CORRECT", " INCORRECT")
    m = None
    for m in FINAL_RE.finditer(transcript):
        pass
    pre = transcript[:m.start()] if m else transcript
    out = [("A", "VERDICT:", space)]
    for f in FRACS:
        cut = pre[: int(len(pre) * f)]
        cut = cut[: cut.rfind(" ")] if " " in cut else cut  # do not split a word
        out.append((f"{int(f * 100)}", cut.rstrip() + "\n\nVERDICT:", space))
    if m:  # real verdict position: everything the judge wrote up to the verdict word
        s = m.start(1)
        prefix = transcript[:s]
        if prefix.endswith(" "):
            out.append(("C", prefix[:-1], space))
        else:
            words = ("A", "B") if pairwise else ("CORRECT", "INCORRECT")
            out.append(("C", prefix, words))
    return out


def _cut(text, f):
    cut = text[: int(len(text) * f)]
    return cut[: cut.rfind(" ")] if " " in cut else cut  # do not split a word


def checkpoints_think(text, pairwise):
    """Same as checkpoints(), for a transcript that starts inside <think> (the chat template opens it)."""
    space = (" A", " B") if pairwise else (" CORRECT", " INCORRECT")
    close = "\n</think>\n\nVERDICT:"
    out = [("A", close.lstrip("\n"), space)]
    if "</think>" not in text:  # thinking never ended: only the partial-thinking checkpoints exist
        return out + [(f"{int(f * 100)}", _cut(text, f).rstrip() + close, space) for f in FRACS]
    thinking, answer = text.split("</think>", 1)
    out += [(f"{int(f * 100)}", _cut(thinking, f).rstrip() + close, space) for f in FRACS]
    out.append(("E", thinking.rstrip() + close, space))
    m = None
    for m in FINAL_RE.finditer(answer):
        pass
    if m:
        prefix = thinking + "</think>" + answer[:m.start(1)]
        if prefix.endswith(" "):
            out.append(("C", prefix[:-1], space))
        else:
            out.append(("C", prefix, ("A", "B") if pairwise else ("CORRECT", "INCORRECT")))
    return out
