# Qwen, Nemotron and Kimi prompt text

Qwen3.6-35B-A3B and Nemotron-3-Super got two chat messages, and so did Qwen3.5-4B and Qwen3.5-9B in the screening check. The instruction is the system message and the juror's message the user message, through each model's own chat template. The two candidate graders, Qwen3.5-397B-A17B and Kimi-K2.6, got the instruction and the grader message the same way, with up to 8,192 new tokens.

Reasoned read: thinking on, up to 6,144 new tokens at temperature 0. The rendered template must end with the text below. The verdict is the last `VERDICT:` line after `</think>`, and an output with no `</think>` counts as unparsed.

- Qwen: `"<think>\n"`
- Nemotron: `"<think>\n"`
- Kimi-K2.6: `"<think>"`

Gut read: thinking off (`enable_thinking=False`). The rendered template must end with the empty thinking block below, and `VERDICT:` is appended. The margin is log P(" INCORRECT") minus log P(" CORRECT") at that point, each the summed log-probability of the word's tokens. Above 0 is a reject.

- Qwen: `"<think>\n\n</think>\n\n"`, then `VERDICT:`
- Nemotron: `"<think></think>"`, then `VERDICT:`
