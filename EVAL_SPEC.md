# EVAL_SPEC — design spec

The deliverable is the **analyst memo**. The harness exists to produce it.
Register: decision-oriented, quantified, recommends actions, honest about
limits. That register is what reads as "T&S analyst" rather than "Kaggle
notebook."

## Part 1 — Memo structure

1. **Header + scope (2 lines)** — title, date, author, one-line scope.
2. **TL;DR (3–5 bullets, conclusions only)** — what leadership reads. Findings
   as decisions, with numbers. If someone reads only this, they know what you
   found and what you'd do.
3. **Scope, data & method** — model, dataset, label space, operating threshold
   (and *why*). One explicit data-ethics paragraph: public proxy chosen
   deliberately. That paragraph is a selling point, not a disclaimer.
4. **Aggregate performance** — P/R/F1 at threshold, PR curve, calibration. The
   "looks fine" baseline the next sections puncture.
5. **Subgroup / slice analysis — headline finding** — slice the metrics, surface
   the recall cliff aggregate hides, translate to absolute scale.
6. **Adversarial robustness** — evasion matrix results, framed by attacker cost.
   Lead with cheap-and-devastating. Recall before / under attack / defended.
7. **Error analysis (qualitative)** — representative FNs and FPs, what they
   reveal. Eyes on the data, not just the metric.
8. **Recommendations (prioritized, concrete)** — normalization preprocessor,
   threshold change with precision tradeoff stated, targeted data collection for
   the weak slice, evasion-augmented training, monitoring. Each pinned to a
   finding.
9. **Limitations & next steps** — honest gaps. Calibration reads as senior.

## Part 2 — Evasion test matrix

"Attacker cost" = effort + fluency penalty (how weird it looks to a human).
Low effort + low fluency penalty = top priority.

| Class | Transform | Example (`example`) | Cost (effort / fluency) | Hypothesized impact | Defense |
|---|---|---|---|---|---|
| Homoglyph | Latin → Cyrillic/Greek confusables | `еxаmplе` | low / low | severe on subword; low on byte | NFKC + confusable folding |
| Leetspeak | a4 e3 i1 o0 s5 t7 | `3x4mpl3` | low / low-med | high on subword | leet de-map |
| Spacing | separators between chars | `e x a m p l e` | low / med | high (breaks tokenization) | collapse char spacing |
| Punctuation | dot-separate chars | `e.x.a.m.p.l.e` | low / med | high | collapse char spacing |
| Zero-width | invisible char between chars | (invisible) | low / **zero** | high, stealthy | strip Cf chars |
| Diacritics | combining marks | `ĕx̃âmplé` | low / low-med | med-high | NFKD + strip Mn |
| Char typos | swap/delete/dup | `exmaple` | low / low | med | robust tokenizer / spell-norm |
| Word split | break tokens | `exam ple` | low / low | med-high | segmentation norm |
| Coded language | in-group code substitution | (lexical) | **med** / low | high (semantic) | evolving lexicon + embedding neighbors |
| Code-switching | embed term in another language | (mixed) | low-med / low | high if English-centric | multilingual model |
| Transliteration | romanize non-Latin term | (Hinglish) | low-med / low | high | transliteration norm |
| LLM paraphrase | rewrite, drop trigger tokens | (generated) | low / **zero** | high (defeats lexical) | semantic models, hard negatives |
| Implication | harm via implication | (generated) | med / zero | very high (hardest) | context-aware models |

Stretch (out of v1): **text-in-image (OCR bypass)** — severe on text-only
pipelines; defense is an OCR pre-pass.

## Measurement protocol

1. Pick the operating threshold; collect the true positives at baseline.
2. Per evasion, transform the caught set, rescore, compute **Evasion Success
   Rate** = share of caught items that now evade. Report post-attack recall.
3. Collateral check: apply benign-applicable transforms to true negatives,
   confirm FPR doesn't drift.
4. Plot ESR vs attacker cost → the cheap+effective quadrant is the priority.
5. Stack 2–3 cheap evasions; measure compound ESR.
6. Headline the single cheapest evasion that breaks the model.

## LLM red-team layer

Prompt an LLM to generate paraphrase/coded variants of held-out positives →
keep only label-preserving ones (LLM judge + human spot-check) → score
survivors. Misses become both the hardest test set and the recommended training
augmentation. Closes the find-fix loop without building a full agent.
