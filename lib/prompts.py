"""Every prompt the experiment sent, and how each output was read back into a verdict. Pure Python: nothing here imports a
model library or opens a connection.

What a juror, the grader and the safeguard juror saw:
  instruction(ds)              the grading instruction. Finance answers (ds "BFF", BFF-Bench) get the finance version, and
                               MT-Bench answers (ds "CMT", Kensho's corrected MT-Bench) the same text with "finance and
                               accounting" swapped once for "math and reasoning".
  noref_user(item)             the juror's message: the conversation and the closing line, with no reference answer.
  selfref_user(item, own)      the own-answer reference read: the juror's own answer where the reference goes, not called expert
                               or ground truth.
  user_message(item)           the grader's message: the conversation plus the expert reference, "treat as ground truth".
  solve_messages(users, own1)  the self-solve chat: the question alone (turn 1), or question 1, the juror's own turn-1 answer and
                               question 2 (turn 2). No system message.
  oss(...)                     gpt-oss's raw chat format (harmony), date pinned to 2026-10-17, reasoning effort medium. The gut
                               read adds an empty reasoning message and opens the final message at "VERDICT:".
  safeguard_prompt(item, mode) the same for gpt-oss-safeguard-20b, whose template drops the blank line before the developer end.
  judge_prompt / selfref_prompt / solve_prompt / grade_prompt / grade_prompt_item
                               the full prompt text per model. Qwen, Nemotron and Kimi use their own chat templates, as does
                               gpt-oss for self-solve, so these take the model's tokenizer (from lib/tinker_client.py).

Every string and builder is copied verbatim from the code that ran on Oct 24, 2026. A build check rendered both for every
answer and juror and found them byte-identical. The codes "BFF" and "CMT" stay because the saved rows use them.
"""
from __future__ import annotations

import math
import re

# ------------------------------------------------------------------------------------------------ the grading instruction
STD = ("You are an expert finance and accounting grader. Read the conversation and decide whether the assistant's FINAL response "
       "correctly answers the user's final question. Key facts, calculations, numbers and conclusions must be correct; wording and "
       "formatting do not matter. Think it through briefly, then end with exactly one line: VERDICT: CORRECT or VERDICT: INCORRECT.")
_FIN, _MATH = "expert finance and accounting grader", "expert math and reasoning grader"
assert STD.count(_FIN) == 1, "the MT-Bench instruction swap must happen exactly once"
STD_CMT = STD.replace(_FIN, _MATH, 1)


def instruction(ds: str) -> str:
    """The instruction for one answer set: "BFF" (finance answers) or "CMT" (MT-Bench answers)."""
    return STD if ds == "BFF" else STD_CMT


instr = instruction   # the name the original code used

# ------------------------------------------------------------------------------------------------ user messages
FINAL_LINE = "Grade the FINAL assistant response. End with VERDICT: CORRECT or VERDICT: INCORRECT."
NOTES_HEADER = "NOTES FROM A COLLEAGUE WHO COMPARED THE RESPONSE WITH THE REFERENCE"


def user_message(item, ground_truth=True, notes=None, notes_header=NOTES_HEADER, final_line=FINAL_LINE, conv=None):
    """The grader's user turn: the conversation, the expert reference and the closing line. ground_truth=False drops
    ' (treat as ground truth)'. notes go before the closing line (not used here). conv overrides the conversation."""
    convo = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in (conv or item["conv"]))
    gt = " (treat as ground truth)" if ground_truth else ""
    s = f"CONVERSATION:\n\n{convo}\n\nEXPERT REFERENCE ANSWER for the final question{gt}:\n{item['ref']}\n\n"
    if notes is not None:
        s += f"{notes_header}:\n{notes}\n\n"
    return s + final_line


REF_BLOCK = "EXPERT REFERENCE ANSWER for the final question (treat as ground truth):\n{ref}\n\n"


