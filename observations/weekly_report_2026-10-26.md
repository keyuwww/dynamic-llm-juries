# Weekly Report — 2026-10-26

## The short version

This week we tried to break our own result, and it held up.

## Background: what we're actually testing

Our project is about LLMs acting as judges — grading whether another model's answer is correct, safe, etc. We ran 7 judge models (from Qwen, Nemotron, gpt-oss, and DeepSeek families, ranging from 4B to 120B+ parameters) across 3 benchmarks (BFF-Bench, JudgeBench, and RewardBench2-Safety), 459 items each.

For every item, each model produces a final verdict, like any judge normally would. But we also do something extra: at every single layer of the model, before it's even finished "thinking," we take that layer's internal state and run it through the model's own final math (its norm + unembedding) to see what answer it *would* give if it stopped right there. This is called logit lens. It lets us watch the model's answer evolve layer by layer, instead of only seeing the final output.

## What we found

When we compare "the model's internal guess at its best layer" against "what the model actually said at the end," they don't always match — and sometimes the internal guess is *more* correct, by our human-labeled gold standard, than the model's real answer.

The clearest example is gpt-oss-120b: a layer in the back half of the network agrees with human labels noticeably more than the model's own final answer does. In other words, the information needed to get the right answer seems to be present inside the model earlier, but something happens between that layer and the final output that makes the model's actual answer worse. Several other models (Qwen3.5-4B, Qwen3.6-35B-A3B, gpt-oss-20b) show smaller versions of the same pattern; a couple show close to no gap at all.

That's an interesting finding, but it's also an easy one to fool yourself with: if you search across 24 to 88 layers looking for "the one that looks best," you'll find a good-looking layer even in pure random noise, just by chance. So this week's job was ruling that out.

## How we checked it

**Check 1 — held out validation.** We split each model/benchmark's 459 items into two random halves. We used only the first half to search for the best layer. Then, separately, we tested *that exact layer* — frozen, no more searching — against the second half, data it never got to influence the search. We repeated this with 20 different random splits. If the original effect were just noise, the gap should vanish or flip randomly across these 20 tries. It didn't: the gap kept pointing the same direction in the large majority of the 20 splits, for the models showing the effect.

**Check 2 — is it the same layer every time? (new this week).** We went further and asked a sharper question: across those 20 splits, does the *same specific layer* keep winning, or does the "best layer" jump around unpredictably each time? If it bounced around randomly, that would be a red flag that we're just picking up noise. What we found: for almost every model and benchmark, it's the same layer winning 19 or 20 times out of 20 — very stable. The one clear exception is nemotron3-super-120b, where the winning layer jumps around a lot — and that's also the model with the weakest effect to begin with. So the instability shows up exactly where the effect is weak, and the effect is stable exactly where it's strong. That consistency is a second, independent reason to trust the result rather than dismiss it as a search artifact.

## Other work this week

We also did a cleanup pass on the write-up itself: trimmed a lot of over-explaining and self-justifying sentences, simplified a confusing 9-row chart (which mixed two different rubric conditions) down to one clean row per model, fixed a bug where the published version of the report had lost all its styling, and added a simple diagram showing how the logit-lens method and the held-out validation work, placed right before the results.

## What we skipped

We considered testing whether this effect is caused specifically by instruction tuning (i.e., would a base, non-chat version of the same model show it too?). We decided not to run this: every judge model we actually care about for the project is already instruction-tuned, so the answer wouldn't change what we do next. Not worth the extra GPU time.

## Open for next week

- Two of our three benchmarks are tested on a smaller sample (459 items) than they actually contain in full (JudgeBench has 620, RewardBench2-Safety has 1800). Extending to the full sets would need new GPU runs — worth the cost, or is 459 good enough?
- One figure (a CoCoNot-based rubric replication) might be more confusing than it's worth as currently presented. Keep it with clearer explanation, cut it, or fold it into the main results figure?
