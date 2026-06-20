"""Re-render a memo (and plots) from a cached results dict — no re-inference.

Run an eval once (which writes outputs/<dataset>.results.json), then iterate on
report.py formatting as fast as you like:

    python scripts/render_memo.py --dataset hatecheck
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import cache
from src.report import render_memo, write_plots

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True,
                    help="basename of the cache, e.g. civil_comments or hatecheck")
    args = ap.parse_args()

    cache_path = os.path.join(OUT, f"{args.dataset}.results.json")
    if not os.path.exists(cache_path):
        sys.exit(f"No cache at {cache_path}. Run scripts/run_eval.py first.")

    results, meta = cache.load(cache_path)
    memo = render_memo(results, meta)
    memo_path = os.path.join(OUT, f"MEMO_{args.dataset}.md")
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo)
    write_plots(results, OUT)
    print(f"memo -> {memo_path}")


if __name__ == "__main__":
    main()
