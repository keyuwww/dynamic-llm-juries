# Third label auditor: Claude Opus 5.5

Answers audited: 98; missing Claude verdicts: 0

## Blind 60-answer sample (stratified on GLM's verdict), n = 60

| GLM verdict | n | Claude: clearly wrong | actually correct | contested |
|---|---|---|---|---|
| LABEL_OK | 25 | 22 | 0 | 3 |
| LABEL_WRONG | 25 | 3 | 17 | 5 |
| CONTESTED | 10 | 1 | 5 | 4 |

Claude vs glm (clearly-wrong-or-not), sample: 53/60 agree, kappa 0.76

Claude vs kimi (clearly-wrong-or-not), sample: 50/60 agree, kappa 0.67
Agreement with GLM re-weighted to GLM's full mix: 88.1% (per stratum: LABEL_OK 88%, LABEL_WRONG 88%, CONTESTED 90%)
All three auditors make the same clearly-wrong-or-not call on 49/60 sample answers

## GLM/Kimi disagreements, n = 43
Claude sides with GLM on 22, with Kimi on 21.
Claude's verdicts there: CONTESTED 18, LABEL_OK 16, LABEL_WRONG 9

| GLM | Kimi | Claude | n |
|---|---|---|---|
| CONTESTED | LABEL_OK | CONTESTED | 10 |
| CONTESTED | LABEL_OK | LABEL_OK | 9 |
| LABEL_OK | LABEL_WRONG | LABEL_OK | 4 |
| LABEL_OK | CONTESTED | CONTESTED | 4 |
| LABEL_OK | LABEL_WRONG | LABEL_WRONG | 4 |
| LABEL_WRONG | LABEL_OK | CONTESTED | 3 |
| LABEL_WRONG | LABEL_OK | LABEL_WRONG | 3 |
| LABEL_WRONG | LABEL_OK | LABEL_OK | 2 |
| LABEL_OK | LABEL_WRONG | CONTESTED | 1 |
| LABEL_OK | CONTESTED | LABEL_WRONG | 1 |
| LABEL_OK | CONTESTED | LABEL_OK | 1 |
| CONTESTED | LABEL_OK | LABEL_WRONG | 1 |

## By benchmark (sample)

- bff: Claude agrees with GLM on 19/22, with Kimi on 16/22
- judgebench: Claude agrees with GLM on 34/38, with Kimi on 34/38
