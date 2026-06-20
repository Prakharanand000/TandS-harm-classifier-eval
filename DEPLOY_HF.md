# Deploying the scanner to Hugging Face Spaces

The interactive scanner (`scripts/scanner_app.py`) deploys to a free Hugging
Face **Space** as a Streamlit app. A Space *is* a git repo, so the flow is:
create the Space, push this project to it, done.

## 1. Create the Space

1. Sign in at <https://huggingface.co> → **New** → **Space**.
2. Name it e.g. `harm-classifier-scanner`.
3. **SDK: Streamlit.** Hardware: **CPU basic (free)**. Visibility: Public.
4. Create.

## 2. Give the Space its config

A Space reads its settings from a YAML header at the top of `README.md`, and its
Python deps from `requirements.txt`. Put these two files in the Space.

**`README.md`** (the header is what HF reads; keep or edit the body):

```markdown
---
title: Harm-Classifier Robustness Scanner
emoji: 🛡️
colorFrom: red
colorTo: gray
sdk: streamlit
sdk_version: 1.56.0
app_file: streamlit_app.py
pinned: false
license: mit
---

Interactive robustness scanner for content-safety classifiers. Type a comment
and watch evasions attack it live, or read a full weakness report. Public proxy
data only — a methodology demonstrator, not an egregious-harms detector.
See the code: https://github.com/Prakharanand000/TandS-harm-classifier-eval
```

**`requirements.txt`** (light — fast build, free-tier friendly):

```
streamlit>=1.30
altair>=5.0
pandas>=2.0
numpy>=1.26
# Optional: uncomment to run the real Detoxify model live in the Live Attack Lab
# (heavier build, needs the larger free CPU space). The Scan Report already shows
# real Detoxify results from the committed caches without this.
# detoxify>=0.5.2
```

## 3. Push the project to the Space

From this repo, add the Space as a second remote and push (replace the URL with
your Space's git URL, shown under the Space's **⋮ → Clone repository**):

```bash
git remote add space https://huggingface.co/spaces/<your-username>/harm-classifier-scanner
git push space main
```

The Space needs `streamlit_app.py`, `src/`, `scripts/scanner_app.py`, and
`outputs/*.results.json` (the committed caches that power the Scan Report) — all
already in this repo. The only files to adjust on the Space side are the two
above: ensure its `README.md` has the YAML header and its `requirements.txt` is
the light list (the repo's default `requirements.txt` is the heavier full-eval
one; overwrite it on the Space, or keep it if you want the live Detoxify option
and don't mind a longer build).

HF will build and serve automatically. First load takes a minute.

## 4. Safety note — do not expose your API key

The Live Attack Lab's optional LLM-paraphrase feature reads `ANTHROPIC_API_KEY`.
The app auto-hides it when no key is set, so a public Space simply runs without
it. **Do not** add your key as a public Space secret — leave the feature off in
the public demo.
