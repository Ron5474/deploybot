# ── Stage 1: build React ──────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: runtime ──────────────────────────────────────────────────
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python deps (cached layer — only re-runs when lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY agent/   ./agent/
COPY backend/ ./backend/
COPY db/      ./db/
COPY rag/     ./rag/
COPY tools/   ./tools/

# Copy built frontend — served as static files by FastAPI
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Pre-download ChromaDB ONNX embedding model so it doesn't download at runtime
RUN uv run python -c "import chromadb; c = chromadb.Client(); c.get_or_create_collection('warmup').add(documents=['warmup'], ids=['1'])"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
