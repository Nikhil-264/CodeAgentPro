# CodeAgent Pro 🤖

An agentic AI coding assistant with a self-repair loop — generates code, tests it, debugs itself, and refactors until it works. Now supporting **Python**, **JavaScript**, and **C++**, with **Ollama**, **Groq**, and **Google Gemini** LLM providers.

---

## Architecture

```
User Task
   ↓
RAG Context Fetch    → Retrieves relevant docs, codebase, past fixes
   ↓
Planner Agent        → Breaks task into sub-tasks
   ↓
Code Generator       → Writes the code (via Ollama / Groq / Gemini)
   ↓
Execution Sandbox    → Runs Python / JS / C++ code in Docker (isolated)
   ↓
Test Generator       → Writes test suites (Pytest / Node test / C++ assert)
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

All agents are Orchestrated via **LangGraph** as a compiled state graph with conditional edges.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker Desktop** *(Optional: used for secure containerized execution sandboxing; falls back to local execution if missing/not running)*
- **[Ollama](https://ollama.com)** *(Optional: if running local models like `deepseek-coder:6.7b`)*

---

## Setup & API Keys

### 1. Environment Configuration (.env)
Create a `.env` file inside the `backend/` directory (or copy `backend/.env.example`):

```env
# Cloud LLM Provider Keys (Optional if using Ollama)
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Local Ollama URL
OLLAMA_BASE_URL=http://localhost:11434
```

### 2. Pull local model (for Ollama)
```bash
ollama pull deepseek-coder:6.7b
```

### 3. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Start the backend
```bash
cd backend
python main.py
```

API: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

### 5. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:3000

### 6. Or run everything with Docker
```bash
docker compose up --build
```

Backend → `:8000` | Frontend → `:3000`

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
  -d '{
    "task": "Write a function to check if a string is a palindrome",
    "language": "Python",
    "provider": "ollama",
    "model": "deepseek-coder:6.7b"
  }'
```

### Full pipeline with real-time streaming (SSE)
```bash
curl -X POST http://localhost:8000/api/generate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Build a REST API for a todo list using FastAPI",
    "language": "Python",
    "provider": "groq",
    "model": "llama-3.3-70b-versatile"
  }'
```

### Request body options
```json
{
  "task": "your task description",
  "language": "Python",
  "framework": "standard library",
  "provider": "ollama",
  "model": "deepseek-coder:6.7b",
  "skip_tests": false,
  "skip_refactor": false
}
```

*Supported Languages:* `Python`, `JavaScript`, `C++`  
*Supported Providers:* `ollama`, `groq`, `gemini`

---

## Project Structure

```
codeagent-pro/
├── README.md
├── docker-compose.yml            # Root docker compose orchestration
├── start_project.bat             # Automated Windows launcher
├── backend/
│   ├── main.py                   # FastAPI entry point
│   ├── requirements.txt
│   ├── .env.example              # API key configuration template
│   ├── agents/
│   │   ├── planner.py            # Task decomposition
│   │   ├── code_generator.py     # Multi-provider LLM code generation
│   │   ├── test_generator.py     # Pytest / JS / C++ test generator
│   │   ├── debugger.py           # Self-repair loop core
│   │   └── refactor.py           # Code quality pass
│   ├── core/
│   │   ├── llm_client.py         # Multi-provider client (Ollama, Groq, Gemini)
│   │   ├── prompts.py            # Centralized prompt templates
│   │   ├── sandbox.py            # Multi-language Docker execution engine
│   │   ├── state.py              # LangGraph shared state
│   │   ├── nodes.py              # LangGraph node functions
│   │   ├── graph.py              # LangGraph compiled state graph
│   │   └── pipeline.py           # Thin SSE stream adapter
│   ├── api/
│   │   └── routes.py             # FastAPI endpoints + RAG routes
│   └── rag/
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
│       ├── App.jsx               # Main layout + Provider/Model/Language panel
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
| 1 | MVP — Prompt to code via Ollama / Groq / Gemini | ✅ Done |
| 2 | Multi-language Docker execution sandbox (Python, JS, C++) | ✅ Done |
| 3 | Pytest / JS / C++ test generation | ✅ Done |
| 4 | Self-repair debug loop | ✅ Done |
| 5 | RAG — codebase + docs + error memory | ✅ Done |
| 6 | LangGraph multi-agent orchestration | ✅ Done |
| 7 | React frontend with real-time terminal & progress bar | ✅ Done |

---

## Key Design Decisions

- **Why LangGraph?** The debug loop is a cycle in the state graph, not a `for` loop in code. Conditional edges make agent routing explicit and inspectable.
- **Why Multi-Provider (Ollama, Groq, Gemini)?** Choose local privacy with Ollama (`deepseek-coder:6.7b`), ultra-fast cloud inference with Groq (`openai/gpt-oss-20b`, `qwen/qwen3.6-27b`, `openai/gpt-oss-120b`), or Google Gemini (`gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.5-flash`).
- **Why Multi-Language Docker Sandboxing?** Executes Python (`python:3.11-slim`), JavaScript (`node:20-alpine`), and C++ (`gcc:latest`) inside isolated containers with `--network none`, memory limits, and CPU caps.
- **Why ChromaDB RAG?** Persistent local vector store. Error memory grows with every run, making the debugger smarter over time.