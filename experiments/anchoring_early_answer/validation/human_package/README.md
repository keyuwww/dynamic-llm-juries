# Human label check (not yet done)

177 items: 60 high-belief reclassifications, 23 auditor disagreements, 94 stratified retained
answers (8 per benchmark x belief cell; population sizes in key.json for weighting). Give readers only
items.jsonl. For each item a reader records: clearly wrong / actually correct / ambiguous, and a short reason.
Two readers per item; BFF-Bench items need finance background. Disagreements are adjudicated by a third reader.
No model output may be recorded as a human annotation.

## Transcript sample (transcripts.jsonl, not yet annotated)
76 thinking-on Qwen transcripts of audited wrong answers, 20 per belief bin (all 16 available at 7/7), verdict lines removed. Two readers label
PROCESS (independent derivation / checking the candidate's steps / paraphrasing / unclear) and RESULT (own final
result equals the candidate's / differs / none), blind to belief; report confusion between readers and adjudicate.
