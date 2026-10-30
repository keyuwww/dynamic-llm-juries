# gpt-oss prompt text

gpt-oss-20b and gpt-oss-120b got their reads as raw text in their own chat format, with the date pinned to Oct 17, 2026 (`2026-10-17` in the prompt) and reasoning effort medium. The instruction sits in the developer message. `{instruction}` is [instruction_finance.md](instruction_finance.md) or [instruction_math.md](instruction_math.md) and `{message}` is [juror_message.md](juror_message.md) or [own_answer_reference_message.md](own_answer_reference_message.md).

Reasoned read, up to 4,096 new tokens at temperature 0. The verdict is the last `VERDICT:` line of the final message:

```text
<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: 2024-06
Current date: 2026-10-17

Reasoning: medium

# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|><|start|>developer<|message|># Instructions

{instruction}

<|end|><|start|>user<|message|>{message}<|end|><|start|>assistant
```

Gut read: the same text plus an empty reasoning message and a final message opened at `VERDICT:`. One token is sampled at temperature 0 with its log-probability. The margin is log P(INCORRECT) minus log P(CORRECT), where the word not sampled gets the rest of the probability. Above 0 is a reject.

```text
<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: 2024-06
Current date: 2026-10-17

Reasoning: medium

# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|><|start|>developer<|message|># Instructions

{instruction}

<|end|><|start|>user<|message|>{message}<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>final<|message|>VERDICT:
```
