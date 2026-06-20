"""LLM red-team pass: semantic (label-preserving) evasions, not just mechanical.

Where `run_eval.py` perturbs caught harmful items at the character level
(homoglyphs, leet, zero-width, ...), this driver asks an LLM to *paraphrase*
them — coded synonyms, code-switching, rewording — while preserving the harmful
intent, then keeps only the variants a judge confirms are still label-preserving.
The survivors the detector misses are simultaneously the hardest test set and
the recommended training-augmentation data.

Paraphrase + judge run on the Anthropic API (`src/redteam.py`), so this needs
`pip install anthropic` and ANTHROPIC_API_KEY in the environment.

    # cheap end-to-end wiring check: local ToyClassifier, ~a few dozen API calls
    python scripts/run_redteam.py --dataset synthetic --n-seeds 8

    # the real thing: Detoxify under semantic attack on a proxy dataset
    python scripts/run_redteam.py --dataset civil_comments --sample 5000 --n-seeds 30

Produces outputs/MEMO_redteam.md and outputs/redteam_variants.jsonl.
API cost is bounded by --n-seeds x --n-per (default 25 x 5 = 125 generate calls
plus one judge call per generated variant); start small.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.redteam import evaluate_semantic_evasions

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def load_dataset_and_model(args):
    """Mirror run_eval's dataset choices; synthetic uses the offline ToyClassifier
    so the red-team wiring can be exercised without a Detoxify download."""
    if args.dataset == "synthetic":
        from src.data import make_synthetic
        from src.models import ToyClassifier
        return make_synthetic(n=600, seed=7), ToyClassifier(), "synthetic proxy"
    from src.models import DetoxifyModel
    model = DetoxifyModel(args.variant)
    if args.dataset == "civil_comments":
        from src.data import load_civil_comments
        return load_civil_comments(sample=args.sample), model, "civil_comments"
    from src.data import load_hatecheck
    return load_hatecheck(), model, "hatecheck"


def _table(rows, cols, headers=None):
    headers = headers or cols
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["synthetic", "civil_comments", "hatecheck"],
                    default="synthetic")
    ap.add_argument("--sample", type=int, default=5000,
                    help="rows to sample for real datasets before seed selection")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--variant", default="unbiased", help="Detoxify checkpoint")
    ap.add_argument("--n-seeds", type=int, default=25,
                    help="caught harmful items to attack (bounds API cost)")
    ap.add_argument("--n-per", type=int, default=5,
                    help="paraphrase variants requested per seed")
    ap.add_argument("--model", default="claude-sonnet-4-6",
                    help="Anthropic model for paraphrase + judge")
    args = ap.parse_args()

    if "ANTHROPIC_API_KEY" not in os.environ:
        sys.exit("ANTHROPIC_API_KEY is not set. The red-team layer needs it; "
                 "export it (and `pip install anthropic`) before running.")

    df, model, dataset_name = load_dataset_and_model(args)
    res = evaluate_semantic_evasions(
        model, df, threshold=args.threshold, n_seeds=args.n_seeds,
        n_per=args.n_per, llm_model=args.model,
    )
    if res["n_seeds"] == 0:
        sys.exit("No caught harmful items to attack — nothing for the red-team to do.")
    records = res["records"]
    if not records:
        sys.exit("Generated 0 label-preserving variants — try more seeds or n-per.")
    esr, esr_def = res["esr"], res["esr_def"]
    n_seeds = res["n_seeds"]

    # --- write the training-augmentation artifact ----------------------------- #
    os.makedirs(OUT, exist_ok=True)
    jsonl_path = os.path.join(OUT, "redteam_variants.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- memo ----------------------------------------------------------------- #
    n_evaders = sum(r["evaded"] for r in records)
    survivors = [r for r in records if r["evaded"]][:8]
    L = []
    L.append(f"# Red-team memo: semantic evasions vs {dataset_name}")
    L.append(f"_Author: Prakhar Anand | Attack: LLM paraphrase ({args.model}), "
             f"label-preservation judged | Operating threshold: {args.threshold}_\n")
    L.append("## What this adds over the mechanical adversarial table")
    L.append("`run_eval.py` measures character-level evasions (homoglyphs, leet, "
             "zero-width). Those are defeated by normalization. This pass measures "
             "**semantic** evasions: reworded, code-switched, coded paraphrases that "
             "carry the same harmful intent but share no surface trigger tokens — so "
             "normalization cannot touch them. A judge model discards variants that "
             "drifted off-label, so ESR here reflects genuine label-preserving misses.\n")
    L.append("## Result")
    L.append(_table([{
        "seeds": n_seeds,
        "variants_kept": len(records),
        "evaders": n_evaders,
        "ESR": round(esr["esr"], 3),
        "recall_attacked": round(esr["recall_after"], 3),
        "recall_defended": round(esr_def["recall_after"], 3),
    }], ["seeds", "variants_kept", "evaders", "ESR",
         "recall_attacked", "recall_defended"]))
    L.append("\n> Note: `recall_defended ≈ recall_attacked` is the *expected* and "
             "important result — semantic evasions are not recovered by the "
             "normalization preprocessor, which is exactly why they matter. The fix is "
             "data (augment training with these survivors), not preprocessing.\n")
    if survivors:
        L.append("## Representative label-preserving evaders")
        for r in survivors:
            L.append(f"- `{r['variant']}` (score {r['score_raw']:.2f}) "
                     f"— from: `{r['original']}`")
        L.append("")
    L.append("## Use the survivors")
    L.append(f"All {len(records)} kept variants are written to "
             "`outputs/redteam_variants.jsonl` (original, variant, scores, evaded "
             "flag). The evaders are hard positives: fold them into the training set "
             "as augmentation and re-evaluate. This closes the loop the limitations "
             "section of the main memo calls out.\n")
    memo = "\n".join(L)
    memo_path = os.path.join(OUT, "MEMO_redteam.md")
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo)

    print("=== RED-TEAM OK ===")
    print(f"seeds={n_seeds} variants_kept={len(records)} evaders={n_evaders}")
    print(f"ESR={esr['esr']:.2f} recall_attacked={esr['recall_after']:.2f} "
          f"recall_defended={esr_def['recall_after']:.2f}")
    print(f"memo     -> {memo_path}")
    print(f"variants -> {jsonl_path}")


if __name__ == "__main__":
    main()
