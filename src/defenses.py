"""Normalization defenses paired to the evasion matrix.

Each evasion in perturbations.py has a corresponding normalization here. The
harness measures recall (a) at baseline, (b) under attack, and (c) under attack
+ normalization, so the report can show that the recommended preprocessing step
actually recovers the lost recall. That before/after recovery is the analyst
recommendation made concrete rather than asserted.
"""
from __future__ import annotations

import re
import unicodedata

from .perturbations import CONFUSABLE_REVERSE, LEET_REVERSE, ZERO_WIDTH


def fold_confusables(text: str) -> str:
    """Map known confusable codepoints back to Latin. NFKC will NOT do this."""
    return "".join(CONFUSABLE_REVERSE.get(ch, ch) for ch in text)


def strip_zero_width(text: str) -> str:
    """Remove zero-width and other format (Cf) control characters."""
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def strip_combining(text: str) -> str:
    """Decompose and drop combining marks (Mn)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def collapse_char_spacing(text: str) -> str:
    """Re-join runs of single characters: ``e x a m p l e`` -> ``example``.

    Heuristic: collapse separators that sit between single alphanumeric chars.
    Leaves genuine word boundaries intact.
    """
    # collapse single-char . or space separators between letters
    text = re.sub(r"(?<=\w)[.\s](?=\w(?:[.\s]\w)+)", "", text)
    # second pass for the trailing pair
    text = re.sub(r"(?<=\w)[.\s](?=\w$)", "", text)
    return text


def de_leet(text: str) -> str:
    """Reverse common leet substitutions (lossy heuristic)."""
    return "".join(LEET_REVERSE.get(ch, ch) for ch in text)


def normalize_pipeline(text: str) -> str:
    """Full defensive normalization, applied before the classifier sees text."""
    text = strip_zero_width(text)
    text = unicodedata.normalize("NFKC", text)
    text = fold_confusables(text)
    text = strip_combining(text)
    text = collapse_char_spacing(text)
    text = de_leet(text)
    return text