def noref_user(item, conv=None):
    """The juror's user turn: user_message with the reference block removed (the instruction never mentions a reference)."""
    s = user_message(item, conv=conv); blk = REF_BLOCK.format(ref=item["ref"])
    assert s.count(blk) == 1; return s.replace(blk, "", 1)


def selfref_user(item, own):
    """The own-answer reference read: the juror's own answer in the reference slot, not labeled expert or ground truth."""
    s = user_message(dict(item, ref=own), ground_truth=False)
    h = "EXPERT REFERENCE ANSWER for the final question"; assert s.count(h) == 1
    return s.replace(h, "REFERENCE ANSWER for the final question", 1)


# ------------------------------------------------------------------------------------------------ gpt-oss raw chat format (harmony)
DATE = "2026-10-17"   # the date pinned in every raw gpt-oss prompt
SYSTEM_IDENTITY = "You are ChatGPT, a large language model trained by OpenAI."
CHANNELS_LINE = "# Valid channels: analysis, commentary, final. Channel must be included for every message."
FAST_OSS_SUFFIX = "<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>final<|message|>VERDICT:"


def harmony_system_block(reasoning_effort="medium", date="2026-10-17", extra=None):
    """The system message exactly as the gpt-oss chat template writes it (no tools)."""
    body = (f"{SYSTEM_IDENTITY}\nKnowledge cutoff: 2024-06\nCurrent date: {date}\n\nReasoning: {reasoning_effort}\n\n"
            f"{CHANNELS_LINE}")
    if extra:
        body += "\n\n" + extra
    return f"<|start|>system<|message|>{body}<|end|>"


def harmony_prompt(instructions, user, where="developer", reasoning_effort="medium", date="2026-10-17",
                   developer_heading="# Instructions\n\n", safeguard=False):
    """Raw harmony prompt ending with '<|start|>assistant'. where="developer" is what the chat template does with a system
    message: <|start|>developer<|message|># Instructions\\n\\n{instructions}\\n\\n<|end|> (safeguard=True drops the trailing
    \\n\\n, as gpt-oss-safeguard's template does). The experiment used only where="developer"."""
    if where == "developer":
        tail = "" if safeguard else "\n\n"
        dev = f"<|start|>developer<|message|>{developer_heading}{instructions}{tail}<|end|>"
        return harmony_system_block(reasoning_effort, date) + dev + f"<|start|>user<|message|>{user}<|end|><|start|>assistant"
    if where == "system":
        return harmony_system_block(reasoning_effort, date, extra=instructions) + f"<|start|>user<|message|>{user}<|end|><|start|>assistant"
    if where == "user":
        return harmony_system_block(reasoning_effort, date) + f"<|start|>user<|message|>{instructions}\n\n{user}<|end|><|start|>assistant"
    if where == "none":
        return harmony_system_block(reasoning_effort, date) + f"<|start|>user<|message|>{user}<|end|><|start|>assistant"
    raise ValueError(where)


def oss(instr, user, effort="medium", fast=False, safeguard=False):
    """Raw harmony text for gpt-oss. fast=True (the gut read) opens the final message at 'VERDICT:' after an empty analysis."""
    s = harmony_prompt(instr, user, where="developer", reasoning_effort=effort, date=DATE, safeguard=safeguard)
    return s + (FAST_OSS_SUFFIX if fast else "")


# ------------------------------------------------------------------------------------------------ chat templates (Qwen, Nemotron, Kimi)
GUT_TAIL = {"qwen": "<think>\n\n</think>\n\n", "nemo": "<think></think>"}           # thinking off: what the template must end with
THINK_TAIL = {"qwen": "<think>\n", "nemo": "<think>\n", "kimi": "<think>"}         # thinking on


def family(m):
    """'oss' (gpt-oss), 'nemo' (Nemotron), 'kimi' (Kimi) or 'qwen'."""
    return "oss" if m.startswith("openai/") else "nemo" if "Nemotron" in m else "kimi" if "Kimi" in m else "qwen"


