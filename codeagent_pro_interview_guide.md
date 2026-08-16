# CodeAgent Pro: Interview Preparation Guide 🚀

This document is a comprehensive technical breakdown of **CodeAgent Pro**, compiled specifically to prepare you for your upcoming technical interview. It covers architecture, design decisions, code implementation details, RAG mechanics, and the technical challenges/fixes solved in this project.

---

## 1. Executive Summary
**CodeAgent Pro** is a fully local, agentic AI coding assistant equipped with a **self-repair (debug) loop**. Given a prompt in plain English, the system:
1. **Decomposes the task** using a Planner agent.
2. **Retrieves local RAG context** (library documentation, existing codebase, and past error-fix pairs).
3. **Generates source code** via a local Ollama LLM (defaulting to `deepseek-coder:6.7b`).
4. **Executes and runs Pytest test suites** inside a secure, resource-capped **Docker Sandbox**.
5. **Enters a self-repair loop** (failing test logs + broken code → Debugger agent → rerun tests) up to 5 times.
6. **Refactors and polishes** the code for PEP8 and readability once tests pass.
7. **Streams the entire multi-agent state changes** to a premium React web UI in real-time via **Server-Sent Events (SSE)**.

---

## 2. System Architecture & Flow

The entire orchestrator is built using **LangGraph** to model the state machine. The state is represented by a single, shared dictionary (`PipelineState`) that transitions between nodes.

```
                  User Task Input
                        │
                        ▼
               ┌─────────────────┐
               │   RAG Context   │ ◄─── (ChromaDB: Codebase, Docs)
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │  Planner Agent  │ ─── (Decomposes task to sub-tasks)
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ Code Generator  │ ─── (Ollama deepseek-coder)
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ Sandbox Execute │ ─── (First run check in Docker)
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ Test Generator  │ ─── (Generates pytest suite)
               └────────┬────────┘
                        ▼
         ┌────────► ┌───────────┐
         │          │ Run Tests │ ─── (Executes pytest in Docker)
         │          └─────┬─────┘
         │                │
    Debugger Agent        ├─────── [Tests Pass?] ───► [Yes] ───► Refactor ───► Done
   (Max 5 attempts)       │
         ▲                ▼
         └───────────── [No] 
```

---

## 3. Core Component Breakdown

### 3.1 LangGraph Orchestration & State
- **Why LangGraph?** Traditional sequential LLM chains cannot represent cyclic graphs cleanly. The debug loop is an explicit cycle (Run Tests → Fail → Debug → Run Tests). LangGraph models this elegantly using a compiled state graph with conditional edges.
- **Shared State**: Defined in [state.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/core/state.py). It holds inputs (task, settings), outputs (generated code, tests, logs), execution outputs (stdout, stderr), and pipeline status (debug attempt, error).
- **Orchestration Graph**: Implemented in [graph.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/core/graph.py). Nodes are python functions in [nodes.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/core/nodes.py) that modify the state. Conditional edges control branching, such as `should_skip_tests` and `after_tests_run`.

### 3.2 Ollama Integration
- Implemented in [llm_client.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/core/llm_client.py).
- A lightweight async client using `httpx.AsyncClient` that interfaces with Ollama's local REST API (`http://localhost:11434`).
- Uses a deterministic configuration: low temperature (`0.2`) and top-p (`0.9`) to generate highly consistent and functional code.

### 3.3 Secure Docker Sandbox
- Implemented in [sandbox.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/core/sandbox.py).
- **Safety Features**:
  - `--network none`: No internet access to prevent generated code from uploading secrets or downloading malicious packages.
  - `--memory 256m / 512m`: Limits memory consumption to prevent resource depletion.
  - `--cpus 1.0`: Limits CPU consumption.
  - `--pids-limit 64 / 128`: Prevents fork bombs or infinite processes from freezing the host system.
  - `-v {tmpdir}:/workspace:ro`: Mounts the temporary directory as read-only for basic code execution. (Write permissions are given only for test runs to install dependencies and cache test metrics).

### 3.4 Vector Search RAG (ChromaDB)
- Base wrapper in [base_store.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/rag/base_store.py).
- Local text embeddings are computed using `sentence-transformers` (specifically the lightweight `all-MiniLM-L6-v2` model, which loads in ~80MB of memory).
- Divided into three distinct vector stores:
  1. **Docs Store** ([docs_store.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/rag/docs_store.py)): Preloaded with FastAPI, Pytest, and Pydantic coding snippets.
  2. **Codebase Store** ([codebase_store.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/rag/codebase_store.py)): Indexes local directory structures using character-based sliding window chunking (chunk size: 800, overlap: 150) for relevant references.
  3. **Error Memory Store** ([error_memory_store.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/rag/error_memory_store.py)): Keeps a history of task descriptions, compilation/test errors, and the subsequent code changes that successfully resolved them.
- **RAG Graceful Degradation**: RAG is built as optional. If `chromadb` is missing or fails, the pipeline degrades gracefully, carrying out execution without vector context.

