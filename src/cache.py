"""Persist a run's results so the memo can be re-rendered without re-running
inference. Detoxify on CPU is the slow part; with a cache, every later tweak to
report.py is instant via scripts/render_memo.py.

The results dict carries numpy scalars (scores, metrics); they are coerced to
native Python types so the cache is plain JSON.
"""
from __future__ import annotations

import json

import numpy as np


def _default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def save(path: str, results: dict, meta: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "results": results}, f, default=_default, indent=2)


def load(path: str):
    """Return (results, meta) from a cache file."""
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return d["results"], d["meta"]