def chat_text(tokenizer, msgs, think=True):
    """Chat template text with the generation prompt. think=False passes enable_thinking=False."""
    kw = {} if think else {"enable_thinking": False}
    return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw)


def judge_messages(item, user=None):
    """The two messages a thinking-model juror gets: the instruction as system, the juror's message as user."""
    u = user if user is not None else noref_user(item)
    return [{"role": "system", "content": instruction(item["ds"])}, {"role": "user", "content": u}]


def judge_prompt(model, item, mode, user=None, tokenizer=None):
    """A juror's prompt. mode 'gut' (one-token verdict, no reasoning) or 'reasoned'. user defaults to the no-reference message.
    gpt-oss needs no tokenizer (raw harmony text). Qwen and Nemotron gut reads switch thinking off and append 'VERDICT:'."""
    I = instruction(item["ds"]); u = user if user is not None else noref_user(item)
    f = family(model)
    if f == "oss": return oss(I, u, fast=(mode == "gut"))
    msgs = [{"role": "system", "content": I}, {"role": "user", "content": u}]
    if mode == "gut":
        s = chat_text(tokenizer, msgs, think=False); assert s.endswith(GUT_TAIL[f]), (model, s[-40:]); return s + "VERDICT:"
    s = chat_text(tokenizer, msgs); assert s.endswith(THINK_TAIL[f]), (model, s[-40:]); return s


def selfref_prompt(model, item, own, tokenizer=None):
    """The own-answer reference read: always a gut read."""
    return judge_prompt(model, item, "gut", user=selfref_user(item, own), tokenizer=tokenizer)


def solve_messages(users, own1=None):
    """Self-solve chat for one question turn. users = the user messages up to this turn. Turn 2 needs the juror's own turn-1
    answer (the original wrote a 't1_missing' row with no call when there was none)."""
    if len(users) == 1:
        return [{"role": "user", "content": users[0]}]
    return [{"role": "user", "content": users[0]}, {"role": "assistant", "content": own1}, {"role": "user", "content": users[1]}]


def solve_prompt(model, msgs, tokenizer):
    """Self-solve prompt. gpt-oss: its chat template at reasoning effort medium (the template stamps the day it is rendered as
    the current date). Others: chat template with thinking on."""
    if family(model) == "oss":
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, reasoning_effort="medium")
    s = chat_text(tokenizer, msgs); assert s.endswith(THINK_TAIL[family(model)]); return s


def grade_conv(users, own1, own2=None):
    """The conversation the grader sees for a juror's own answer: turn 1 is [question 1, own answer 1], turn 2 adds
    [question 2, own answer 2]."""
    if len(users) == 1:
        return [{"role": "user", "content": users[0]}, {"role": "assistant", "content": own1}]
    return [{"role": "user", "content": users[0]}, {"role": "assistant", "content": own1},
            {"role": "user", "content": users[1]}, {"role": "assistant", "content": own2}]


def grade_messages(item):
    """The two messages the grader gets: the instruction as system, the conversation plus the expert reference as user."""
    return [{"role": "system", "content": instruction(item["ds"])}, {"role": "user", "content": user_message(item)}]


def grade_prompt(grader, item, conv, tokenizer):
    """The grader on a juror's own answer: item gives the turn's reference and answer set, conv the juror's own conversation."""
    x = dict(item, conv=conv)
    s = chat_text(tokenizer, grade_messages(x)); assert s.endswith(THINK_TAIL[family(grader)]), (grader, s[-40:]); return s


def grade_prompt_item(grader, item, tokenizer):
    """The grader screening check: an examinee's answer graded with the expert reference."""
    s = chat_text(tokenizer, grade_messages(item)); assert s.endswith(THINK_TAIL[family(grader)]); return s


def safeguard_prompt(item, mode):
    """gpt-oss-safeguard-20b, the add-on juror run on Modal: the juror's message in raw harmony with safeguard=True."""
    return oss(instruction(item["ds"]), noref_user(item), fast=(mode == "gut"), safeguard=True)


