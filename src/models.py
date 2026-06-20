"""Classifiers under evaluation.

ToyClassifier   -- a deliberately brittle keyword model used by the offline
                   smoke test. It fails the way real lexical models fail: it
                   has a language blind spot (it only knows English toxic
                   tokens) and it shatters under character-level evasions. That
                   makes the smoke run produce honest, real-looking findings
                   with zero network access.

DetoxifyModel   -- thin wrapper over the `detoxify` library (unbiased
                   checkpoint, trained on Civil Comments) for real runs. Lazily
                   imported so the smoke path never needs it installed.
"""
from __future__ import annotations

from typing import List

import numpy as np

# Mild, non-slur stand-in "toxic" tokens for the synthetic demo only.
TOXIC_WORDS_EN = {"idiot", "stupid", "loser", "worthless", "hate", "trash", "pathetic"}


class ToyClassifier:
    """Surface-token keyword scorer. Score 0.9 if any known toxic token is
    present (post simple lowercase/split), else 0.1, with light noise so PR
    curves are non-degenerate. Knows English tokens only -> language blind spot.
    """

    def __init__(self, vocab=None, seed: int = 0):
        self.vocab = set(vocab) if vocab else set(TOXIC_WORDS_EN)
        self._rng = np.random.default_rng(seed)

    def predict_proba(self, texts: List[str]) -> np.ndarray:
        scores = []
        for t in texts:
            toks = t.lower().split()
            hit = any(tok.strip(".,!?") in self.vocab for tok in toks)
            base = 0.9 if hit else 0.1
            scores.append(np.clip(base + self._rng.normal(0, 0.03), 0, 1))
        return np.array(scores)


class DetoxifyModel:
    """Wrapper over detoxify for real datasets. Requires `pip install detoxify`."""

    def __init__(self, variant: str = "unbiased", batch_size: int = 32):
        from detoxify import Detoxify  # lazy import
        self.model = Detoxify(variant)
        self.batch_size = batch_size

    def predict_proba(self, texts: List[str]) -> np.ndarray:
        # detoxify.predict() runs the WHOLE list as one padded batch, so a large
        # input allocates a huge activation tensor and OOMs on CPU. Chunk it to
        # bound peak memory; scores are identical, just computed batch-by-batch.
        texts = list(texts)
        scores: List[float] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            preds = self.model.predict(chunk)  # dict label -> list[score]
            scores.extend(preds["toxicity"])
        return np.array(scores)