### 3.5 Real-Time Streaming UI (FastAPI & SSE)
- The FastAPI router in [routes.py](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/backend/api/routes.py) hosts the `/api/generate/stream` endpoint.
- Returns a `StreamingResponse` with `media_type="text/event-stream"`.
- Uses `agent_graph.astream()` to capture incremental updates emitted from each node and yields them to the client.
- The React custom hook [useAgent.js](file:///c:/Users/HP/Documents/Coding journeys/CV projects/CodeAgentPro/frontend/src/useAgent.js) reads the stream chunk-by-chunk using a reader (`res.body.getReader()`), decodes the data stream, and dispatches UI updates.

---

## 4. Key Troubleshooting Wins (Windows Realities)

Be ready to explain these during your interview. They demonstrate deep system integration experience on Windows environments:

### 4.1 Subprocess Event Loop Block on Windows
- **The Issue**: On Windows, Uvicorn's event loop configuration does not support async subprocesses via standard `asyncio.create_subprocess_exec`. Running Docker sandbox commands directly threw a `NotImplementedError`, abruptly dropping the client's SSE stream.
- **The Fix**: Rewrote sandbox execution using standard `subprocess.run` wrapped in `asyncio.to_thread`. This delegates subprocess blocking calls to a background threadpool, keeping the FastAPI main thread responsive.

### 4.2 Empty UI Code Viewers During Runs
- **The Issue**: Code/Test tabs in React remained blank until the entire pipeline succeeded. If the backend crashed, or got stuck in a multi-step debug loop, the user was left staring at empty screens.
- **The Fix**: Added immediate code payloads inside intermediate node success events (`CodeGenerator` and `TestGenerator`). Updated the frontend SSE hook to capture these events and update `state.currentCode` and `state.testCode` instantly.

### 4.3 RAG Memory Hallucination Loops
- **The Issue**: During earlier Docker crashes, the Debugger agent output explaining the environment issue was recorded as a "successful fix" in ChromaDB. On subsequent runs, this error message was pulled as RAG context and prepended to prompts, causing the LLM to output explanations instead of python code.
- **The Fix**: Created a collection-wide `clear()` method in the ChromaDB vector wrapper to reset collections. Added a `/api/rag/clear` POST endpoint to easily reset memory without sqlite file locking issues on Windows.

### 4.4 UI Progress Bar Stage Mismatch
- **The Issue**: The top progress bar segment for "Debug" remained gray even when the debugger was running. The UI was filtering events for the key `DebugLoop`, while the backend emitted them under the node name `Debugger`.
- **The Fix**: Updated the react progress bar component `PipelineBar.jsx` to map any event from the step `Debugger` into `DebugLoop`.

---

## 5. Potential Interview Questions & Answers

### Q: Why did you choose LangGraph for this application?
> **Answer:** "Unlike simple linear chains, CodeAgent Pro requires a cyclic state machine. If tests fail, the program needs to route back to a debugging agent, modify the code, and execute tests again. LangGraph allows us to define nodes as simple Python functions and orchestrate routing explicitly using compiled state graphs and conditional edges. It keeps our logic clean, prevents recursive function overflows, and provides a clear state payload that we can capture and stream to the user in real-time."

### Q: How do you secure local execution of AI-generated code?
> **Answer:** "We use a dedicated Docker execution sandbox (`python:3.11-slim` image). When code is generated, it is written to a temporary directory and mounted into a container. We enforce a zero-network policy (`--network none`) so the code cannot make external API calls or download dependencies. Additionally, we cap resources to prevent denial-of-service style code: memory is limited to 256MB/512MB, CPU is capped at 1.0, and we use a PID limit (`--pids-limit 64`) to eliminate risk from fork bombs or infinite loops."

### Q: How does the self-repair (debug) loop work?
> **Answer:** "When the test node runs, it executes Pytest in the Docker sandbox. If tests fail, the exit code is non-zero, and `exec_success` is set to `False`. The graph's conditional edge checks this and routes state to the `debugger` node. The Debugger Agent is prompted with the broken code, the test failure logs (stdout/stderr), and the retry count. It returns patched code which is written back to state. The graph then routes back to the test node. This loop repeats up to 5 times. If it still fails, the system yields the best attempt and stops."

### Q: Tell me about how the RAG database prevents the agent from repeating mistakes.
> **Answer:** "We implemented an `ErrorMemoryStore` collection inside a local ChromaDB instance. When a bug is successfully resolved in the debug loop, we record the task description, the test error trace, the broken code, and the fixed code as a single record. On subsequent runs, if a test fails, the debugger queries this store using the current error trace. If a high-similarity match (cosine distance score > 0.65) is found, we prepend the past fix to the debugger prompt. This acts as a short-term memory that prevents the LLM from making the same coding mistake twice."

### Q: How does the SSE streaming work from backend to frontend?
> **Answer:** "FastAPI's `StreamingResponse` yields Server-Sent Events as a text stream. In the background, we invoke LangGraph's `astream()` method. As each node executes and modifies the state, we capture the new events appended to the state dictionary, format them as JSON strings prefixed with `data: `, and yield them. In the React frontend, we use `fetch` with a body reader (`res.body.getReader()`) to process the stream incrementally, updating the react state in real-time. This provides a live terminal-like experience for the developer."
