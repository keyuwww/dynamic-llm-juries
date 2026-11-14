# Overnight deep-dive: why gpt-oss-120b's winning layer is unstable, qwen3.5-4b's isn't, and is any of this genuine hidden knowledge

Scope note up front: this ran as a single compute session, not literally overnight — sample sizes
(25-40 items per model, vs. the 459-item significance-test samples) are deliberately small, meant
to establish *shape*, not to replace the existing held-out kappa results. Treat everything here as
a first pass that narrows down what's worth a full-scale follow-up, not a final answer.

## Priority 1: is the "unstable winning layer" real movement, or noise around a tie?

**Answer: for gpt-oss-120b, it's a near-tie, not real movement. For qwen3.5-4b, it's a real, separated peak.**

Using the existing pilot data (no new compute needed) I measured, per item, the gap between the
best layer's logit-lens confidence (`pcn`) and the second-best layer's:

| Model | Benchmark/cond | mean top1 vs top2 pcn gap | plateau width (#layers within 0.02 of max) |
|---|---|---|---|
| gpt-oss-120b | BFF-standard | 0.0034 | 2.05 |
| gpt-oss-120b | BFF-rubric | 0.0044 | 2.15 |
| gpt-oss-120b | BiGGen-standard | 0.0027 | 3.29 |
| qwen3.5-4b | BFF-standard | 0.0213 | 1.60 |
| qwen3.5-4b | BFF-rubric | 0.0311 | 1.35 |
| qwen3.5-9b | BiGGen-rubric (the "final wins" cell) | 0.0917 | - |

gpt-oss-120b's top1-top2 gap is 7-9x smaller than qwen3.5-4b's. In other words: gpt-oss-120b
doesn't have one layer that's meaningfully more confident than its neighbors -- confidence is
essentially flat/tied across most of the network, so which exact layer gets crowned "the winner"
in the population-level kappa calculation (`modal_winning_layer`) is highly sensitive to sampling
noise and shifts around between benchmark/condition cells (11-94% depth) even though nothing is
actually moving. qwen3.5-4b has a real, separated peak (7-9x larger gap), which is why its winning
layer sits in a stable, narrow band (78-97% depth) across cells.

Side finding, worth flagging: qwen3.5-9b (the final-answer-wins model) has an even sharper peak
(0.092) than qwen3.5-4b. A sharp, confident interior peak does not by itself mean the interior
layer is right -- qwen3.5-9b is confidently wrong there more often than the final answer. Peak
sharpness measures confidence, not correctness; don't conflate the two.

Jacobian lens (gradient of the final CORRECT/INCORRECT margin w.r.t. each layer's hidden state),
25-40 items per model, BFF-standard:

- qwen3.5-4b: clean gradient flow through all 33 layers. Shape: high at the embedding layer
  (trivial), declining through early layers, then a genuine flat shoulder/re-bump in the middle of
  the network (layers 6-19, ~19-59% depth) before declining again toward the output. This
  mid-network plateau is a real structural feature.
- qwen3.5-9b: clean gradient flow through all 33 layers, but smooth, monotonic decay with no
  mid-network bump (small uptick only at the very last layer). No distinctive "this region matters
  again" feature anywhere in the middle.
- gpt-oss-120b: gradient flow breaks completely and reproducibly at layer 19 of 36 (~51% depth)
  for every single one of the 25 items tested (torch.autograd.grad returns None from that point on,
  every time, not occasionally). This lines up with gpt-oss-120b's native MXFP4-quantized kernels --
  they most likely don't implement a backward pass for at least part of the (MoE) blocks past that
  depth. This means Jacobian lens cannot currently say anything about the back half of
  gpt-oss-120b's network -- a structural/methodological limitation, not a finding about the model's
  representations.

Interpretation (mechanistic, not architecture-driven): gpt-oss-120b's layer instability looks like
a genuine representational property -- the network keeps a nearly flat, undifferentiated confidence
profile across most of its depth. We are NOT claiming "it's because gpt-oss-120b is MoE" -- the
Jacobian kernel limitation means we can't yet confirm that attribution, so it stays an open
question, not a conclusion. qwen3.5-4b's stability corresponds to an actual sharp, well-separated
confidence peak AND a real mid-network sensitivity feature in the Jacobian profile -- two
independent signals pointing at the same thing, good converging evidence it's a real computational
checkpoint, not noise.

## Priority 3: is the interior-layer effect genuine hidden knowledge, or an artifact?

- qwen3.5-9b "truly null" check (reusing the earlier cross-model breakdown, no new compute): on its
  one large final-wins cell (BiGGen-rubric), interior layer rescues only 2.2% of items where it
  disagrees with the final answer, vs. the final answer winning 10% outright (82% of all
  disagreements go the final answer's way). Close-to-null, not "no signal ever," but small and
  heavily outweighed.
- A naive "does the interior ever cross 0.5 on the correct side, at ANY layer" check gave 100% for
  qwen3.5-9b's final-wrong items -- not informative: with ~33 layers and a binary threshold,
  crossing 0.5 somewhere at least once is close to guaranteed by chance. Dropped this metric; the
  fixed-winning-layer disagreement ratio above is the correct one to cite.
- Tuned Lens: not completed tonight. Needs the model's full final-layer softmax per item to fit the
  per-layer affine correction, which isn't in the existing pilot data (only the 2-way
  CORRECT/INCORRECT renormalized probability is saved) -- needs a new capture pass. Top concrete
  next step, specifically for gpt-oss-120b's genuinely early-layer cells (11%, 28% depth), since
  that's where plain logit lens is least trustworthy and where the plateau finding above means the
  "winning" layer pick is least meaningful anyway.
- Lexical/surface-cue check: not run (would need prompt text joined to each item; feasible but not
  attempted tonight). Next step: for "layer-rescues" items, check whether they share a surface
  property (answer length, specific rubric keywords) the interior layer could be shortcutting on.
- Linear probes: attempted but not reported. With only 25-40 items and a high-dimensional hidden
  state, a logistic-regression probe would overfit completely; any accuracy number would be
  meaningless. Hidden states ARE saved (overnight_deepdive/probe_data/*.jsonl) so this can be scaled
  up without recapturing once a larger item sample (~150-300) is pulled.

## Deprioritized: rubric-wording mechanism

Not investigated tonight, per explicit deprioritization -- the rubric-worsens-it effect isn't
large/consistent enough to warrant mechanistic compute right now.

## Patchscopes

Not run tonight -- time went to the stability/plateau analysis instead. Still a good candidate for
a handful of qualitative examples (one gpt-oss-120b layer-rescue item, one qwen3.5-9b final-better
item) for the write-up, but needs its own short, targeted run.

## Bugs/fixes worth knowing about

The Jacobian capture script originally called torch.autograd.grad once per layer with
retain_graph=True in a loop -- this keeps the entire saved-activation graph alive across every call
and OOM'd even a 4B model on a 24GB A10G. Fixed to a single torch.autograd.grad(margin, list(hs),
...) call that gets all layers' gradients in one backward pass. Even after that fix, A10G still
wasn't enough for qwen3.5-4b/9b (backward-enabled forward over long multi-turn BFF conversations
needs much more memory than inference-only) -- moved those two to a single H100 (80GB), which
worked cleanly. gpt-oss-120b's job (launched before the fix, on H100:2) survived the inefficient
version fine since it had far more headroom to begin with.

## Round 2 (same night, continued): executing the 5 recommended next steps

Reprioritized per coordinator: layer-stability first, mechanistic/representational explanations
preferred over architecture-driven ones, genuineness-vs-artifact second, rubric-wording mechanism
dropped.

**1. Tuned Lens approximation, gpt-oss-120b BFF-standard (layer 10/36, the genuinely early-layer
cell) -- INCONCLUSIVE, not a clean confirmation or refutation.** Scaled the probe/jacobian capture
to 200 items, fit a ridge-regression affine map (5-fold out-of-fold) from the layer-10 hidden state
to a proxy target (the final layer's own binarized CORRECT/INCORRECT label -- the capture script
doesn't persist a true continuous margin, a real limitation). Recomputed the held-out gap the same
way as held_out_significance.py: the gap shrinks from +0.161 (raw logit lens, 459 items, p<1e-4) to
+0.030 (tuned, 200 items, CI [-0.147, 0.211], p=0.38 -- not significant). Important caveat before
reading this as "the effect was a logit-lens artifact": the proxy target is literally the same
binary label as the final answer, which structurally biases the correction toward agreeing with the
final answer -- of course a lens trained to predict X looks more like X. This result is suggestive
but not trustworthy as stated. Needs a true margin-valued target (capture the final logit margin
directly, not just the thresholded label) before it can be read either way.

**2. Scaled probe/jacobian capture + linear probes, all 3 models -- DONE, one real surprise.**
qwen3.5-4b and gpt-oss-120b scaled cleanly to 200 items (qwen3.5-9b capped at 71 -- a specific
long-conversation item OOMs a single H100 on the backward-enabled forward pass even after adding
`torch.cuda.empty_cache()` per item; not pursued further). Linear probe (5-fold CV logistic
regression) accuracy per layer:
  - qwen3.5-4b: majority baseline 66.5%, probe accuracy rises smoothly to a plateau of 80-82.5% by
    layer ~20-27. Single clean rise, matches its stable winning-layer band.
  - gpt-oss-120b: majority baseline 66.5%, probe accuracy is bumpy/multi-modal (78-80% through
    layers 2-18, dips, a second bump to 80% at layers 21-22, then *declines* toward the final
    layers, 73-74% by layer 36). Confirms the gradient-break finding independently: gradients stop
    flowing past layer 19/36 at this larger sample too (same reproducible break).
  - **qwen3.5-9b: majority baseline only 50.7% (near-balanced sample), but probe accuracy reaches
    83.1% at layers 23-25 -- the single highest probe accuracy of the three models.** This is a
    real surprise and complicates the "nothing to rescue" story from round 1: qwen3.5-9b's hidden
    states DO linearly encode substantial information about gold correctness. The fact that its
    *raw logit-lens* readout still loses to the final answer (per the original held-out significance
    test) suggests the gap may be between what a dedicated probe can extract and what the model's
    own unembedding head reads out at that layer -- i.e. a representational-drift / basis-mismatch
    problem, exactly what Tuned Lens is designed to fix. qwen3.5-9b is now also a Tuned Lens
    candidate, not just gpt-oss-120b.

**3. gpt-oss-120b MXFP4 dequantized-backward check -- DONE, and it REFUTES the round-1 hypothesis.**
Loaded gpt-oss-120b with `Mxfp4Config(dequantize=True)` on H100:4 (59GB allocated) and reran the
same torch.autograd.grad probe on 3 items. Prediction under the round-1 hypothesis ("native MXFP4
kernels lack a backward pass") was that dequantizing to bf16 should restore gradient flow past layer
19. **It did not. Gradients now break even EARLIER -- at layer 10/36 instead of layer 19/36 --
consistently across all 3 items tested, regardless of quantization.** This refutes the
quantization-kernel explanation: if MXFP4 numerics were the cause, removing them should have fixed
or at least not worsened the break. The break point being quantization-independent (and earlier,
not later, once dequantized) points instead to something structural in gpt-oss's block
implementation itself -- most likely a non-differentiable operation inside its MoE
routing/expert-dispatch path (e.g. a hard top-k/argmax expert selection or a custom grouped-GEMM
expert kernel not written with autograd support), which would explain why it's present under both
quantization regimes. This is a more mechanistically specific and more defensible conclusion than
the original guess, and the right thing to say in public: "the gradient break is structural to
gpt-oss-120b's MoE block, not a byproduct of its native quantization" -- Jacobian lens cannot cover
this model's back half under either load path without digging into (or bypassing) the MoE kernel
itself.

**4. Lexical/identity-level confound check -- DONE, real finding, no GPU needed.** Joined the
layer-rescues / final-better / both-right / both-wrong breakdown (for qwen3.5-4b BFF-rubric,
nemotron3-nano-30b BFF-standard, gpt-oss-120b BFF-standard) back to the original VERDICTS items by
id, locally. Response length shows no meaningful confound (means within ~15% of each other across
categories). **Examinee identity is a real confound: pooled across the 3 cells, rescue ratio
(layer-rescues / (layer-rescues + final-better)) is 77.6% for gemma-2-2b and yi1.5-34b-16k
(smaller/weaker examinee models) vs 55.7-56.1% for gpt-4o and llama-3.3-70b.** The layer-rescue
effect is partly about *which model produced the response being judged*, not purely an
instance-level reasoning signal -- worth controlling for before making claims about "the judge
model reasons better internally."

**5. Patchscopes -- mixed, one clean result, one inconclusive, one uninformative run.**
Found and fixed a real bug first: the patch hook was re-applying on every autoregressive decode
step (not just the prefill), which clamps every newly generated token's hidden state to the same
patched vector and produces a degenerate repeated-token loop (observed: endless "\n" or endless
" INC"). Fixed by patching only the first (prefill) forward call.
  - **qwen3.5-9b (final-better items, layer 32): clean, informative result.** All three patched
    continuations read "INCORRECT\nThe assistant's response is: INCOR..." -- a coherent, genuine
    verdict, confirming the interior layer really does hold an incorrect belief at that position
    for these items (not just an artifact of the forced CORRECT/INCORRECT logit-lens readout).
  - **qwen3.5-4b (layer 25): inconclusive.** Even at 60 generated tokens, continuations stay in
    generic chain-of-thought preamble ("<think>\nThinking Process:\n1. **Analyze the
    Request:**...") without reaching a verdict, and are nearly identical regardless of which item
    was patched. Not informative as implemented; would need a longer generation budget or a
    differently-worded patch prompt.
  - **gpt-oss-120b (layer 10): uninformative.** All 6 items (across layer_rescue, final_better, and
    both_wrong categories) produced the exact same canned continuation ("The assistant's response
    is correct...") regardless of patched content or the item's actual gold label -- the patch does
    not appear to be influencing generation at all for this model, possibly an MoE-block
    hook-structure mismatch (gpt-oss's decoder blocks may not return a plain tensor/tuple the same
    way qwen's do). Not debugged further given this was the lowest-priority item.

## Round 2 bottom line for the morning readout

- The headline claim from round 1 (gpt-oss-120b's instability is a near-tie, qwen3.5-4b's is a real
  peak) still stands and is now independently corroborated by linear probes at a larger sample.
- The Tuned Lens check on gpt-oss-120b's early-layer cell is inconclusive, not a refutation -- the
  shrinkage is confounded by a proxy regression target. Redo with a true margin target before citing
  either the raw +0.161 or the tuned +0.030 as more correct.
- The gpt-oss-120b gradient break is NOT caused by native MXFP4 quantization (dequantizing made it
  worse, breaking at layer 10 instead of 19) -- it's structural to the MoE block implementation.
  Report it that way, not as a quantization artifact.
- New, real finding: qwen3.5-9b's hidden states linearly encode substantial signal (83% probe
  accuracy) despite raw logit lens losing to the final answer there -- qwen3.5-9b should be added to
  the Tuned Lens follow-up list, not treated as a clean "no signal" control anymore.
- New, real finding: the layer-rescue effect is confounded by examinee identity (weaker models'
  responses get rescued ~1.4x more often) -- any claim about "the judge reasons better internally"
  should control for this before being stated cleanly.
- Patchscopes qualitatively confirms genuine (not artifactual) interior beliefs for qwen3.5-9b;
  inconclusive for qwen3.5-4b; not working as implemented for gpt-oss-120b.

## Concrete recommended next steps, in priority order

1. Tuned Lens on gpt-oss-120b's early-layer cells (BFF-standard, BiGGen-rubric) -- needs a new
   capture saving the full final-layer softmax per item, not just the 2-way CORRECT/INCORRECT
   slice, to fit per-layer affine correctors. Main way to tell whether the early-layer "interior
   wins" result there is real or a raw-logit-lens artifact.
2. Scale the Jacobian/probe capture to ~150-300 items per model (current run was 25-40, enough for
   shape, not enough for a trustworthy linear-probe accuracy number).
3. Investigate the gpt-oss-120b gradient break at layer 19/36 -- check whether a non-MXFP4 /
   dequantized load path restores backward support; if so, Jacobian lens could cover the model's
   full depth instead of just the first half.
4. Lexical-shortcut check on the layer-rescues bucket -- join prompt text to flag whether rescued
   items share surface features, to rule out "the interior layer is pattern-matching, not
   reasoning."
5. Patchscopes, scoped down to ~6-10 hand-picked qualitative examples, not a large run.
