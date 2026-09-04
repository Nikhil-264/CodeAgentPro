"""
Pipeline State
The single shared state object that flows through every LangGraph node.
Each agent reads what it needs and writes its output back into state.
"""
from typing import TypedDict, Optional, Any


class PipelineState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────────
    task: str
    language: str
    framework: str
    model: str
    skip_tests: bool
    skip_refactor: bool

    # ── Planner ────────────────────────────────────────────────────────────
    plan: list[dict]               # [{id, title, description, files}]

    # ── RAG context ────────────────────────────────────────────────────────
    rag_context: str               # Injected before code generation

    # ── Code generation ────────────────────────────────────────────────────
    current_code: str
    test_code: str

    # ── Execution ──────────────────────────────────────────────────────────
    exec_stdout: str
    exec_stderr: str
    exec_success: bool

    # ── Debug loop ─────────────────────────────────────────────────────────
    debug_attempt: int
    max_debug_attempts: int        # loop bound, read by after_tests_run
    tests_passed: bool
    last_error: str
    pending_fix: Optional[dict[str, Any]]   # staged (error, broken_code, fixed_code,
                                            # task, language); persisted to error
                                            # memory only after run_tests verifies it

    # ── Refactor ───────────────────────────────────────────────────────────
    final_code: str

    # ── Event log (streamed to frontend) ───────────────────────────────────
    events: list[dict]             # Appended by every node
    error: Optional[str]           # Set on fatal failures