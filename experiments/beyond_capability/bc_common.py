"""Shared pieces for the beyond-capability experiments: models, prompts, answer normalisation."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from data import BBEH_SUFFIX, _extract_answer, _fuzzy_match  # noqa: E402

# key -> (Tinker id, renderer, context length). Judges run with thinking OFF, as in the pool runs.
# Kimi-K3.1-Pro (high reasoning) is the "stronger model": a different family from every judge.
MODELS = {
    "qwen3.5-4b": ("Qwen/Qwen3.5-4B", "qwen3_5_disable_thinking", 65536),
    "qwen3.5-9b": ("Qwen/Qwen3.5-9B", "qwen3_5_disable_thinking", 65536),
    "qwen3.6-35b-a3b": ("Qwen/Qwen3.6-35B-A3B", "qwen3_5_disable_thinking", 65536),
    "nemotron3-super-120b": ("nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16", "nemotron3_disable_thinking", 65536),
    "kimi-k3.1-pro": ("moonshotai/Kimi-K3.1-Pro:peft:262144", "kimi_k31_pro_high_reasoning", 262144),
    # thinking-ON solves (a second definition of "can solve": the model's best effort, not the judging mode)
    "nemotron3-super-120b@think": ("nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16:peft:262144", "nemotron3", 262144),
    "qwen3.5-4b@think": ("Qwen/Qwen3.5-4B:peft:262144", "qwen3_5", 262144),
    "qwen3.5-9b@think": ("Qwen/Qwen3.5-9B", "qwen3_5", 65536),
    "qwen3.6-35b-a3b@think": ("Qwen/Qwen3.6-35B-A3B:peft:262144", "qwen3_5", 262144),
}
JUDGES = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b", "nemotron3-super-120b"]
STRONG = "kimi-k3.1-pro"
GLM = ("zai-org/GLM-5.3-Flash:peft:262144", "glm5_3_high_reasoning", 262144)


def has_final(text):
    return bool(text) and ("The answer is" in text or "final answer is" in text)


def norm_answer(text):
    """The BBEH final answer, normalised like the official grader (None if no final answer)."""
    if not has_final(text):
        return None
    p = _extract_answer(text.strip()).lower().replace(", ", ",").replace("**", "")
    p = p.split("\n")[0].strip()
    p = p[:-1] if p.endswith(".") else p
    if len(p) == 3 and p[0] == "(" and p[-1] == ")":
        p = p[1]
    return p or None


def same_answer(a, b):
    """Two normalised BBEH answers are the same (official fuzzy match, both directions)."""
    if a is None or b is None:
        return False
    return _fuzzy_match(a, b) or _fuzzy_match(b, a)


# ----------------------------------------------------------------------------- judge prompts
BBEH_JUDGE = """You are grading an AI assistant's answer to a reasoning question.

[QUESTION]
{question}

