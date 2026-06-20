"""Evaluation metrics. Implemented on numpy/pandas so the harness runs with no
network and no heavy deps. Everything is computed at an explicit operating
threshold, because Trust & Safety lives at the operating point, not at AUC.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def binarize(scores: np.ndarray, threshold: float) -> np.ndarray:
    return (np.asarray(scores) >= threshold).astype(int)


def prf(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Precision, recall, F1 for the positive (harmful) class."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "precision": precision, "recall": recall, "f1": f1, "fpr": fpr,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "support": tp + fn,
    }


def pr_curve(y_true: np.ndarray, scores: np.ndarray, n: int = 50) -> List[Tuple[float, float, float]]:
    """Return [(threshold, precision, recall), ...] swept across score range."""
    out = []
    for t in np.linspace(0.01, 0.99, n):
        m = prf(y_true, binarize(scores, t))
        out.append((float(t), m["precision"], m["recall"]))
    return out


def expected_calibration_error(y_true: np.ndarray, scores: np.ndarray, bins: int = 10) -> float:
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    n = len(scores)
    for i in range(bins):
        mask = (scores >= edges[i]) & (scores < edges[i + 1])
        if not mask.any():
            continue
        conf = scores[mask].mean()
        acc = y_true[mask].mean()
        ece += (mask.sum() / n) * abs(conf - acc)
    return float(ece)


def slice_metrics(
    df: pd.DataFrame, slice_col: str, score_col: str, label_col: str, threshold: float
) -> pd.DataFrame:
    """Per-slice precision/recall/fpr at the operating threshold."""
    rows = []
    for value, sub in df.groupby(slice_col):
        m = prf(sub[label_col].values, binarize(sub[score_col].values, threshold))
        rows.append({
            slice_col: value, "n": len(sub), "support": m["support"],
            "precision": round(m["precision"], 3), "recall": round(m["recall"], 3),
            "fpr": round(m["fpr"], 3), "f1": round(m["f1"], 3),
        })
    return pd.DataFrame(rows).sort_values("recall").reset_index(drop=True)


def evasion_success_rate(
    scores_before: np.ndarray, scores_after: np.ndarray, threshold: float
) -> Dict[str, float]:
    """On items the model *caught* at baseline (score_before >= threshold),
    what fraction now evade (score_after < threshold)?
    """
    before = np.asarray(scores_before)
    after = np.asarray(scores_after)
    caught = before >= threshold
    n_caught = int(caught.sum())
    if n_caught == 0:
        return {"esr": 0.0, "n_caught": 0, "n_evaded": 0, "recall_after": 0.0}
    evaded = caught & (after < threshold)
    n_evaded = int(evaded.sum())
    return {
        "esr": n_evaded / n_caught,
        "n_caught": n_caught,
        "n_evaded": n_evaded,
        "recall_after": (n_caught - n_evaded) / n_caught,
    }
