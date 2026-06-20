"""Evaluation orchestration: baseline -> slices -> adversarial -> error analysis.

Produces a single results dict consumed by report.py.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import metrics as M
from .defenses import normalize_pipeline
from .perturbations import EVASIONS


def run_evaluation(
    model,
    df: pd.DataFrame,
    threshold: float = 0.5,
    slice_cols: Optional[List[str]] = None,
    evasions: Optional[List[str]] = None,
    n_examples: int = 6,
    min_slice_support: int = 20,
) -> Dict:
    df = df.copy().reset_index(drop=True)
    slice_cols = slice_cols or [c for c in ("language", "subgroup", "identity_mention",
                                            "functionality") if c in df.columns]
    evasions = evasions or list(EVASIONS.keys())

    # ---- baseline -------------------------------------------------------- #
    df["score"] = model.predict_proba(df["text"].tolist())
    df["pred"] = M.binarize(df["score"].values, threshold)
    baseline = M.prf(df["label"].values, df["pred"].values)
    baseline["ece"] = M.expected_calibration_error(df["label"].values, df["score"].values)
    pr = M.pr_curve(df["label"].values, df["score"].values)

    # ---- slice analysis -------------------------------------------------- #
    slices = {
        col: M.slice_metrics(df, col, "score", "label", threshold)
        for col in slice_cols
    }

    # ---- adversarial robustness ------------------------------------------ #
    # Apply each evasion to the items the model CAUGHT at baseline, then rescore
    # both raw and after defensive normalization.
    pos = df[df["label"] == 1].copy()
    caught_mask = pos["score"].values >= threshold
    caught = pos[caught_mask].reset_index(drop=True)
    scores_before = caught["score"].values

    adversarial = []
    for name in evasions:
        fn = EVASIONS[name]["fn"]
        attacked = [fn(t) for t in caught["text"].tolist()]
        scores_after = model.predict_proba(attacked)
        esr = M.evasion_success_rate(scores_before, scores_after, threshold)

        # defended: normalize the attacked text, then rescore
        defended_text = [normalize_pipeline(t) for t in attacked]
        scores_def = model.predict_proba(defended_text)
        esr_def = M.evasion_success_rate(scores_before, scores_def, threshold)

        adversarial.append({
            "evasion": name,
            "effort": EVASIONS[name]["effort"],
            "fluency_penalty": EVASIONS[name]["fluency_penalty"],
            "esr": round(esr["esr"], 3),
            "recall_after": round(esr["recall_after"], 3),
            "recall_after_defense": round(esr_def["recall_after"], 3),
            "n_caught": esr["n_caught"],
        })
    adversarial = sorted(adversarial, key=lambda r: r["esr"], reverse=True)

    # ---- error analysis -------------------------------------------------- #
    fns = df[(df["label"] == 1) & (df["pred"] == 0)].head(n_examples)
    fps = df[(df["label"] == 0) & (df["pred"] == 1)].head(n_examples)
    errors = {
        "false_negatives": fns[["text", "score"] + slice_cols].to_dict("records"),
        "false_positives": fps[["text", "score"] + slice_cols].to_dict("records"),
    }

    # ---- headline detection ---------------------------------------------- #
    # Pick the worst-recall slice, but only among slices with enough POSITIVES to
    # make recall meaningful. Slices with support < min_slice_support (e.g. the
    # non-hateful HateCheck functionalities, which have zero positives) have a
    # trivially-0 recall that is not a real failure — including them would yield a
    # nonsensical "slice cliff". Those slices are a precision/FPR story, not recall.
    worst_slice = None
    for col, tbl in slices.items():
        sized = tbl[tbl["support"] >= min_slice_support]
        if sized.empty:
            continue
        cand = sized.sort_values("recall").iloc[0]
        if worst_slice is None or cand["recall"] < worst_slice["recall"]:
            worst_slice = {"column": col, "value": cand[col],
                           "recall": float(cand["recall"]),
                           "support": int(cand["support"])}
    cheapest_break = next(
        (r for r in adversarial
         if r["effort"] == "low" and r["fluency_penalty"] in ("zero", "low")),
        adversarial[0] if adversarial else None,
    )

    return {
        "threshold": threshold,
        "n": len(df),
        "baseline": baseline,
        "pr_curve": pr,
        "slices": {c: t.to_dict("records") for c, t in slices.items()},
        "adversarial": adversarial,
        "errors": errors,
        "headline": {"worst_slice": worst_slice, "cheapest_break": cheapest_break},
    }
