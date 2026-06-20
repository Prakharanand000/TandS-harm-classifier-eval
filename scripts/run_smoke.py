"""Offline smoke test: no network, no model downloads. Proves the whole harness
runs end to end and emits a real memo from synthetic data + the brittle
ToyClassifier. Run: python scripts/run_smoke.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data import make_synthetic
from src.models import ToyClassifier
from src.evaluate import run_evaluation
from src.report import render_memo, write_plots

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def main():
    df = make_synthetic(n=1200, seed=7)
    model = ToyClassifier()
    results = run_evaluation(model, df, threshold=0.5,
                             slice_cols=["language", "subgroup"])
    memo = render_memo(results, meta={
        "model_name": "ToyClassifier (keyword baseline)",
        "dataset_name": "synthetic proxy (smoke)",
        "author": "Prakhar Anand",
    })
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "MEMO_smoke.md"), "w") as f:
        f.write(memo)
    write_plots(results, OUT)

    b = results["baseline"]
    ws = results["headline"]["worst_slice"]
    cb = results["headline"]["cheapest_break"]
    print("=== SMOKE OK ===")
    print(f"aggregate: P={b['precision']:.2f} R={b['recall']:.2f} F1={b['f1']:.2f}")
    print(f"worst slice: {ws['column']}={ws['value']} recall={ws['recall']:.2f}")
    print(f"cheapest break: {cb['evasion']} ESR={cb['esr']:.2f} "
          f"recall_after={cb['recall_after']:.2f} "
          f"defended={cb['recall_after_defense']:.2f}")
    print(f"memo -> {os.path.join(OUT, 'MEMO_smoke.md')}")


if __name__ == "__main__":
    main()
