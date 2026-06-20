"""Run: python -m pytest tests/ -q   (or: python tests/test_all.py)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import perturbations as P
from src import defenses as D
from src import metrics as M
from src.evaluate import run_evaluation


class _MarkerModel:
    """Scores high iff 'BAD' is in the text — enough to drive run_evaluation."""
    def predict_proba(self, texts):
        return np.array([0.9 if "BAD" in t else 0.1 for t in texts])


def test_homoglyph_changes_and_folds_back():
    s = "example"
    h = P.homoglyph(s)
    assert h != s
    assert D.fold_confusables(h) == s


def test_zero_width_invisible_and_stripped():
    s = "example"
    z = P.zero_width(s)
    assert P.ZERO_WIDTH in z
    assert D.strip_zero_width(z) == s


def test_leet_roundtrip_basic():
    assert P.leetspeak("test") == "7357"
    assert D.de_leet("7357") == "test"


def test_compose_stacks():
    f = P.compose(P.leetspeak, P.zero_width)
    out = f("test")
    assert P.ZERO_WIDTH in out


def test_prf_known_values():
    y_true = [1, 1, 0, 0]
    y_pred = [1, 0, 0, 0]
    m = M.prf(y_true, y_pred)
    assert m["precision"] == 1.0
    assert m["recall"] == 0.5
    assert round(m["f1"], 3) == 0.667


def test_evasion_success_rate():
    before = [0.9, 0.9, 0.2]   # two caught at thr=0.5
    after = [0.1, 0.9, 0.1]    # one of the caught now evades
    r = M.evasion_success_rate(before, after, 0.5)
    assert r["n_caught"] == 2
    assert r["n_evaded"] == 1
    assert r["esr"] == 0.5


def test_headline_ignores_zero_support_slices():
    # 'nh' slice: all negatives -> support 0, recall trivially 0 (NOT a real cliff).
    # 'h'  slice: 10 positives, model catches 6 -> recall 0.6 (the real worst slice).
    rows = []
    rows += [{"text": "ok", "label": 0, "func": "nh"} for _ in range(5)]
    rows += [{"text": "BAD", "label": 1, "func": "h"} for _ in range(6)]
    rows += [{"text": "ok", "label": 1, "func": "h"} for _ in range(4)]
    df = pd.DataFrame(rows)
    res = run_evaluation(_MarkerModel(), df, threshold=0.5,
                         slice_cols=["func"], min_slice_support=5)
    ws = res["headline"]["worst_slice"]
    assert ws is not None
    assert ws["value"] == "h", f"picked zero-support slice: {ws}"
    assert ws["support"] == 10
    assert round(ws["recall"], 3) == 0.6


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"\n{len(fns)} tests passed")
