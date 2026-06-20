"""Real evaluation run: Detoxify + a real proxy dataset. Runs on YOUR machine
(needs network + `pip install -r requirements.txt`).

    python scripts/run_eval.py --dataset civil_comments --sample 5000
    python scripts/run_eval.py --dataset hatecheck

Add --redteam to fold an LLM-paraphrase (semantic) evasion row into the
adversarial table, alongside the mechanical character-level evasions. That
needs `pip install anthropic` and ANTHROPIC_API_KEY:

    python scripts/run_eval.py --dataset civil_comments --redteam --n-seeds 30

Produces outputs/MEMO.md plus PR-curve and cost-vs-impact plots (and, with
--redteam, outputs/redteam_variants.jsonl of label-preserving survivors).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import DetoxifyModel
from src.evaluate import run_evaluation
from src.report import render_memo, write_plots

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["civil_comments", "hatecheck"],
                    default="civil_comments")
    ap.add_argument("--sample", type=int, default=5000)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--variant", default="unbiased")
    ap.add_argument("--redteam", action="store_true",
                    help="add an LLM-paraphrase semantic-evasion row (needs API key)")
    ap.add_argument("--n-seeds", type=int, default=25,
                    help="caught harmful items to attack when --redteam (bounds cost)")
    ap.add_argument("--n-per", type=int, default=5,
                    help="paraphrase variants per seed when --redteam")
    ap.add_argument("--redteam-model", default="claude-sonnet-4-6",
                    help="Anthropic model for paraphrase + judge")
    args = ap.parse_args()

    identity_proxy = False
    if args.dataset == "civil_comments":
        from src.data import load_civil_comments
        df = load_civil_comments(sample=args.sample)
        slice_cols = [c for c in ("identity_mention",) if c in df.columns]
        # google/civil_comments ships no ground-truth identity columns, so the
        # loader derives identity_mention from a keyword proxy — disclose it.
        identity_proxy = "identity_mention" in df.columns
    else:
        from src.data import load_hatecheck
        df = load_hatecheck()
        slice_cols = ["functionality"]

    model = DetoxifyModel(args.variant)
    results = run_evaluation(model, df, threshold=args.threshold, slice_cols=slice_cols)

    os.makedirs(OUT, exist_ok=True)
    if args.redteam:
        if "ANTHROPIC_API_KEY" not in os.environ:
            sys.exit("--redteam needs ANTHROPIC_API_KEY (and `pip install anthropic`).")
        from src.redteam import evaluate_semantic_evasions
        rt = evaluate_semantic_evasions(
            model, df, threshold=args.threshold, n_seeds=args.n_seeds,
            n_per=args.n_per, llm_model=args.redteam_model,
        )
        if rt["row"] is not None:
            # inject the semantic row and keep the table sorted by ESR
            results["adversarial"].append(rt["row"])
            results["adversarial"].sort(key=lambda r: r["esr"], reverse=True)
            with open(os.path.join(OUT, "redteam_variants.jsonl"), "w",
                      encoding="utf-8") as f:
                for r in rt["records"]:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"redteam: {len(rt['records'])} variants kept "
                  f"(ESR {rt['row']['esr']}) -> redteam_variants.jsonl")
        else:
            print("redteam: 0 label-preserving variants — no row added.")

    meta = {
        "model_name": f"Detoxify ({args.variant})",
        "dataset_name": args.dataset,
        "author": "Prakhar Anand",
        "identity_proxy": identity_proxy,
    }
    # cache results so the memo can be re-rendered later without re-running inference
    from src import cache
    cache_path = os.path.join(OUT, f"{args.dataset}.results.json")
    cache.save(cache_path, results, meta)

    memo = render_memo(results, meta)
    memo_path = os.path.join(OUT, f"MEMO_{args.dataset}.md")
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo)
    write_plots(results, OUT)
    print(f"memo -> {memo_path}")
    print(f"cache -> {cache_path}")


if __name__ == "__main__":
    main()
