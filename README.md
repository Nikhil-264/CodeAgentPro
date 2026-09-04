# CodeAgent Pro 🤖

An agentic AI coding assistant with a self-repair loop — generates code, tests it, debugs itself, and refactors until it works. Supporting **Python**, **JavaScript**, and **C++**, with **Ollama**, **Groq**, and **Google Gemini** LLM providers.

---

## Architecture

```
User Task
   ↓
RAG Context Fetch    → Retrieves relevant docs, codebase, past error fixes (Cached Singleton)
   ↓
Planner Agent        → Breaks task into sub-tasks
   ↓
Code Generator       → Writes code (Ollama / Groq / Gemini) [3-Attempt Retry]
   ↓
Execution Sandbox    → Runs Python / JS / C++ code in Docker (isolated)
   ↓
Test Generator       → Writes test suites (Pytest / Node test / C++ assert) [3-Attempt Retry]
   ↓
┌─ Debug Loop ────────────────────────────────────────────────────────┐
│  Run Tests → Fail → RAG Error Memory → Debugger Agent → Re-Test Loop │
│             Pass → Exit loop to Refactor                            │
└─────────────────────────────────────────────────────────────────────┘
   ↓
Refactor Agent       → Cleans up working code (Enforces target language)
   ↓
Final Code ✅
```

All agents are orchestrated via **LangGraph** as a compiled state graph with conditional abort edges and deterministic state routing.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker Desktop** — used for secure containerized execution sandboxing. If Docker is not running, the pipeline aborts with a clear error **unless** you explicitly opt into unsandboxed local execution by setting `ALLOW_LOCAL_SANDBOX=true` (local development only — generated code then runs directly on your machine with no isolation).
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

# Execution sandbox: code runs in Docker by default. Set to true to allow
# unsandboxed local execution when Docker is unavailable (local dev only).
ALLOW_LOCAL_SANDBOX=false
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

### 6. Or launch automatically on Windows
Double-click [start_project.bat](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/start_project.bat) to set up dependencies and launch both backend and frontend servers in separate terminal windows.

---

## RAG Architecture (Retrieval-Augmented Generation)

CodeAgent Pro features a multi-collection **ChromaDB** vector store powered by `sentence-transformers` (`all-MiniLM-L6-v2`):

1. **Docs Store (`docs`)**: Contains built-in documentation for FastAPI, Pytest, Python idioms, and DSA algorithms.
2. **Codebase Store (`codebase`)**: Indexes local project directories for context-aware coding.
3. **Error Memory Store (`error_memory`)**: Records `(broken_code, error_stacktrace, fixed_code)` pairs to prevent repeating past debugging errors. A fix is staged during the debug step and only written to memory **after** the next test run confirms it actually passes — unverified fixes are never persisted.

### RAG Latency Optimization
- **Singleton Model Cache**: The embedding model is cached globally (`_EMBEDDING_MODEL` singleton in `base_store.py`).
- **Startup Pre-Warming**: Backend server pre-warms the model on boot (`main.py`), reducing RAG retrieval time from ~36s down to **<0.05s**.

### RAG API Commands:
Seed built-in documentation:
```bash
curl -X POST http://localhost:8000/api/rag/seed-docs
```

Index a local directory (confined to the project root — paths outside it are rejected):
```bash
curl -X POST http://localhost:8000/api/rag/index-project \
  -H "Content-Type: application/json" \
  -d '{"directory": "./backend"}'
```

Check stored stats:
```bash
curl http://localhost:8000/api/rag/stats
```

Clear all vector stores:
```bash
curl -X POST http://localhost:8000/api/rag/clear
```

---

## Offline Evaluation Pipeline (`eval/`)

CodeAgent Pro includes an offline benchmarking framework to evaluate LLM coding capabilities, compute Pass@1/Pass@k rates, measure latencies, and detect regressions.

### Run Evaluation CLI:
```bash
# Test run on 1 task using Groq
python -m eval.run_eval --provider groq --model openai/gpt-oss-20b --subset 1

# Full 18-task benchmark across Python, JS, and C++ using Gemini
python -m eval.run_eval --provider gemini --model gemini-3.6-flash

# Run benchmark using local Ollama model
python -m eval.run_eval --provider ollama --model deepseek-coder:6.7b

# Compare candidate run against baseline to flag quality regressions
# (exits non-zero if pass@1 / pass@k drop > 5 pts, or any task flips pass -> fail)
python -m eval.run_eval --provider groq --model openai/gpt-oss-20b --compare eval/runs/baseline.json
```

### Regression gate in CI

`.github/workflows/eval.yml` runs a 5-task subset on every PR that touches `backend/**`.
If `backend/eval/runs/baseline.json` exists, the workflow runs with `--compare` against it
and **fails the check on regression**; otherwise it posts the metrics as a PR comment only.
To enable gating, generate a known-good run once and commit it as the baseline:

