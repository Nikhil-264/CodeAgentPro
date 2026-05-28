# CodeAgent Pro - Development & Troubleshooting Log

This document summarizes the core technical problems identified and resolved during this session to make **CodeAgent Pro** fully operational, robust, and responsive on Windows.

---

## 1. Project Launch & Configuration (Windows)
### Problem
Running both the FastAPI backend and React frontend requires manually activating the virtual environment, installing Python dependencies, installing npm packages, pulling the local Ollama coding model, and starting two separate terminal sessions. This manual process is tedious and error-prone.

### Solution
Created a root-level script: [start_project.bat](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/start_project.bat).
* Automatically checks for `.venv`, creating it if missing.
* Installs backend requirements from `backend/requirements.txt`.
* Runs `npm install` in `frontend/` if `node_modules` is not present.
* Prompts the user to pull the required Ollama model (`deepseek-coder:6.7b`).
* Launches the FastAPI server and Vite dev server in two separate, styled command windows.

---

## 2. Empty Code Section During Execution
### Problem
The Code and Test viewer sections in the React UI remained empty during the agent run. They were designed to only load code at the end of the run on success. If the pipeline crashed or entered a long debug loop, the user could not see the generated code.

### Solution
Enabled real-time streaming of code and test outputs:
* Modified [nodes.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/core/nodes.py): Added the generated source code directly to the `CodeGenerator` success payload and the test suite code to the `TestGenerator` success payload.
* Modified [useAgent.js](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/frontend/src/useAgent.js): Updated the React hook to intercept those events and update `currentCode` and `testCode` in the state immediately, rather than waiting for the final `Pipeline` done event.

---

## 3. Subprocess Execution Failure (Windows Event Loop Issue)
### Problem
Whenever the pipeline ran the Docker sandbox to execute code or run tests, the backend crashed with a `network error` in the frontend. 
Under the hood, Uvicorn on Windows defaults to an event-loop configuration that does not support asynchronous subprocesses via `asyncio.create_subprocess_exec`. This threw a `NotImplementedError` (with an empty message), causing the FastAPI SSE stream connection to drop abruptly.

### Solution
Made sandbox subprocess execution robust and loop-agnostic:
* Modified [sandbox.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/core/sandbox.py): Rewrote `_run_subprocess` to execute standard Python `subprocess.run` inside a background worker thread via `asyncio.to_thread`.
* Added robust exception handling around the Docker runs in [nodes.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/core/nodes.py) and [pipeline.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/core/pipeline.py) to capture OS-level warnings (e.g. if Docker Desktop is closed) without crashing the FastAPI thread.

---

## 4. RAG Hallucination Loop
### Problem
During the earlier sandbox crashes, the Debugger Agent generated a conversational text explanation explaining that the errors were due to Docker and Python encoding issues. 
Because the debugger step completed, this conversational text was incorrectly saved to the database (`error_memory` collection) as a "successful fix". On subsequent runs, the RAG system queried this collection, fetched the old explanation text, and prepended it to the code generator prompt, causing the LLM to output the exact same explanation instead of code.

### Solution
Built a database clearing mechanism to reset RAG memory:
* Modified [base_store.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/rag/base_store.py): Added a `clear()` method that deletes all documents in a collection by their IDs (safe from Windows SQLite file locking issues).
* Modified [rag_manager.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/rag/rag_manager.py): Exposed `clear_all()`.
* Modified [routes.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/api/routes.py): Added a `/api/rag/clear` POST endpoint.
* *Note:* Users can also resolve this manually by stopping the server, deleting the `backend/data/chromadb` directory, and restarting.

---

## 5. UI Progress Bar "Debug" Stage Mismatch
### Problem
The "Debug" node in the top progress bar remained grey (idle) even when the backend was actively debugging code. The frontend key in the progress bar was `'DebugLoop'`, but the backend emitted active debugging events under the step name `'Debugger'`.

### Solution
Modified [PipelineBar.jsx](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/frontend/src/components/PipelineBar.jsx): Normalized any incoming `'Debugger'` event key to `'DebugLoop'` in the `nodeStatus` selector. The progress node now lights up correctly when the agent is debugging.

---

## 6. Refactor Stage Remaining Grey / Inactive
### Explanation & Behavior
The **Refactor** stage only executes on working code. In the agent graph ([graph.py](file:///c:/Users/HP/Documents/Coding%20journeys/CV%20projects/CodeAgentPro/backend/core/graph.py)):
* **Successful Path**: If the code passes tests (initially or after debugging), the orchestrator transitions to the `refactor` node to polish the code, and then to `finalise`.
* **Failed Path (Retries Exhausted)**: If the tests continue to fail and the debug attempt limit (5) is reached, the agent gives up and routes directly to the `finalise` node. Because `refactor` is skipped, its progress bar circle remains grey (`idle`), while `Done` turns green to indicate the pipeline has terminated.
* **Skip Refactor Flag**: If the **"Skip Refactor"** toggle is enabled in the Configuration panel, the pipeline skips refactoring entirely, even if the tests pass.

