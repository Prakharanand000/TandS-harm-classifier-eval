"""The Robustness Review — FastAPI backend.

Serves the built React frontend and a small JSON API. The heavy model (Detoxify)
is deliberately NOT loaded here: its real numbers are precomputed into
data/*.json by scripts/precompute_web_data.py, so this service fits a free 512MB
tier. Live "type any text" scoring uses a lightweight lexical model, and a
Bloom-filter tier-0 pre-filter (prefilter.py) runs first.
"""
from __future__ import annotations

import json
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
# In the Docker image src/ is copied next to this file; locally it's at repo root.
SRC_ROOT = HERE if os.path.isdir(os.path.join(HERE, "src")) \
    else os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, SRC_ROOT)
sys.path.insert(0, HERE)
DATA = os.path.join(HERE, "data")
STATIC = os.path.join(HERE, "static")

from src.perturbations import EVASIONS, ZERO_WIDTH   # noqa: E402
from src.defenses import normalize_pipeline           # noqa: E402
from src.models import ToyClassifier                  # noqa: E402
from prefilter import prefilter                        # noqa: E402

# Lightweight live scorer (lexical). Detoxify numbers are precomputed, not live.
MODEL = ToyClassifier()
THREAT = {"kill", "hurt", "attack", "destroy", "die", "shoot", "stab", "burn"}
IDENTITY = {"muslim", "christian", "jewish", "black", "white", "asian", "gay",
            "lesbian", "trans", "woman", "women", "man", "men", "immigrant",
            "disabled", "hindu", "arab", "latino"}


def _load(name: str) -> dict:
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


BANK = _load("attack_bank.json")
SLICES = _load("slices.json")
CALIB = _load("calibration.json")

app = FastAPI(title="The Robustness Review API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


class TextIn(BaseModel):
    text: str


def _decision(score: float, t: float = 0.5) -> str:
    if score >= max(t, 0.7):
        return "FLAGGED"
    if score >= t - 0.15:
        return "BORDERLINE"
    return "CLEAN"


def _guess_slice(text: str) -> str:
    toks = {w.strip(".,!?\"'").lower() for w in text.split()}
    if toks & IDENTITY:
        return "identity-mentioning — watch for over- or under-flagging"
    if toks & THREAT:
        return "direct threat — the model usually catches these"
    return "general toxicity"


@app.get("/api/health")
def health():
    return {"ok": True, "live_model": "ToyClassifier (lexical)",
            "note": "real Detoxify numbers are precomputed; see /api/attack-bank"}


@app.post("/api/score")
def score(inp: TextIn):
    s = float(MODEL.predict_proba([inp.text])[0])
    return {"score": round(s, 3), "decision": _decision(s),
            "prefilter": prefilter(inp.text), "slice_guess": _guess_slice(inp.text),
            "model": "ToyClassifier (lexical, live)"}


@app.post("/api/attack")
def attack(inp: TextIn):
    base = float(MODEL.predict_proba([inp.text])[0])
    rows = []
    for nm, meta in EVASIONS.items():
        atk = meta["fn"](inp.text)
        sa = float(MODEL.predict_proba([atk])[0])
        sd = float(MODEL.predict_proba([normalize_pipeline(atk)])[0])
        rows.append({
            "evasion": nm, "effort": meta["effort"],
            "fluency_penalty": meta["fluency_penalty"],
            "disguised": atk.replace(ZERO_WIDTH, "·")[:80],
            "score_attacked": round(sa, 3),
            "evaded": bool(sa < 0.5 and base >= 0.5),
            "score_defended": round(sd, 3), "recovered": bool(sd >= 0.5),
        })
    rows.sort(key=lambda r: r["score_attacked"])
    return {"base": round(base, 3), "flagged": bool(base >= 0.5),
            "model": "ToyClassifier (lexical, live)", "rows": rows,
            "note": "Live scoring uses the lightweight lexical model. The Attack "
                    "Bank shows the same matrix on the real Detoxify model "
                    "(precomputed)."}


@app.get("/api/attack-bank")
def attack_bank():
    return BANK


@app.get("/api/slices")
def slices():
    return SLICES


@app.get("/api/calibration")
def calibration():
    return CALIB


# Serve the built React app (if present) at the root.
if os.path.isdir(STATIC):
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
