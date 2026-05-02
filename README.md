# DeployBot

An AI assistant for self-hosting open-source applications. Ask it to generate docker-compose files, look up CVEs, find self-hosted alternatives to popular services, and walk through complete setup guides — all backed by a RAG knowledge base built from hundreds of real app READMEs.

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

### Semantic Cache

A ChromaDB-based cache returns stored responses for semantically similar queries (cosine distance threshold).

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
- An OpenAI-compatible LLM endpoint (Ollama, vLLM, OpenRouter, etc.)

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
uv run python data/scraper.py

# Embed README chunks and app catalog into ChromaDB
uv run python rag/embed.py
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
