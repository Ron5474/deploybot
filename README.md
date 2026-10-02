# DeployBot

An AI assistant for self-hosting open-source applications. Ask it to generate docker-compose files, look up CVEs, find self-hosted alternatives to popular services, and walk through complete setup guides — all backed by a RAG knowledge base built from hundreds of real app READMEs.

---

## For reviewers

DeployBot is a FastAPI + LangGraph agent that answers self-hosting questions using a SQL app catalog, a RAG index of app READMEs, CVE lookup, and web search.

The files most worth reading:

| File | What to look at |
|---|---|
| `agent/guardrail.py` | Output redaction of secrets, including `StreamRedactor`, which redacts a token stream without ever emitting part of a secret |
| `agent/agent.py` | The four prompting strategies: ReAct streaming, self-reflection, prompt chaining, meta-prompting |
| `tools/db_tool.py` | Running LLM-written SQL safely: SELECT-only parse check plus a read-only database connection |
| `rag/embed.py` | Chunking READMEs by heading and indexing them into ChromaDB |
| `backend/app.py` | The streaming `/chat` endpoint and how redaction and persistence fit around it |

Run the tests (no API keys or LLM needed):

```bash
uv sync && uv run pytest
```

---

## Features

### Four Prompting Strategies

Switch strategies from the UI to trade speed for quality:

| Strategy | How it works |
|---|---|
| **Regular** | LangGraph ReAct agent streams a response in real time |
| **Self-Reflection** | Agent produces an answer, then the LLM reviews and corrects it before returning |
| **Prompt Chaining** | Breaks docker-compose generation into four sequential steps: identify services → generate blocks → merge → security harden |
| **Meta-Prompting** | LLM internally classifies the query and selects the best approach before answering |

### Agent & Tools

The ReAct agent picks from four tools per turn:

- **App database** — SQL search over 400+ self-hosted apps (name, category, license, language)
- **Vector search** — semantic search over README documentation chunks for setup guides, env vars, ports, and troubleshooting
- **CVE lookup** — live queries to the NIST NVD API for known vulnerabilities
- **Web search** — Tavily search for current information, latest image tags, and recent releases

### Deployment Checklist

When the assistant returns a docker-compose file, a checklist is automatically generated for that specific configuration — covering secrets hardening, exposed ports, volume backups, TLS setup, and service-specific gotchas. Checklist state persists across page refreshes.

### Conversation History

- Conversations are persisted per-browser via a `client_id` stored in localStorage
- Sidebar groups history by Today / Yesterday / Older
- Conversations can be loaded, deleted, or exported as Markdown
- Last response can be regenerated

### Chat UI

- Streaming responses for the regular strategy
- Markdown rendering with syntax-highlighted code blocks and one-click copy
- Smart scroll: auto-scrolls to the bottom during streaming but stays put if the user scrolls up to read earlier content
- Auto-growing textarea input (Enter to send, Shift+Enter for new line)

### LangChain Response Cache

Repeated identical prompts are served from a local SQLite cache, skipping the LLM entirely.

### Semantic Cache (benchmarked, not in the request path)

`rag/semantic_cache.py` is a ChromaDB-based semantic caching layer: it returns a stored response when a new query is close enough to a cached one (distance threshold). It is exercised only by `eval/benchmark_semantic_cache.py`, which measures cold vs. warm latency. It is not yet wired into `/chat`.

Why not: the cache is keyed only on the question text. A follow-up like "what about with Postgres?" means something different in every conversation, so the cache would need to be scoped per conversation before it is safe to serve from it.

---

## Tech Stack

**Backend:** Python 3.12, FastAPI, LangGraph, LangChain, ChromaDB, SQLite, Tavily  
**Frontend:** React 19, Vite, react-markdown, react-syntax-highlighter, lucide-react  
**Infra:** Docker, uv