[ASSISTANT'S ANSWER]
{answer}
{reference}
Is the assistant's final answer correct? Only the final answer matters, not the style of the reasoning.
Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""

REF_BLOCK = "\n[REFERENCE ANSWER{note}]\n{ref}\n"
REF_NOTES = {
    "gold": " (the official correct answer)",
    "strong": " (a solution written by a stronger AI model; it is usually but not always right)",
    "self": "",  # the judge's own earlier solution, presented exactly like the pool's 'self' condition
}

# Verification instead of re-solving: check the conditions and each step of the candidate's own reasoning.
BBEH_VERIFY = """You are checking an AI assistant's answer to a reasoning question.

[QUESTION]
{question}

[ASSISTANT'S ANSWER]
{answer}

Do NOT solve the question yourself from scratch. Verify the assistant's work instead:
1. List the conditions stated in the question that a correct final answer must satisfy.
2. Go through the assistant's reasoning step by step. For each step, check it against the question and the earlier steps; note the first step that is wrong, if any.
3. Check that the final answer follows from the steps and satisfies every condition from (1).
The answer is incorrect if any step the final answer depends on is wrong, or if the final answer breaks a condition. Only the correctness of the final answer matters, not the style.
End with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""

CONDITIONS = ["none", "gold", "strong", "self", "verify", "selfturn", "saidit", "otherturn"]

# "Your own answer" framing (the candidate is NOT the judge's own; only the presentation says so).
#  selfturn: a conversation where the candidate is the model's own reply, then "is your answer correct?" -- the same
#            layout as the self-check role in the hidden-state study (dir_build.py)
#  saidit:   one prompt that says "here is the answer you gave earlier"
SELFTURN_Q = ("Is your final answer above correct? Only the final answer matters, not the style of the reasoning.\n"
              "Reason briefly, then end with exactly one line: \"VERDICT: CORRECT\" or \"VERDICT: INCORRECT\".")
BBEH_SAIDIT = """Earlier, you answered the reasoning question below. Here is the answer you gave.

[QUESTION]
{question}

[YOUR EARLIER ANSWER]
{answer}

Is your final answer correct? Only the final answer matters, not the style of the reasoning.
Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


# otherturn: the same conversation and follow-up as selfturn, but the answer is relayed as ANOTHER assistant's
# ("Here is the answer another AI assistant gave...") and the follow-up asks about "that answer", not "your answer".
RELAY = "Here is the answer another AI assistant gave to your question:\n\n"
OTHERTURN_Q = SELFTURN_Q.replace("Is your final answer above correct?", "Is that assistant's final answer above correct?")


def judge_messages(cond, question, answer, ref=None):
    """Chat messages for a BBEH judging call (multi-turn for 'selfturn')."""
    q = question.replace(BBEH_SUFFIX, "")
    if cond == "selfturn":
        return [{"role": "user", "content": q + BBEH_SUFFIX}, {"role": "assistant", "content": answer},
                {"role": "user", "content": SELFTURN_Q}]
    if cond == "saidit":
        return [{"role": "user", "content": BBEH_SAIDIT.format(question=q, answer=answer)}]
    if cond == "otherturn":
        return [{"role": "user", "content": q + BBEH_SUFFIX}, {"role": "assistant", "content": RELAY + answer},
                {"role": "user", "content": OTHERTURN_Q}]
    return [{"role": "user", "content": judge_prompt(cond, question, answer, ref)}]


def judge_prompt(cond, question, answer, ref=None):
    q = question.replace(BBEH_SUFFIX, "")
    if cond == "verify":
        return BBEH_VERIFY.format(question=q, answer=answer)
    reference = "" if cond == "none" else REF_BLOCK.format(note=REF_NOTES[cond], ref=ref)
    return BBEH_JUDGE.format(question=q, answer=answer, reference=reference)


VERDICT_RE = re.compile(r"VERDICT:\s*\**\s*(CORRECT|INCORRECT)", re.I)


def parse_verdict(text):
    m = VERDICT_RE.findall(text or "")
    if not m:
        return None
    return 1 if m[-1].upper() == "CORRECT" else 0


VERDICT_FILL_PROMPT = """Below is the end of an evaluation written by a grader. The grader was asked whether an AI assistant's final answer to a question is correct.
What final verdict did the grader give? Judge only from what the grader wrote; do not grade the problem yourself.

[GRADER'S EVALUATION (end)]
{text}

Reply with exactly one word: CORRECT, INCORRECT, or NONE if the grader gave no clear verdict."""


# ----------------------------------------------------------------------------- BFF-Bench (finance, human labels)
def render_conv(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv)


BFF_JUDGE = """You are grading an AI assistant's answer in a finance/accounting conversation.

{conversation}
{reference}
Is the assistant's FINAL response a correct answer to the user's final question? The key facts, calculations, numbers and conclusions must be correct; minor wording or formatting issues do not matter, but a wrong number, wrong method or wrong conclusion makes it incorrect.
Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""

BFF_VERIFY = """You are checking an AI assistant's answer in a finance/accounting conversation.

{conversation}

Do NOT write your own solution from scratch. Verify the assistant's FINAL response instead:
1. List what the user's final question asks for and the facts and numbers given in the conversation.
2. Go through the response step by step: check that each formula or accounting treatment is the right one for this question, that the right inputs are used, and recompute every calculation. Note the first step that is wrong, if any.
3. Check that the conclusion follows from the steps and answers every part of the question.
The response is incorrect if a step the conclusion depends on is wrong (wrong number, wrong method or wrong conclusion); minor wording or formatting issues do not matter.
End with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""

BFF_REF_NOTES = {"human": " (written by an expert)", "strong": REF_NOTES["strong"], "self": ""}
BFF_CONDITIONS = ["none", "human", "strong", "self", "verify", "selfturn", "saidit", "otherturn"]

BFF_SELFTURN_Q = ("Is your final response above a correct answer to my last question? The key facts, calculations, numbers "
                  "and conclusions must be correct; minor wording or formatting issues do not matter, but a wrong number, "
                  "wrong method or wrong conclusion makes it incorrect.\nReason briefly, then end with exactly one line: "
                  "\"VERDICT: CORRECT\" or \"VERDICT: INCORRECT\".")
BFF_SAIDIT = """Earlier, you had the finance/accounting conversation below with a user. The [ASSISTANT] turns are your own answers.

{conversation}

Is your FINAL response a correct answer to the user's final question? The key facts, calculations, numbers and conclusions must be correct; minor wording or formatting issues do not matter, but a wrong number, wrong method or wrong conclusion makes it incorrect.
Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


def bff_judge_messages(cond, conv, ref=None):
    if cond == "selfturn":
        return [dict(m) for m in conv] + [{"role": "user", "content": BFF_SELFTURN_Q}]
    if cond == "saidit":
        return [{"role": "user", "content": BFF_SAIDIT.format(conversation=render_conv(conv))}]
    if cond == "otherturn":
        c = [dict(m) for m in conv]
        c[-1]["content"] = RELAY.replace("your question", "your last question") + c[-1]["content"]
        q = BFF_SELFTURN_Q.replace("Is your final response above", "Is that assistant's final response above")
        return c + [{"role": "user", "content": q}]
    return [{"role": "user", "content": bff_judge_prompt(cond, conv, ref)}]


def bff_judge_prompt(cond, conv, ref=None):
    c = render_conv(conv)
    if cond == "verify":
        return BFF_VERIFY.format(conversation=c)
    reference = "" if cond == "none" else REF_BLOCK.format(note=BFF_REF_NOTES[cond], ref=ref)
    return BFF_JUDGE.format(conversation=c, reference=reference)


BFF_GRADER = """You are grading an AI assistant's answer to a finance/accounting question, using an expert reference answer as ground truth.

{conversation}

Expert reference answer for the final question:
{ref}

Is the assistant's FINAL response substantively correct? The key facts, calculations, numbers and conclusions must match the reference; minor wording or formatting differences do not matter, but a wrong number, wrong method or wrong conclusion makes it incorrect.
Explain briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""