# ------------------------------------------------------------------------------------------------ reading the outputs
VERDICT_RE = re.compile(r"VERDICT:\s*\**\s*(CORRECT|INCORRECT)")
_SPECIAL_END = re.compile(r"(<\|[a-z_]+\|>|</s>|\[EOS\])+\s*$")


def final_channel(text):
    """gpt-oss output: the text after the last final-channel header, end tokens stripped ('' if none)."""
    tag = "<|channel|>final<|message|>"
    return text.rsplit(tag, 1)[1].replace("<|return|>", "").replace("<|end|>", "").strip() if tag in text else ""


def parse_verdict(o):
    """gpt-oss reasoned read: 1 CORRECT, 0 INCORRECT, -1 unparsed. Reads the final channel, else the last 300 characters."""
    txt = o.get("final") or o["text"][-300:]
    m = VERDICT_RE.findall(txt)
    if not m: return -1
    return {"CORRECT": 1, "INCORRECT": 0}[m[-1]]


def parse_think(text):
    """Thinking-model output to (final text, verdict 1/0/-1). No '</think>' means the trace was cut (-1). Last VERDICT wins."""
    if "</think>" not in text: return "", -1
    fin = _SPECIAL_END.sub("", text.rsplit("</think>", 1)[1]).strip()
    m = VERDICT_RE.findall(fin)
    return fin, (1 if m and m[-1] == "CORRECT" else 0 if m else -1)


def own_from(model, o):
    """Self-solve output to the juror's own answer, or None (cut at the token limit, empty, no final channel or no '</think>')."""
    if o["finish"] == "length": return None
    if family(model) == "oss": fin = o["final"].strip()
    else: fin = parse_think(o["text"])[0]
    return fin or None


def parse_raw(text):
    """Safeguard reasoned read (vLLM output, special tokens kept) to (analysis, final, verdict 1/0/-1)."""
    a, f = text, ""
    if "<|channel|>final<|message|>" in text:
        a, f = text.split("<|channel|>final<|message|>", 1)
    a = a.replace("<|channel|>analysis<|message|>", "").split("<|end|>")[0]
    m = VERDICT_RE.findall(f or text[-200:])
    return a, f, (1 if m and m[-1] == "CORRECT" else 0 if m else -1)


def _cls(tok):
    """A verdict token's class: 'COR' if it starts the word CORRECT, 'INC' if it starts INCORRECT, else None."""
    t = (tok or "").strip().strip("*").strip().upper()
    if not t:
        return None
    if "CORRECT".startswith(t):
        return "COR"
    if "INCORRECT".startswith(t):
        return "INC"
    return None


def _lse(xs):
    m = max(xs); return m + math.log(sum(math.exp(x - m) for x in xs))


def m1_from(o):
    """gpt-oss gut margin from one sampled token at temperature 0 with its log-probability: margin = log P(INCORRECT) -
    log P(CORRECT), taking the rest of the probability as the other class. nan if the token is neither class."""
    cls = _cls(o["text"]); lp = float(o["logprobs"][0]); p = min(math.exp(lp), 1 - 1e-12)
    if cls is None: return float("nan")
    return (lp - math.log1p(-p)) if cls == "INC" else (math.log1p(-p) - lp)


def margin_from_top(top):
    """Safeguard gut margin from the top-20 tokens {token: logprob}: logsumexp(INCORRECT-class) - logsumexp(CORRECT-class).
    A class absent from the list gets (lowest listed logprob - 1) and censored=True. Returns (margin, censored)."""
    cor = [lp for t, lp in top.items() if _cls(t) == "COR"]
    inc = [lp for t, lp in top.items() if _cls(t) == "INC"]
    floor = min(top.values()) - 1.0 if top else -30.0
    cens = not cor or not inc
    return (_lse(inc) if inc else floor) - (_lse(cor) if cor else floor), cens


def margin_from_vllm(out):
    """out: one raw safeguard row with token_logprobs [[token, logprob, {top 20}]]."""
    return margin_from_top(out["token_logprobs"][0][2])
