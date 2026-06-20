# harm-classifier-eval

A classifier **evaluation + adversarial-robustness harness** for content-safety
models. It measures aggregate precision/recall, slices the metrics to surface
the nuanced failure that aggregates hide, stress-tests the model against a
matrix of low-cost text evasions, and renders an **analyst memo** with concrete,
prioritized recommendations.

Built as a portfolio piece for Trust & Safety / abuse-detection analyst work.
The deliverable is the memo in `outputs/` — it reads like the actual work
product of the role, not a notebook dump.

📄 **Write-up:** [`PAPER.md`](PAPER.md) — *Below the Aggregate: Slice and
Adversarial Failure Modes of a Production Toxicity Classifier*, the working
paper with the full findings, figures, and method.

> **Data ethics.** This harness uses **public proxy data only** (ordinary
> toxic-comment / hate-speech datasets). It does not touch — and must not be
> pointed at — CSAM, NCII, or violent-extremism material, which can only be
> handled inside a sanctioned, legally-authorized pipeline. The *methods*
> transfer to production; the data deliberately does not.

## Interactive scanner

The fastest way to see what this does is the **robustness scanner** — an
interactive console (Streamlit) for a Trust & Safety reviewer to poke at:

```bash
pip install -r requirements-app.txt
streamlit run scripts/scanner_app.py
```

- **🔬 Live Attack Lab** — type any comment and watch every evasion attack it in
  real time: which cheap disguises slip it past the filter, and which a
  normalization defense recovers. Optional one-click LLM paraphrase attack.
- **📊 Scan Report** — a full prioritized weakness report for a real classifier,
  loaded from the committed result caches (no model download): aggregate metrics,
  the slice cliff, the cost-vs-impact adversarial chart, and a ranked fix list.
- **ℹ️ For Reviewers** — the scope, the methods-transfer-not-data stance, and why
  both error directions matter.

The Live Attack Lab defaults to the instant offline `ToyClassifier`; switch to
Detoxify (real model) in the sidebar locally. Public proxy data only.

## Quickstart

```bash
pip install -r requirements.txt

# 1) Offline smoke test — no network, no model download. Proves the pipeline
#    end to end on synthetic data and writes outputs/MEMO_smoke.md
python scripts/run_smoke.py

# 2) Real run — Detoxify on a real proxy dataset, writes outputs/MEMO_<dataset>.md
#    (and caches results to outputs/<dataset>.results.json)
python scripts/run_eval.py --dataset civil_comments --sample 5000
python scripts/run_eval.py --dataset hatecheck

# 3) Add semantic (LLM-paraphrase) evasions to the adversarial table.
#    Needs `pip install anthropic` + ANTHROPIC_API_KEY. The llm_paraphrase row
#    appears alongside the mechanical evasions in the memo, and the
#    label-preserving survivors are written to outputs/redteam_variants.jsonl.
python scripts/run_eval.py --dataset civil_comments --redteam --n-seeds 30

#    Or run the red-team pass standalone (its own memo + the same JSONL):
python scripts/run_redteam.py --dataset synthetic --n-seeds 8     # cheap wiring check
python scripts/run_redteam.py --dataset civil_comments --n-seeds 30

# 4) Re-render a memo from cache without re-running inference (fast iteration)
python scripts/render_memo.py --dataset hatecheck

# tests
python tests/test_all.py
```

## Results (real Detoxify run)

Findings from `Detoxify (unbiased)` at threshold 0.5 — the full memos are in
`outputs/MEMO_civil_comments.md` and `outputs/MEMO_hatecheck.md`.

**The pattern in one line:** aggregate F1 looks healthy (0.70–0.76), but every
layer of scrutiny below the aggregate finds a real failure.

| Dataset | Aggregate F1 | Hidden slice cliff | Cheapest mechanical break | Semantic (LLM) break |
|---|---|---|---|---|
| Civil Comments (n=1500) | 0.70 | `identity_mention` recall **0.56** vs 0.78 | `diacritics` ESR 1.0 (recovered to 0.99 by normalization) | `llm_paraphrase` ESR **0.57**, *not* recovered by normalization (0.43 → 0.43) |
| HateCheck (n=3728) | 0.76 | `derog_impl_h` (implicit derogation) recall **0.53** vs 0.77 | `stack_zw_homoglyph` ESR 1.0 (recovered to 0.97) | — |

