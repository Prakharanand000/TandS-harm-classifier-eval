# Deploy to Render

The app is a single Docker web service defined in `render.yaml` (a Render Blueprint).
One-time setup takes about 5 minutes; every subsequent `git push` auto-deploys.

## First deploy

1. Go to <https://render.com> and sign in (or create a free account).
2. Click **New → Blueprint**.
3. Connect your GitHub account if you haven't already.
4. Select the **`TandS-harm-classifier-eval`** repository.
5. Render reads `render.yaml` and shows the `robustness-review` service. Click **Apply**.
6. Wait ~5–8 minutes for the first build (it builds the React frontend inside the Docker
   image, then starts FastAPI).
7. Your live URL: **`https://robustness-review.onrender.com`**

The health-check endpoint is `/api/health` — Render uses this to confirm the service
is up before routing traffic.

## What's in the image

The Dockerfile at `web/backend/Dockerfile` is a two-stage build:

| Stage | What it does |
|---|---|
| `node-builder` | `npm ci && npm run build` — compiles the React frontend into `web/backend/static/` |
| `python-runner` | Installs the Python deps, copies `src/` and the precomputed JSON, runs `uvicorn` |

The final image is Python-only (~200 MB). Detoxify is **not** installed — the model
numbers are precomputed and shipped as JSON in `web/backend/data/`. This keeps the
image under Render's free-tier 512 MB RAM limit.

## Environment variables

No secrets required for the base demo. If you want live LLM paraphrase attacks in the
Attack Lab (currently served from a precomputed bank), add:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |

Add it in Render → your service → **Environment** → **Add environment variable**.

## Auto-deploy

`render.yaml` sets `autoDeploy: true`. Every push to `main` triggers a new build
automatically. You can disable this in Render → your service → **Settings →
Auto-Deploy**.

## Free-tier notes

- Render free web services spin down after 15 minutes of inactivity. The first request
  after a cold start takes ~20–30 seconds while the container wakes up. If you want
  always-on, upgrade to the Starter plan ($7/mo) or set up an uptime-ping service (e.g.
  UptimeRobot hitting `/api/health` every 10 minutes).
- Build minutes are generous on the free tier for a repo this size.

## Retiring the old Hugging Face Space

The Streamlit app at `streamlit_app.py` now shows a redirect page pointing to
`https://robustness-review.onrender.com`. To push that retirement page to HF:

```bash
# from repo root — push the updated streamlit_app.py to the HF Space remote
git remote add space https://huggingface.co/spaces/prakharanand85/harm-classifier-scanner
git push space main
```

Or simply set the Space to **Private** or **Delete** it from the HF web UI:
Spaces → your space → Settings → Delete.