```bash
cd backend
ALLOW_LOCAL_SANDBOX=true python -m eval.run_eval --provider groq \
  --model openai/gpt-oss-20b --subset 5 --output-dir eval/runs
cp eval/runs/run_<timestamp>_<model>.json eval/runs/baseline.json
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
    "task": "Write a binary search implementation with comprehensive edge case handling in C++",
    "language": "C++",
    "provider": "groq",
    "model": "openai/gpt-oss-20b"
  }'
```

### Request body options
```json
{
  "task": "your task description",
  "language": "Python",
  "framework": "standard library",
  "provider": "groq",
  "model": "openai/gpt-oss-20b",
  "skip_tests": false,
  "skip_refactor": false
}
```

*Supported Languages:* `Python`, `JavaScript`, `C++`  
*Supported Groq Models:* `openai/gpt-oss-20b`, `qwen/qwen3.6-27b`, `openai/gpt-oss-120b`  
*Supported Gemini Models:* `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.5-flash`  

---

## Project Structure

```
CodeAgentPro/
├── README.md                     # Project overview and documentation
├── troubleshooting_and_fixes.md  # Detailed technical log of 18+ solved issues
├── start_project.bat             # Automated Windows launcher script
├── docker-compose.yml            # Root docker compose orchestration
├── .github/
│   └── workflows/
│       └── eval.yml              # GitHub Actions CI evaluation workflow
├── backend/
│   ├── main.py                   # FastAPI entry point & startup pre-warming
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # API keys (Groq, Gemini, Ollama)
│   ├── .env.example              # API key configuration template
│   ├── agents/
│   │   ├── planner.py            # Task decomposition agent
│   │   ├── code_generator.py     # Code generation agent (3-attempt retry)
│   │   ├── test_generator.py     # Test suite generator agent (3-attempt retry)
│   │   ├── debugger.py           # Self-repair debug agent with stacktrace analysis
│   │   └── refactor.py           # Code refactoring agent (enforces target language)
│   ├── core/
│   │   ├── llm_client.py         # Multi-provider async LLM client with 429 retries
│   │   ├── prompts.py            # Centralized prompt templates with strict language guards
│   │   ├── sandbox.py            # Subprocess/Docker execution engine (Python, JS, C++)
│   │   ├── state.py              # LangGraph shared state schema
│   │   ├── nodes.py              # LangGraph node functions with error handling
│   │   ├── graph.py              # LangGraph compiled state graph with abort edges
│   │   └── pipeline.py           # SSE stream adapter
│   ├── api/
│   │   └── routes.py             # FastAPI streaming, quick generate & RAG routes
│   ├── rag/
│   │   ├── base_store.py         # ChromaDB base wrapper with singleton model cache
│   │   ├── codebase_store.py     # Project directory vector indexing
│   │   ├── docs_store.py         # Seeded library documentation store
│   │   ├── error_memory_store.py # Historical error-fix vector memory
│   │   └── rag_manager.py        # Centralized RAG manager
│   ├── data/
│   │   └── chromadb/             # Persistent ChromaDB vector database storage
│   └── eval/                     # Offline Evaluation Pipeline
│       ├── dataset/
│       │   └── tasks.yaml        # 18 benchmark tasks with held-out tests
│       ├── harness.py            # Async evaluation harness
│       ├── metrics.py            # Pass@1, Pass@k, latency, and error metrics
│       ├── report.py            # Timestamped JSON run reporter
│       ├── compare.py           # Baseline diff comparator for regression detection
│       ├── run_eval.py           # CLI entry point (python -m eval.run_eval)
│       └── runs/                 # Output directory for evaluation run logs
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx               # Main layout + Provider/Model/Language panel
│       ├── index.css             # Design system + HSL color theme
│       ├── useAgent.js           # SSE streaming hook & state manager
│       └── components/
│           ├── PipelineBar.jsx   # Animated LangGraph step progress bar
│           ├── TerminalLog.jsx   # Real-time event stream terminal
│           └── CodeViewer.jsx    # Token-isolation syntax highlighter
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
| 8 | Offline evaluation pipeline & CI benchmark workflow | ✅ Done |

---

## Key Design Decisions

- **Why LangGraph?** The self-repair loop is a cycle in the state graph. Conditional abort edges prevent runaway execution if generation fails or no execution sandbox is available.
- **Why Multi-Provider (Ollama, Groq, Gemini)?** Offers total privacy with local Ollama (`deepseek-coder:6.7b`), or high-speed cloud inference with Groq (`openai/gpt-oss-20b`, `qwen/qwen3.6-27b`) or Google Gemini (`gemini-3.6-flash`, `gemini-3.7-flash`).
- **Why Multi-Language Sandboxing?** Executes Python (`pytest`), JavaScript (`node --test`), and C++ (`gcc`) inside isolated containers with strict resource caps (`--network none`, `--memory 256m/512m`, read-only mounts). Unsandboxed local execution is opt-in only (`ALLOW_LOCAL_SANDBOX=true`).
- **Why ChromaDB RAG?** Persistent local vector store with singleton embedding caching. Error memory grows with every successful fix, preventing the debugger from repeating mistakes.