---

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- Node.js 20+
- A Tavily API key — [tavily.com](https://tavily.com) (free tier available)
- A GitHub personal access token (only needed if you re-run the scraper)
- An OpenAI-compatible LLM endpoint (Ollama, vLLM, OpenRouter, etc.)

### Obtain API keys

**Tavily** (required — used by the web search tool):

1. Sign up at [app.tavily.com](https://app.tavily.com). The free tier includes ~1,000 requests/month.
2. From the dashboard, copy the API key (starts with `tvly-`).
3. Paste it into `.env` as `TAVILY_TOKEN`.

**GitHub personal access token** (only needed to re-run `data.scraper`):

1. Go to [github.com/settings/tokens/new](https://github.com/settings/tokens/new) (classic tokens).
2. Set a note like `deploybot scraper` and pick an expiration.
3. Under **Select scopes**, check `public_repo` (inside the `repo` group). No other scopes are needed — the scraper only reads public README files.
4. Click **Generate token** and copy the value (it will not be shown again).
5. Paste it into `.env` as `GITHUB_ACCESS_TOKEN`.

> A fine-grained token also works: give it **public repositories (read-only)** access with no account permissions.

### 1. Clone and configure

```bash
git clone https://github.com/Ron5474/deploybot.git
cd deploybot
cp .env.example .env
```

Edit `.env` and fill in your model URL, API keys, and Tavily token. See the [Environment Variables](#environment-variables) section for details.

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Build the app catalog and knowledge base

These steps populate the SQLite app database and ChromaDB vector store. Only needed once (or when you want to refresh the data).

```bash
# Scrape app metadata from awesome-selfhosted and fetch READMEs
# Requires GITHUB_ACCESS_TOKEN in your .env
uv run python -m data.scraper

# Embed README chunks and app catalog into ChromaDB
uv run python -m rag.embed
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Run

**Development** (frontend dev server + backend separately):

```bash
# Terminal 1 — backend
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Frontend runs at `http://localhost:5173`, proxying API calls to the backend at port 8000.

**Production** (backend serves the compiled frontend):

```bash
cd frontend && npm run build && cd ..
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

---

## Docker

### Build and run locally

```bash
cp .env.example .env   # fill in your keys first
docker-compose up --build
```

Open `http://localhost:8000`.

> **Note:** The app database and vector store are mounted as volumes from your local directory. Run steps 3 from the local setup above before starting the container if you haven't already, so the data files exist on the host.

### Volumes

The compose file mounts the following from the repo root so data persists across container restarts:

| Volume | Purpose |
|---|---|
| `./apps.db` | Self-hosted app catalog |
| `./conversation_history.db` | Chat history |
| `./rag/chroma_db` | Vector store |
| `./.langchain_cache.db` | LLM response cache |
| `./data/readme_cache` | Cached app READMEs |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values below.

| Variable | Required | Description |
|---|---|---|
| `MODEL_BASE_URL` | Yes | Base URL of an OpenAI-compatible LLM API |
| `MODEL_API_KEY` | Yes | API key for the main model |
| `MODEL_NAME` | Yes | Model name/identifier |
| `SMALL_MODEL_API_KEY` | Yes | API key for the small/fast model |
| `SMALL_MODEL_NAME` | Yes | Small model name (used in benchmarks) |
| `TAVILY_TOKEN` | Yes | Tavily API key for web search |
| `GITHUB_ACCESS_TOKEN` | Scraper only | GitHub token for fetching app READMEs (`read:public_repo` scope) |
| `DISABLE_CACHE` | No | Set to any value to disable the LangChain SQLite cache |

---

## Evaluation

```bash
# Compare large vs small model quality and latency across 20 queries
uv run python -m eval.benchmark_models

# Benchmark LangChain response cache hit speedup
uv run python -m eval.benchmark_cache

# Benchmark semantic cache hit rate and latency
uv run python -m eval.benchmark_semantic_cache

# Run prompt injection security tests
uv run python -m eval.security_tests
```
