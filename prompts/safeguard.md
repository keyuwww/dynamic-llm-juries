# Safeguard juror prompt text

gpt-oss-safeguard-20b, the add-on juror run with vLLM on Modal, got the gpt-oss text with one difference: its template has no blank line before the end of the developer message. Reasoned read: up to 4,096 new tokens, temperature 0, seed 0. Gut read: 1 token with the top 20 log-probabilities, temperature 0, seed 0. The margin is the log of the summed probability of the listed tokens that could begin the word INCORRECT, such as " INC", minus the same for CORRECT. A word with no such token among the 20 gets the lowest listed log-probability minus 1.

Reasoned read:

```text
<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: 2024-06
Current date: 2026-10-17

Reasoning: medium

# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|><|start|>developer<|message|># Instructions

{instruction}<|end|><|start|>user<|message|>{message}<|end|><|start|>assistant
```

Gut read:

```text
<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: 2024-06
Current date: 2026-10-17

Reasoning: medium

# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|><|start|>developer<|message|># Instructions

{instruction}<|end|><|start|>user<|message|>{message}<|end|><|start|>assistant<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>final<|message|>VERDICT:
```
