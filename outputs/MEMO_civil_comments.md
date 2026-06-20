# Evaluation memo: Detoxify (unbiased) on civil_comments
_Author: Prakhar Anand | Scope: aggregate performance, subgroup failure modes, adversarial robustness | Operating threshold: 0.5_

## TL;DR
- Aggregate F1 is **0.70** (precision 0.67, recall 0.73) at threshold 0.5 — the headline looks healthy.
- That aggregate **masks a slice cliff**: `identity_mention=mentions_identity` recall is **0.56** vs 0.73 overall (gap 0.17; ~1,733,333 missed items/period at 10,000,000-item volume).
- A **low-cost evasion** (`stack_zw_homoglyph`, effort low, fluency penalty zero) drops recall to **0.01** (ESR 0.99); defensive normalization recovers it to 0.99.
- Recommended: ship the normalization preprocessor, re-collect labels for the weak slice, and monitor slice recall as a guardrail metric.

## Scope, data & method
Model evaluated: **Detoxify (unbiased)**. Dataset: **civil_comments** (n=1500). Operating threshold 0.5, chosen for the precision/recall trade-off shown below (T&S operates at the operating point, not at AUC). Calibration: ECE 0.022.

> **Data ethics.** No real egregious-harms content was used. Public proxy data was chosen deliberately: handling CSAM / NCII / violent extremism material outside a sanctioned, legally-authorized pipeline is neither lawful nor responsible. The methods transfer directly to the production setting; the data does not.

## Aggregate performance
| precision | recall | f1 | fpr | support |
| --- | --- | --- | --- | --- |
| 0.667 | 0.733 | 0.698 | 0.032 | 120 |

## Subgroup / slice analysis — headline finding

**By `identity_mention`:**

| identity_mention | n | support | precision | recall | fpr |
| --- | --- | --- | --- | --- | --- |
| mentions_identity | 178 | 25 | 0.7 | 0.56 | 0.039 |
| no_identity | 1322 | 95 | 0.661 | 0.779 | 0.031 |

> `identity_mention` here is a **keyword proxy** (does the comment mention a protected-attribute term?), not a ground-truth identity label — the public dataset carries none. It under-counts coded references and over-counts neutral mentions, so read the gap as indicative, not precise.

The `identity_mention=mentions_identity` slice is the failure aggregate metrics hide: recall **0.56** on 25 positives. At production volume that gap is ~1,733,333 missed items/period at 10,000,000-item volume — the kind of nuanced, easily-missed problem that only appears once you slice.

## Adversarial robustness
Each evasion is applied to items the model caught at baseline. ESR = share of caught items that now evade. `recall_after_defense` is recall once the normalization pipeline is applied first.

| evasion | effort | fluency pen. | ESR | recall (attacked) | recall (defended) |
| --- | --- | --- | --- | --- | --- |
| diacritics | low | low-med | 1.0 | 0.0 | 0.989 |
| stack_zw_homoglyph | low | zero | 0.989 | 0.011 | 0.989 |
| leetspeak | low | low-med | 0.977 | 0.023 | 0.966 |
| homoglyph | low | low | 0.943 | 0.057 | 0.989 |
| word_split | low | low | 0.602 | 0.398 | 0.364 |
| llm_paraphrase | high | zero | 0.571 | 0.429 | 0.429 |
| zero_width | low | zero | 0.568 | 0.432 | 0.989 |
| typos | low | low | 0.364 | 0.636 | 0.636 |
| punct_injection | low | med | 0.068 | 0.932 | 0.216 |
| space_injection | low | med | 0.023 | 0.977 | 0.193 |

`llm_paraphrase` is a **semantic** evasion (LLM reword, judged label-preserving), not a character trick. Note its `recall (defended)` barely improves on `recall (attacked)`: normalization removes surface obfuscation but cannot reverse a fluent rewrite. That row is the case for training-data augmentation over preprocessing — its survivors are written to `outputs/redteam_variants.jsonl`.