Three things worth reading the memos for:

- **The slice cliff is the headline.** Aggregate metrics hide that the model
  misses ~47% of *implicit* hate (HateCheck `derog_impl_h`) and under-protects
  identity-mentioning comments (Civil Comments). Only slicing reveals it.
- **Mechanical vs semantic evasions diverge under defense.** Character tricks
  (homoglyph, leet, zero-width) are cheap but a normalization preprocessor
  recovers ~all lost recall. LLM paraphrases preserve intent with no surface
  trigger, so normalization *cannot* recover them — the fix is training-data
  augmentation, not preprocessing. The harness shows this side by side.
- **Calibration differs sharply** (ECE 0.022 on Civil Comments vs 0.226 on
  HateCheck) — a reminder that a threshold tuned on one distribution does not
  transfer.

> Numbers are from small samples for fast iteration; scale `--sample` for tighter
> estimates. The `identity_mention` slice on Civil Comments is a documented
> keyword proxy (the public dataset ships no identity labels) — see the memo.

## What it demonstrates

| Capability | Where | Maps to the JD |
|---|---|---|
| Precision/recall at an operating point, calibration | `src/metrics.py` | "analyze statistics (precision, recall)" |
| Slice analysis that surfaces a hidden recall cliff | `src/evaluate.py`, `slice_metrics` | "recognize nuanced, easily missed problems" |
| Evasion matrix (homoglyph, leet, zero-width, spacing, diacritics, typos, stacking, lexicon hooks) | `src/perturbations.py` | "knowledge of current abuse techniques" |
| Normalization defenses that recover lost recall | `src/defenses.py` | "improvement of detection systems / automation" |
| LLM red-team layer (label-preserving paraphrase evasions, folded into the adversarial table via `--redteam`) | `src/redteam.py`, `scripts/run_redteam.py` | proactive / emerging-harm detection |
| Memo with prioritized recommendations | `src/report.py` | "describe technical analyses to a non-tech audience" |

## Layout

```
src/
  perturbations.py  evasion matrix (composable, with cost metadata)
  defenses.py       normalization paired to each evasion
  metrics.py        prf, PR curve, slice metrics, ESR, ECE
  models.py         ToyClassifier (offline) + DetoxifyModel (real)
  data.py           synthetic generator + Civil Comments / HateCheck loaders
  evaluate.py       baseline -> slices -> adversarial -> error analysis
  report.py         renders the analyst memo + plots
  redteam.py        optional LLM paraphrase evasion layer
  cache.py          persist results so memos re-render without re-inference
scripts/
  run_smoke.py      offline end-to-end
  run_eval.py       real datasets + Detoxify (--redteam adds semantic evasions)
  run_redteam.py    standalone LLM-paraphrase red-team pass
  render_memo.py    re-render a memo from a cached results dict
tests/test_all.py
outputs/            generated memos + plots (gitignored: caches, evasion strings)
EVAL_SPEC.md        the design spec (memo structure + evasion matrix)
```

Detoxify inference is batched (`DetoxifyModel(batch_size=...)`) so large inputs
do not OOM on CPU. The red-team survivors (`outputs/redteam_variants.jsonl`) are
deliberately gitignored — publishing a list of evasions that bypass a live
classifier is a dual-use hazard; the methodology is shared, the working evasion
strings are not.

## The adversarial angle

The evasion matrix is the bridge from adversarial-behavior detection (the same
`Put1n` / `Ru$$ia` obfuscation logic from sanctions screening) to content
safety. Each evasion carries **cost metadata** (attacker effort + fluency
penalty); the report prioritizes the cheap, stealthy ones because those are what
real adversaries deploy. Every evasion is paired with a normalization defense,
and the harness reports recall *before attack / under attack / under attack +
defense*, so a recommendation is demonstrated rather than asserted.
