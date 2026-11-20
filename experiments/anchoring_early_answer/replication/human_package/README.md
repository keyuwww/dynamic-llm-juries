# Human label check: MMLU-Pro replication (not yet done)

150 wrong-labelled responses, stratified by the highest belief any judge has in them (7/7 50, 4-6 40,
1-3 30, 0/7 30; population sizes in key.json). Readers get items.jsonl only (or the annotation page), never key.json.

For each item, decide whether the response the MMLU-Pro key marks WRONG really has a wrong final answer:
- clearly wrong: its final option is wrong and the key's option is right
- actually correct: its final option is right (the key is wrong, or both options are defensible as right)
- ambiguous: the question is unclear or more than one option is defensible
and write a one-line reason. Use any reference except AI assistants. Two readers per item, independently; a third
reader adjudicates disagreements. No model output may be recorded as a human annotation.
