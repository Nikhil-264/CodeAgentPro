# CodeAgent Pro 🤖

An agentic AI coding assistant with a self-repair loop — generates code, tests it, debugs itself, and refactors until it works.

## Architecture

```
User Task
   ↓
RAG Context Fetch    → Retrieves relevant docs, codebase, past fixes
   ↓
Planner Agent        → Breaks task into sub-tasks
   ↓
Code Generator       → Writes the code (via Ollama)
   ↓
Execution Sandbox    → Runs code in Docker (isolated)
   ↓
Test Generator       → Writes Pytest tests
   ↓
┌─ Debug Loop ────────────────────────────────────────────┐
│  Run Tests → Fail → RAG Error Memory → Debugger → Repeat│
│             Pass → exit loop                            │
└─────────────────────────────────────────────────────────┘
   ↓
Refactor Agent       → Cleans up working code
   ↓
Final Code ✅
```

All agents are orchestrated via **LangGraph** as a compiled state graph with conditional edges.

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (Optional: used for secure containerized execution sandboxing; falls back to local execution if missing/not running)
- [Ollama](https://ollama.com) installed

---

## Setup

### 1. Pull the coding model
```bash
ollama pull deepseek-coder:6.7b
```

### 2. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the backend
```bash
cd backend
python main.py
```

API: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

### 4. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:3000

### 5. Or run everything with Docker
```bash
cd docker
docker compose up --build
```

Backend → :8000 | Frontend → :3000

---

## RAG Setup (optional but recommended)

Seed the docs store with built-in FastAPI / Pytest / Python snippets:
```bash
curl -X POST http://localhost:8000/api/rag/seed-docs
```

Index your own project into the codebase store:
```bash
curl -X POST http://localhost:8000/api/rag/index-project \
  -H "Content-Type: application/json" \
  -d '{"directory": "./backend"}'
```

Check what's stored:
```bash
curl http://localhost:8000/api/rag/stats
```

---

## API Usage

### Quick code generation (no tests, no debug loop)
```bash
curl -X POST http://localhost:8000/api/generate/quick \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a function to check if a string is a palindrome"}'
```

### Full pipeline with real-time streaming (SSE)
```bash
curl -X POST http://localhost:8000/api/generate/stream \
  -H "Content-Type: application/json" \
  -d '{"task": "Build a REST API for a todo list using FastAPI"}'
```

### Request body options
```json
{
  "task": "your task here",
  "language": "Python",
  "framework": "standard library",
  "model": "deepseek-coder:6.7b",
  "skip_tests": false,
  "skip_refactor": false
}
```

### Check available Ollama models
```bash
curl http://localhost:8000/api/models
```

### Check Ollama health
```bash
curl http://localhost:8000/api/health/ollama
```

---

## Project Structure

```
codeagent-pro/
├── README.md
├── backend/
│   ├── main.py                   # FastAPI entry point
│   ├── requirements.txt
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py            # Task decomposition
│   │   ├── code_generator.py     # LLM code generation
│   │   ├── test_generator.py     # Pytest suite generation
│   │   ├── debugger.py           # Self-repair loop core
│   │   └── refactor.py           # Code quality pass
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm_client.py         # Ollama async client
│   │   ├── prompts.py            # All prompt templates
│   │   ├── sandbox.py            # Docker execution engine
│   │   ├── state.py              # LangGraph shared state
│   │   ├── nodes.py              # LangGraph node functions
│   │   ├── graph.py              # LangGraph compiled graph
│   │   └── pipeline.py           # Thin SSE adapter
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py             # FastAPI endpoints + RAG routes
│   └── rag/
│       ├── __init__.py
│       ├── base_store.py         # ChromaDB base class
│       ├── codebase_store.py     # Project file indexing
│       ├── docs_store.py         # Library documentation
│       ├── error_memory_store.py # Past bug→fix memory
│       └── rag_manager.py        # Single RAG interface
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx               # Main layout + config panel
│       ├── index.css             # Design system + all styles
│       ├── useAgent.js           # SSE streaming hook + state
│       └── components/
│           ├── PipelineBar.jsx   # Animated agent progress bar
│           ├── TerminalLog.jsx   # Real-time event stream
│           └── CodeViewer.jsx    # Syntax-highlighted code + copy
└── docker/
    ├── docker-compose.yml
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── nginx.conf
```

---

## Build Stages

| Stage | Feature | Status |
|-------|---------|--------|
| 1 | MVP — Prompt to code via Ollama | ✅ Done |
| 2 | Docker execution sandbox | ✅ Done |
| 3 | Pytest test generation | ✅ Done |
| 4 | Self-repair debug loop | ✅ Done |
| 5 | RAG — codebase + docs + error memory | ✅ Done |
| 6 | LangGraph multi-agent orchestration | ✅ Done |
| 7 | React frontend with terminal viewer | ✅ Done |

---

## Key Design Decisions

**Why LangGraph?** The debug loop is a cycle in the graph, not a `for` loop in code. Conditional edges make the routing explicit and inspectable.

**Why Ollama?** Fully local — no API costs, no data leaving your machine. Swap `deepseek-coder:6.7b` for any model you have pulled.

**Why Docker sandbox?** Generated code runs with `--network none`, memory cap, and CPU cap. It cannot touch your host filesystem or make network calls. 
*Note: If Docker is not running or not installed, the sandbox automatically falls back to local execution on your host machine (using the active Python virtual environment). You can also force local execution mode by setting `FORCE_LOCAL_SANDBOX=true` in your environment.*

**Why ChromaDB?** Persistent local vector store — no external service needed. Error memory grows with every run, making the debugger smarter over time.

**RAG degrades gracefully** — if `chromadb` isn't installed, the pipeline runs without it. No crashes.