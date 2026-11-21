# Human label check: math replication (not yet done)

66 wrong-labelled responses, stratified by the highest belief any judge has in them (every response at 7/7
and 4-6; 20 each at 1-3 and 0/7; population sizes in key.json). Start with the 7/7 and 4-6 items. Readers get
items.jsonl only (or the annotation page), never key.json.

For each item, decide whether the response the DAPO-Math key marks WRONG really has a wrong final integer:
- clearly wrong: its final integer is wrong and the key's integer is right
- actually correct: its final integer is right (the key is wrong)
- ambiguous: the problem is unclear or admits more than one defensible answer
and write a one-line reason (a short derivation where the key is disputed). Use any reference or computation except
AI assistants. Two readers per item, independently; a third reader adjudicates disagreements. No model output may be
recorded as a human annotation.
