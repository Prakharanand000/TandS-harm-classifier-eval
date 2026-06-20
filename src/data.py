"""Datasets.

make_synthetic()      -- self-contained labeled data for the offline smoke run.
                         Carries `subgroup` and `language` columns so slice
                         analysis has something to find. Toxic items in the
                         `translit` language use tokens the English ToyClassifier
                         does not know, producing a reproducible recall gap that
                         mirrors the real-world non-English under-protection
                         failure.

load_civil_comments() -- real run. Has identity-group annotations, so the
                         documented identity-mention over-flagging effect is
                         reproducible as the headline subgroup finding.
load_hatecheck()      -- purpose-built functional contrast test suite.

The real loaders require network + `datasets`; they are documented and run on
your machine, not in the build sandbox.
"""
from __future__ import annotations

import random
import re
from typing import Optional

import pandas as pd

# Transparent identity-term lexicon used to build a *proxy* `identity_mention`
# slice when a dataset ships no ground-truth identity annotations (as the public
# google/civil_comments parquet does not). This is a documented heuristic, not a
# label: it flags whether a comment *mentions* a protected-attribute term, which
# is how production T&S teams cheaply approximate identity exposure. It will both
# miss coded references and over-count neutral mentions — stated as a limitation
# in the memo. Terms are deliberately non-slur, ordinary descriptors.
IDENTITY_TERMS = {
    # religion
    "muslim", "muslims", "islam", "islamic", "christian", "christians",
    "christianity", "jew", "jews", "jewish", "hindu", "hindus", "buddhist",
    "sikh", "atheist", "atheists",
    # race / ethnicity
    "black", "white", "asian", "latino", "latina", "hispanic", "arab",
    "african", "indian", "mexican", "immigrant", "immigrants",
    # gender / sexuality
    "woman", "women", "man", "men", "female", "male", "gay", "lesbian",
    "trans", "transgender", "lgbt", "lgbtq", "queer", "homosexual",
    # disability / age
    "disabled", "disability", "elderly",
}
_IDENTITY_RE = re.compile(r"\b(" + "|".join(sorted(IDENTITY_TERMS)) + r")\b", re.I)


def mentions_identity(text: str) -> bool:
    """True if the text mentions any protected-attribute term (proxy heuristic)."""
    return bool(_IDENTITY_RE.search(text or ""))

SUBGROUPS = ["group_a", "group_b", "group_c"]
NEUTRAL = [
    "I think the meeting went well today",
    "the weather is nice this afternoon",
    "let us discuss the project plan tomorrow",
    "thanks for sharing the report with the team",
    "the food at that place was pretty good",
]
TOXIC_EN = [
    "you are an idiot and everyone knows it",
    "what a stupid worthless take",
    "people like that are pathetic trash",
    "i hate this loser so much",
]
# Romanized / transliterated toxic items use tokens NOT in the English vocab,
# so a purely English lexical model misses them -> the language blind spot.
TOXIC_TRANSLIT = [
    "tu ek bewakoof insaan hai",
    "kitna bekaar aur faltu vichaar",
    "aise log toh ekdum ghatiya hote hain",
    "mujhe is nikamma se nafrat hai",
]


def make_synthetic(n: int = 1200, seed: int = 7) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        subgroup = rng.choice(SUBGROUPS)
        language = rng.choices(["en", "translit"], weights=[0.7, 0.3])[0]
        label = rng.random() < 0.4
        if label:
            pool = TOXIC_TRANSLIT if language == "translit" else TOXIC_EN
            text = rng.choice(pool)
        else:
            text = rng.choice(NEUTRAL)
        # weave in a subgroup mention so subgroup slicing is meaningful
        text = f"{text} ({subgroup.replace('_', ' ')})"
        rows.append({"text": text, "label": int(label),
                     "subgroup": subgroup, "language": language})
    return pd.DataFrame(rows)


def load_civil_comments(split: str = "test", sample: Optional[int] = 5000, seed: int = 0):
    """Real loader. Returns df[text, label, <identity columns>].
    Requires: pip install datasets ; network access.
    """
    from datasets import load_dataset  # lazy
    ds = load_dataset("google/civil_comments", split=split)
    df = ds.to_pandas()
    if sample:
        df = df.sample(min(sample, len(df)), random_state=seed).reset_index(drop=True)
    df["label"] = (df["toxicity"] >= 0.5).astype(int)
    # Prefer ground-truth identity annotations if the dataset carries them; the
    # public google/civil_comments parquet does not, so fall back to a documented
    # keyword proxy (see mentions_identity / IDENTITY_TERMS).
    ident_cols = [c for c in ["male", "female", "black", "white", "christian",
                              "muslim", "jewish", "homosexual_gay_or_lesbian"]
                  if c in df.columns]
    if ident_cols:
        flag = df[ident_cols].fillna(0).ge(0.5).any(axis=1)
    else:
        flag = df["text"].map(mentions_identity)
    df["identity_mention"] = flag.map({True: "mentions_identity",
                                       False: "no_identity"})
    return df


def load_hatecheck(seed: int = 0):
    """Real loader for the HateCheck functional test suite.
    Requires: pip install datasets ; network access.
    """
    from datasets import load_dataset  # lazy
    ds = load_dataset("Paul/hatecheck", split="test")
    df = ds.to_pandas()
    df["label"] = (df["label_gold"] == "hateful").astype(int)
    df = df.rename(columns={"test_case": "text", "functionality": "functionality"})
    return df[["text", "label", "functionality"]]
