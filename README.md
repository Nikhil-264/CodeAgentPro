# CodeAgent Pro 🤖

An agentic AI coding assistant with a self-repair loop — generates code, tests it, debugs itself, and refactors until it works.

## Architecture

```
User Task
   ↓
Planner Agent        → Breaks task into sub-tasks
   ↓
Code Generator       → Writes the code (via Ollama)
   ↓
Execution Sandbox    → Runs code in Docker (isolated)
   ↓
Test Generator       → Writes Pytest tests
   ↓
┌─ Debug Loop ────────────────────────────────┐
│  Run Tests → Fail → Debugger fixes → Repeat │
│             Pass → exit loop                │
└─────────────────────────────────────────────┘
   ↓
Refactor Agent       → Cleans up working code
   ↓
Final Code ✅
```

## Setup

### Prerequisites
- Python 3.11+
- Docker Desktop running
- [Ollama](https://ollama.com) installed

### 1. Pull the coding model
```bash
ollama pull deepseek-coder:6.7b
```

### 2. Install Python dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the backend
```bash
cd backend
python main.py
```

API available at: http://localhost:8000
Swagger docs at: http://localhost:8000/docs

## API Usage

### Quick code generation (no tests)
```bash
curl -X POST http://localhost:8000/api/generate/quick \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a function to check if a string is a palindrome"}'
```

### Full pipeline with streaming
```bash
curl -X POST http://localhost:8000/api/generate/stream \
  -H "Content-Type: application/json" \
  -d '{"task": "Build a REST API for a todo list using FastAPI"}'
```

### Check available models
```bash
curl http://localhost:8000/api/models
```

## Build Stages

| Stage | Feature | Status |
|-------|---------|--------|
| 1 | MVP — Prompt to code via Ollama | ✅ Done |
| 2 | Docker execution sandbox | ✅ Done |
| 3 | Pytest test generation | ✅ Done |
| 4 | Self-repair debug loop | ✅ Done |
| 5 | RAG (codebase + docs + error memory) | 🔜 Next |
| 6 | Multi-agent orchestration (LangGraph) | 🔜 Planned |
| 7 | React frontend + UI | 🔜 Planned |

## Project Structure
```
codeagent-pro/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── requirements.txt
│   ├── agents/
│   │   ├── planner.py       # Task decomposition
│   │   ├── code_generator.py
│   │   ├── test_generator.py
│   │   ├── debugger.py      # Self-repair loop
│   │   └── refactor.py
│   ├── core/
│   │   ├── llm_client.py    # Ollama interface
│   │   ├── prompts.py       # All prompt templates
│   │   ├── sandbox.py       # Docker execution
│   │   └── pipeline.py      # Orchestrator
│   ├── api/
│   │   └── routes.py        # FastAPI endpoints
│   └── rag/                 # Stage 5 (coming)
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile.backend
└── frontend/                # Stage 7 (coming)
```
