# Build context is the REPO ROOT (so we can copy src/). See render.yaml.

# ---- stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

# ---- stage 2: python backend serving the API + built frontend ----
FROM python:3.11-slim
WORKDIR /app
COPY web/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY web/backend/ ./
COPY --from=frontend /backend/static ./static
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
