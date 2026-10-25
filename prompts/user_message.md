# User message

Every judge got the same user message after its system message: the whole conversation, then the expert reference for the final question. `{convo}` is each turn as `[USER]` or `[ASSISTANT]` and its text, separated by blank lines.

```text
CONVERSATION:

{convo}

EXPERT REFERENCE ANSWER for the final question (treat as ground truth):
{ref}

Grade the FINAL assistant response. End with VERDICT: CORRECT or VERDICT: INCORRECT.
```
