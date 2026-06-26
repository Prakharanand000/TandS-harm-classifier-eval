"""Precompute real-Detoxify data for the web demo, LOCALLY.

Detoxify (RoBERTa, ~500MB) does not fit a free Render web service, so we bake the
real numbers into JSON here and ship those. The deployed backend then needs no
heavy model: it serves these files and runs only a lightweight live scorer.

    python scripts/precompute_web_data.py

Writes to web/backend/data/:
  calibration.json  threshold sweep (P/R/FPR) + reliability bins + ECE, per dataset
  slices.json       recall by slice + representative missed examples
  attack_bank.json  per-example mechanical evasion matrix (real Detoxify) + semantics
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DATA = os.path.join(ROOT, "web", "backend", "data")

from src.models import DetoxifyModel
from src.perturbations import EVASIONS, ZERO_WIDTH
from src.defenses import normalize_pipeline

# Mild, non-slur public-proxy stand-ins (the kind of toxicity in the datasets);
# deliberately no protected-class targeting or egregious content.
CURATED = [
    "you are an idiot and everyone knows it",
    "what a stupid worthless take",
    "i hate this loser so much",
    "people like that are pathetic trash",
    "shut up you moron nobody cares what you think",
    "you're so dumb it is painful to watch",
    "get lost you pathetic waste of space",
    "what a clueless brainless comment",
    "honestly you are the most useless person here",
    "nobody likes you and they never will",
]


def sweep(scores, labels, n=41):
    out = []
    for t in np.linspace(0.02, 0.98, n):
        pred = scores >= t
        tp = int(((pred) & (labels == 1)).sum())
        fp = int(((pred) & (labels == 0)).sum())
        fn = int(((~pred) & (labels == 1)).sum())
        tn = int(((~pred) & (labels == 0)).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        out.append({"t": round(float(t), 3), "precision": round(prec, 3),
                    "recall": round(rec, 3), "fpr": round(fpr, 3)})
    return out


def reliability(scores, labels, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    pts, ece, n = [], 0.0, len(scores)
    for i in range(bins):
        m = (scores >= edges[i]) & (scores < edges[i + 1])
        if not m.any():
            continue
        conf, acc = float(scores[m].mean()), float(labels[m].mean())
        pts.append({"conf": round(conf, 3), "acc": round(acc, 3), "n": int(m.sum())})
        ece += (m.sum() / n) * abs(conf - acc)
    return pts, round(float(ece), 4)


def main():
    os.makedirs(DATA, exist_ok=True)
    model = DetoxifyModel("unbiased")

    from src.data import load_civil_comments, load_hatecheck
    datasets = {
        "civil_comments": load_civil_comments(sample=1500),
        "hatecheck": load_hatecheck(),
    }

    calibration, slices = {}, {}
    for name, df in datasets.items():
        print(f"[{name}] scoring {len(df)} rows ...", flush=True)
        scores = np.asarray(model.predict_proba(df["text"].tolist()), dtype=float)
        labels = df["label"].values.astype(int)
        rel, ece = reliability(scores, labels)
        calibration[name] = {"n": int(len(df)), "ece": ece,
                             "sweep": sweep(scores, labels), "reliability": rel}

        # slice column: functionality (hatecheck) or identity_mention (civil)
        col = "functionality" if "functionality" in df.columns else \
              ("identity_mention" if "identity_mention" in df.columns else None)
        if col:
            rows, df2 = [], df.assign(_score=scores)
            for val, sub in df2.groupby(col):
                pos = sub[sub["label"] == 1]
                support = int(len(pos))
                if support == 0:
                    continue
                rec = float((pos["_score"] >= 0.5).mean())
                missed = pos[pos["_score"] < 0.5]["text"].head(4).tolist()
                rows.append({"slice": str(val), "support": support,
                             "recall": round(rec, 3),
                             "missed_examples": [m[:240] for m in missed]})
            rows.sort(key=lambda r: r["recall"])
            slices[name] = {"column": col, "overall_recall": round(float(
                (scores[labels == 1] >= 0.5).mean()), 3), "rows": rows}

    json.dump(calibration, open(os.path.join(DATA, "calibration.json"), "w"), indent=2)
    json.dump(slices, open(os.path.join(DATA, "slices.json"), "w"), indent=2)
    print("wrote calibration.json, slices.json", flush=True)

    # ---- attack bank: real Detoxify mechanical matrix per curated example ---- #
    print(f"attack bank: {len(CURATED)} examples x {len(EVASIONS)} evasions ...", flush=True)
    bank = []
    for ex in CURATED:
        base = float(model.predict_proba([ex])[0])
        attacks = []
        for nm, meta in EVASIONS.items():
            atk = meta["fn"](ex)
            sa = float(model.predict_proba([atk])[0])
            sd = float(model.predict_proba([normalize_pipeline(atk)])[0])
            attacks.append({
                "evasion": nm, "effort": meta["effort"],
                "fluency_penalty": meta["fluency_penalty"],
                "disguised": atk.replace(ZERO_WIDTH, "·")[:80],
                "score_attacked": round(sa, 3), "evaded": bool(sa < 0.5),
                "score_defended": round(sd, 3), "recovered": bool(sd >= 0.5),
            })
        attacks.sort(key=lambda a: a["score_attacked"])
        bank.append({"text": ex, "score_base": round(base, 3), "attacks": attacks})

    # Semantic evasions: clean, synthetic-vocabulary paraphrase pairs scored with
    # real Detoxify. We deliberately do NOT publish the real working evasions from
    # the red-team (dual-use); these hand-written pairs make the same point that a
    # fluent rewrite preserving intent is not recoverable by normalization.
    PARAPHRASES = [
        ("you are an idiot and everyone knows it",
         "you're absolutely clueless and the whole world can see it"),
        ("what a stupid worthless take",
         "what an utterly pointless and brainless opinion"),
        ("i hate this loser so much",
         "this absolute waste of space makes my blood boil"),
        ("people like that are pathetic trash",
         "folks of that sort are just sad little nobodies"),
        ("shut up you moron nobody cares",
         "be quiet, you simpleton, not a soul is interested"),
    ]
    semantic = []
    for orig, para in PARAPHRASES:
        s0 = float(model.predict_proba([orig])[0])
        s1 = float(model.predict_proba([para])[0])
        semantic.append({"original": orig, "variant": para,
                         "score_before": round(s0, 3), "score_after": round(s1, 3),
                         "evaded": bool(s1 < 0.5)})

    json.dump({"bank": bank, "semantic": semantic},
              open(os.path.join(DATA, "attack_bank.json"), "w"), indent=2)
    print(f"wrote attack_bank.json ({len(bank)} examples, {len(semantic)} semantic)", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
