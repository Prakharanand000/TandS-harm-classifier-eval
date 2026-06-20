"""Adversarial text perturbations for evaluating harm-classifier robustness.

Each perturbation maps clean text -> evaded text. Functions are pure and
composable, so evasions can be stacked. The EVASIONS registry carries cost
metadata (effort, fluency penalty) that drives the cost-vs-impact
prioritization in the report: low effort + low fluency penalty = the evasions
real adversaries actually deploy, so those are the ones that matter most.

Demo transforms are shown in the docstrings on the neutral word ``example`` so
the mechanics are unambiguous and no offensive content is needed to illustrate.
"""
from __future__ import annotations

import random
import unicodedata
from typing import Callable, Dict, List

# --------------------------------------------------------------------------- #
# Character maps
# --------------------------------------------------------------------------- #

# Latin -> visually identical Cyrillic/Greek codepoints (Unicode confusables).
# NFKC does NOT fold these (they are distinct scripts, not compatibility
# characters), which is exactly why naive normalization fails to defend.
HOMOGLYPHS: Dict[str, str] = {
    "a": "\u0430",  # CYRILLIC SMALL A
    "c": "\u0441",  # CYRILLIC SMALL ES
    "e": "\u0435",  # CYRILLIC SMALL IE
    "i": "\u0456",  # CYRILLIC SMALL BYELORUSSIAN-UKRAINIAN I
    "j": "\u0458",  # CYRILLIC SMALL JE
    "o": "\u043e",  # CYRILLIC SMALL O
    "p": "\u0440",  # CYRILLIC SMALL ER
    "s": "\u0455",  # CYRILLIC SMALL DZE
    "x": "\u0445",  # CYRILLIC SMALL HA
    "y": "\u0443",  # CYRILLIC SMALL U
}
CONFUSABLE_REVERSE: Dict[str, str] = {v: k for k, v in HOMOGLYPHS.items()}

LEET: Dict[str, str] = {
    "a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "b": "8",
}
LEET_REVERSE: Dict[str, str] = {v: k for k, v in LEET.items()}

ZERO_WIDTH = "\u200b"          # ZERO WIDTH SPACE
COMBINING_ACUTE = "\u0301"     # COMBINING ACUTE ACCENT


# --------------------------------------------------------------------------- #
# Character-level evasions
# --------------------------------------------------------------------------- #

def homoglyph(text: str, rate: float = 1.0, seed: int = 0) -> str:
    """Substitute Latin chars with confusable Cyrillic. ``example`` -> ``\u0435x\u0430mpl\u0435``."""
    rng = random.Random(seed)
    return "".join(
        HOMOGLYPHS[ch] if ch in HOMOGLYPHS and rng.random() < rate else ch
        for ch in text
    )


def leetspeak(text: str) -> str:
    """Digit/letter substitution. ``example`` -> ``3x4mpl3``."""
    return "".join(LEET.get(ch, ch) for ch in text.lower())


def space_injection(text: str, sep: str = " ") -> str:
    """Insert a separator between every character within each word.

    ``example`` -> ``e x a m p l e``. Whole-string spacing breaks word-piece
    tokenization while staying human-readable.
    """
    return " ".join(sep.join(w) for w in text.split(" "))


def punct_injection(text: str) -> str:
    """Dot-separate characters. ``example`` -> ``e.x.a.m.p.l.e``."""
    return space_injection(text, sep=".")


def zero_width(text: str) -> str:
    """Insert an invisible zero-width space between characters. Visually identical
    to the original; zero fluency penalty, which is what makes it dangerous."""
    return ZERO_WIDTH.join(text)


def diacritics(text: str) -> str:
    """Overlay combining acute accents. ``example`` -> ``\u0435\u0301x\u0301...``."""
    return "".join(ch + COMBINING_ACUTE if ch.isalpha() else ch for ch in text)


def typos(text: str, seed: int = 0, rate: float = 0.15) -> str:
    """Character-level swap / delete / duplicate noise. ``example`` -> ``exmaple``."""
    rng = random.Random(seed)
    chars = list(text)
    out: List[str] = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        if ch.isalpha() and rng.random() < rate:
            op = rng.choice(("swap", "delete", "dup"))
            if op == "swap" and i + 1 < len(chars):
                out.append(chars[i + 1]); out.append(ch); i += 2; continue
            if op == "delete":
                i += 1; continue
            if op == "dup":
                out.append(ch); out.append(ch); i += 1; continue
        out.append(ch); i += 1
    return "".join(out)


def word_split(text: str, seed: int = 0) -> str:
    """Split long tokens with a space. ``example`` -> ``exam ple``."""
    rng = random.Random(seed)
    out = []
    for w in text.split(" "):
        if len(w) > 4:
            p = rng.randint(2, len(w) - 2)
            out.append(w[:p] + " " + w[p:])
        else:
            out.append(w)
    return " ".join(out)


# --------------------------------------------------------------------------- #
# Lexicon-driven evasions (coded language / code-switching / transliteration)
# --------------------------------------------------------------------------- #
# These are semantic, not mechanical: they require a mapping of in-group codes.
# The harness exposes them as hooks that take a lexicon so the evasion stays
# honest about what it does. Provide your own mapping or generate one with the
# LLM red-team layer (src/redteam.py).

def lexicon_substitute(text: str, lexicon: Dict[str, str]) -> str:
    """Replace terms with coded variants / cross-lingual equivalents.

    ``lexicon`` maps surface term -> coded form (e.g. a romanized or
    in-group-coded token). Case-insensitive whole-word replacement.
    """
    if not lexicon:
        return text
    out = []
    for w in text.split(" "):
        out.append(lexicon.get(w.lower(), w))
    return " ".join(out)


# --------------------------------------------------------------------------- #
# Composition / stacking
# --------------------------------------------------------------------------- #

def compose(*funcs: Callable[[str], str]) -> Callable[[str], str]:
    """Stack evasions: ``compose(leetspeak, zero_width)`` applies left to right."""
    def _apply(text: str) -> str:
        for fn in funcs:
            text = fn(text)
        return text
    return _apply


# --------------------------------------------------------------------------- #
# Registry with cost metadata
# --------------------------------------------------------------------------- #
# effort:          how hard for an adversary to apply (low/med/high)
# fluency_penalty: how weird it looks to a human reader (zero/low/med/high)
# A low/low or low/zero cell is a top-priority threat.

EVASIONS: Dict[str, Dict] = {
    "homoglyph":       {"fn": homoglyph,       "effort": "low", "fluency_penalty": "low"},
    "leetspeak":       {"fn": leetspeak,       "effort": "low", "fluency_penalty": "low-med"},
    "space_injection": {"fn": space_injection, "effort": "low", "fluency_penalty": "med"},
    "punct_injection": {"fn": punct_injection, "effort": "low", "fluency_penalty": "med"},
    "zero_width":      {"fn": zero_width,      "effort": "low", "fluency_penalty": "zero"},
    "diacritics":      {"fn": diacritics,      "effort": "low", "fluency_penalty": "low-med"},
    "typos":           {"fn": typos,           "effort": "low", "fluency_penalty": "low"},
    "word_split":      {"fn": word_split,      "effort": "low", "fluency_penalty": "low"},
}

# Cheap, stealthy stacked attack: invisible + visually-identical.
EVASIONS["stack_zw_homoglyph"] = {
    "fn": compose(homoglyph, zero_width),
    "effort": "low", "fluency_penalty": "zero",
}
