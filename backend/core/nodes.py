"""
LangGraph Nodes
Each function is a graph node. It receives the full PipelineState,
does its work, and returns a partial state dict to merge back in.
"""
from core.state import PipelineState
from core.llm_client import OllamaClient
from core.sandbox import ExecutionSandbox
from agents.planner import PlannerAgent
from agents.code_generator import CodeGeneratorAgent
from agents.test_generator import TestGeneratorAgent
from agents.debugger import DebuggerAgent
from agents.refactor import RefactorAgent

# RAG optional
try:
    from rag.rag_manager import RAGManager
    _rag = RAGManager()
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


def _llm(state: PipelineState) -> OllamaClient:
    return OllamaClient(model=state.get("model", "deepseek-coder:6.7b"))


def _event(step: str, status: str, data: dict = None) -> dict:
    return {"step": step, "status": status, "data": data or {}}


# ── Node: RAG context fetch ───────────────────────────────────────────────────

async def node_rag_context(state: PipelineState) -> dict:
    if not RAG_AVAILABLE:
        return {"rag_context": "", "events": state["events"]}

    ctx = _rag.get_generation_context(state["task"], language=state["language"])
    events = state["events"] + [_event("RAG", "success", {"length": len(ctx)})]
    return {"rag_context": ctx, "events": events}


# ── Node: Planner ─────────────────────────────────────────────────────────────

async def node_planner(state: PipelineState) -> dict:
    events = state["events"] + [_event("Planner", "running")]
    result = await PlannerAgent(_llm(state)).run(state["task"])
    events = events + [_event("Planner", "success" if result["success"] else "warning",
                               {"plan": result["plan"]})]
    return {"plan": result["plan"], "events": events}


# ── Node: Code Generator ──────────────────────────────────────────────────────

async def node_code_generator(state: PipelineState) -> dict:
    events = state["events"] + [_event("CodeGenerator", "running")]
    result = await CodeGeneratorAgent(_llm(state)).run(
        state["task"],
        language=state["language"],
        framework=state["framework"],
        context=state.get("rag_context", ""),
    )
    if not result["success"]:
        return {
            "error": result["error"],
            "events": events + [_event("CodeGenerator", "failed", result)],
        }
    events = events + [_event("CodeGenerator", "success", {
        "code_length": len(result["code"]),
        "code": result["code"]
    })]
    return {"current_code": result["code"], "events": events}


# ── Node: Sandbox Execute ─────────────────────────────────────────────────────

async def node_sandbox_execute(state: PipelineState) -> dict:
    events = state["events"] + [_event("Sandbox", "running", {"phase": "initial_run"})]
    try:
        result = await ExecutionSandbox().run_code(
            state["current_code"], language=state.get("language", "Python")
        )
        status = "success" if result["success"] else "warning"
        events = events + [_event("Sandbox", status, result)]
        return {
            "exec_stdout": result["stdout"],
            "exec_stderr": result["stderr"],
            "exec_success": result["success"],
            "events": events,
        }
    except Exception as e:
        err_msg = f"Sandbox execution failed: {str(e)}. Make sure Docker Desktop is running."
        events = events + [_event("Sandbox", "warning", {"stdout": "", "stderr": err_msg, "success": False})]
        return {
            "exec_stdout": "",
            "exec_stderr": err_msg,
            "exec_success": False,
            "events": events,
        }


# ── Node: Test Generator ──────────────────────────────────────────────────────

async def node_test_generator(state: PipelineState) -> dict:
    events = state["events"] + [_event("TestGenerator", "running")]
    result = await TestGeneratorAgent(_llm(state)).run(
        state["current_code"], state["task"], language=state.get("language", "Python")
    )
    if not result["success"]:
        return {
            "test_code": "",
            "events": events + [_event("TestGenerator", "failed", result)],
        }
    events = events + [_event("TestGenerator", "success", {
        "test_code": result["test_code"]
    })]
    return {"test_code": result["test_code"], "events": events}


# ── Node: Run Tests ───────────────────────────────────────────────────────────

async def node_run_tests(state: PipelineState) -> dict:
    attempt = state.get("debug_attempt", 0)
    events = state["events"] + [_event("Sandbox", "running",
                                        {"phase": "test_run", "attempt": attempt})]
    try:
        result = await ExecutionSandbox().run_tests(
            state["current_code"], state["test_code"], language=state.get("language", "Python")
        )
        status = "success" if result["success"] else "warning"
        events = events + [_event("Sandbox", status, {**result, "attempt": attempt})]

        error_out = result["stdout"] + "\n" + result["stderr"]

        if result["success"]:
            events = events + [_event("DebugLoop", "success",
                                       {"attempts": attempt, "message": "All tests passed!"})]

        return {
            "tests_passed": result["success"],
            "last_error": error_out,
            "exec_stdout": result["stdout"],
            "exec_stderr": result["stderr"],
            "events": events,
        }
    except Exception as e:
        err_msg = f"Sandbox test execution failed: {str(e)}. Make sure Docker Desktop is running."
        events = events + [_event("Sandbox", "warning", {"stdout": "", "stderr": err_msg, "success": False, "attempt": attempt})]
        return {
            "tests_passed": False,
            "last_error": err_msg,
            "exec_stdout": "",
            "exec_stderr": err_msg,
            "events": events,
        }


# ── Node: Debugger ────────────────────────────────────────────────────────────

async def node_debugger(state: PipelineState) -> dict:
    attempt = state.get("debug_attempt", 0) + 1
    events = state["events"] + [_event("Debugger", "running", {"attempt": attempt})]

    # Pull similar past fixes from error memory
    error = state.get("last_error", "")
    memory_ctx = (_rag.get_debug_context(error) if RAG_AVAILABLE else "")
    augmented_error = error + ("\n\n" + memory_ctx if memory_ctx else "")

    result = await DebuggerAgent(_llm(state)).run(
        state["current_code"], augmented_error, attempt
    )

    events = events + [_event("Debugger",
                               "success" if result["success"] else "warning",
                               {"attempt": attempt})]

    # Store fix in error memory
    if RAG_AVAILABLE and result["success"]:
        _rag.record_successful_fix(
            error=error,
            broken_code=state["current_code"],
            fixed_code=result["fixed_code"],
            task=state["task"],
            language=state["language"],
        )

    return {
        "current_code": result["fixed_code"],
        "debug_attempt": attempt,
        "events": events,
    }


# ── Node: Refactor ────────────────────────────────────────────────────────────

async def node_refactor(state: PipelineState) -> dict:
    events = state["events"] + [_event("Refactor", "running")]
    result = await RefactorAgent(_llm(state)).run(state["current_code"])
    events = events + [_event("Refactor",
                               "success" if result["success"] else "warning",
                               {"code": result["refactored_code"], "refactored_code": result["refactored_code"]})]
    return {
        "final_code": result["refactored_code"],
        "current_code": result["refactored_code"],
        "events": events,
    }


# ── Node: Finalise ────────────────────────────────────────────────────────────

async def node_finalise(state: PipelineState) -> dict:
    final = state.get("final_code") or state.get("current_code", "")
    events = state["events"] + [_event("Pipeline", "success",
                                        {"final_code": final,
                                         "test_code": state.get("test_code", "")})]
    return {"final_code": final, "events": events}