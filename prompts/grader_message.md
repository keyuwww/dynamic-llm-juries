# Grader message

The user message of the grader, with the expert reference marked as ground truth. In the screening check `{convo}` is an examinee's conversation from VERDICTS. On the jurors' own answers it is the juror's own conversation, shown below as chat messages, and `{ref}` is the expert reference for that question turn. The grader reasons with thinking on, at temperature 0, for up to 8,192 new tokens.

```text
CONVERSATION:

{convo}

EXPERT REFERENCE ANSWER for the final question (treat as ground truth):
{ref}

Grade the FINAL assistant response. End with VERDICT: CORRECT or VERDICT: INCORRECT.
```

The conversation for a turn-1 own answer:

```text
[
 {
  "role": "user",
  "content": "{question 1}"
 },
 {
  "role": "assistant",
  "content": "{own answer 1}"
 }
]
```

For a turn-2 own answer:

```text
[
 {
  "role": "user",
  "content": "{question 1}"
 },
 {
  "role": "assistant",
  "content": "{own answer 1}"
 },
 {
  "role": "user",
  "content": "{question 2}"
 },
 {
  "role": "assistant",
  "content": "{own answer 2}"
 }
]
```