## Error analysis (qualitative)
_Representative false negatives (missed harmful):_
- `No Mr. Crum, you have no right to tell me what to do.  It is often that you presume that you do.  Remember you reported to the police a comment I made about the killing of a professor.  I said that there likely was some personal connection between killer and victim.  You interpreted this to be sexual abuse and demanded that I report anything I know to the police and eventually, you emailed that police about my comment.  Your bullying was exceptional.  But this is not about you or me.  It is about acceptable procedure for state schools in dealing with citizens.  Time will tell what will happen.  There are many abuses within and victims of our system.  You see them on street corners with signs, living along the river, etc.  You think Trump is a sociopath.  But you are apparently happy as a clam when the system destroys lives.` (score 0.34)
- `In our parliamentary system we elect Members, not parties. Floor crossing is part of our system.

Let's compare your view and mine:

Here in Alberta, Jason Kenney is running for the PC leadership on a platform of collapsing 2 parties and moving everyone over to a merged conservative-not-centrist-like-the-PCs party. Details of his plan are sketchy at this point, but all versions of the Kenney plan require many Alberta MLAs to switch parties.

So Layla4, in your view should the entire Wild Rose and PC contingents in the Alberta Legislature stand down for by-elections when that happens??? Or would you argue that voters don't require consultation in that case? (and why not?)

BTW Jason Kenney used to be very vocal, expressing opinions similar to your own. Fortunately for Kenney, hypocrisy is part of his life condition.` (score 0.13)
- `All this from the party that turned a blind eye to all the bimbo eruptions and but helped tirelessly in the bimbo destructions, and that defended the cigar insertions in the oval office, and the interns' kneed pleasuring of him while he is on the phone with a congressman talking about troops in Bosnia, and the consequent killing of innocent people - warmongering -  to force the nation to focus away from his abuse of power and sexual molestation (assault or rape if he had been a republican) of his female staffer.  Malignant.  Right  Bernstein's mouth is open grave..` (score 0.16)
- `Worst President ever. Obama has brought the world closer to WW3, without providing any proof of hacking.` (score 0.46)
- `"We can turn out all the black votes you want," Reed, chairman of the ADC, said in a telephone interview. "But somebody's got to talk to the white voters; it's not our challenge to do that. We can talk to everybody, but white voters got to hear from white folks."

And we conservatives are the racists?? Unbelievable...` (score 0.43)

_Representative false positives (over-flagged benign):_
- `The popular vote thing is a stupid argument. Have you not seen the breakdown by county, of who won each county vs who lost. It's literally all red except LA, Sanfransico, Chicago, New York. Litterially she only won an area that would fit inside the kenai peninsula. If you subtract the LA and New York City votes from both Trump and Clinton, Clinton looses the popular vote by almost 1/2 a million. So stop the ignorance wine about popular vote, unless you stand for United States of California??` (score 0.93)
- `The alpha-sheep is one baaah-d @ss herd animal for sure.` (score 0.67)
- `1. Reply to William (Bill) T. Pirtle - Yes, all you need is a station very near your house and a station where you normally go.  People need multiple stations so they are fairly easy to get to.  2. Pedestrian Bill  -- Sorry, stupidity is against the law all the time.  What do you think traffic laws are or for that matter most other laws.  Pedestrians are getting more and more distracted and causing more and more risks o injury or death for everybody using the roads.` (score 0.63)
- `re: XKR: Yes, and if you do find a nice quiet windy road in the country some local jerk gets right on your bumper because they think they are such hot drivers because they know exactly how fast they can push each corner and when it is critical to slow down to a crawl. Funny thing is that they never pass and if you pull over they slow right down because they are afraid of getting a ticket.
Really looking forward to driverless cars.` (score 0.52)
- `sniff
whats that stink?
you need a shower` (score 0.56)

## Recommendations
1. **Ship a normalization preprocessor** (zero-width strip, NFKC, confusable folding, combining-mark strip, char-spacing collapse, de-leet) ahead of the classifier. The table above shows it recovers most recall lost to cheap character-level evasions.
2. **Close the `identity_mention` gap**: targeted label collection and training augmentation for the `mentions_identity` slice; route to a language-aware / multilingual model where applicable.
3. **Augment training data** with the surviving adversarial variants (including LLM-generated paraphrases) as hard negatives.
4. **Monitor slice recall as a guardrail**, not just aggregate F1, so the next blind spot is caught in metrics rather than in the wild.

## Limitations & next steps
- Proxy data understates production distribution shift and the hardest (implicit / context-dependent) harms.
- Semantic evasions (coded language, paraphrase) need the LLM red-team layer and human label-preservation checks to evaluate properly.
- Next: extend to multimodal (text-in-image OCR bypass) and add conversation-level context signals.
