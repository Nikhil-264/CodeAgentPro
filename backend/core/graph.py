"""
LangGraph Graph
Defines the full agent pipeline as a directed graph with conditional edges.

Flow:
  START
    → rag_context
    → planner
    → code_generator  (abort on failure)
    → sandbox_execute
    → test_generator  (skip if skip_tests=True)
    → run_tests
    → [conditional] tests pass?
        YES → refactor (skip if skip_refactor=True) → finalise → END
        NO  → max attempts reached? → finalise → END
              else → debugger → run_tests (loop)
"""
from langgraph.graph import StateGraph, END
from core.state import PipelineState
from core.nodes import (
    node_rag_context,
    node_planner,
    node_code_generator,
    node_sandbox_execute,
    node_test_generator,
    node_run_tests,
    node_debugger,
    node_refactor,
    node_finalise,
)

MAX_DEBUG_ATTEMPTS = 5


# ── Conditional edge functions ────────────────────────────────────────────────

def should_abort(state: PipelineState) -> str:
    """After code generation: abort if LLM failed."""
    if state.get("error"):
        return "finalise"
    return "sandbox_execute"


def should_skip_tests(state: PipelineState) -> str:
    """After sandbox execute: skip tests if flag set."""
    if state.get("skip_tests"):
        return "finalise"
    return "test_generator"


def after_tests_run(state: PipelineState) -> str:
    """After running tests: pass / debug / give up."""
    if state.get("tests_passed"):
        if state.get("skip_refactor"):
            return "finalise"
        return "refactor"

    attempts = state.get("debug_attempt", 0)
    if attempts >= MAX_DEBUG_ATTEMPTS:
        return "finalise"   # Give up — exceeded retry limit

    return "debugger"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(PipelineState)

    # Register nodes
    g.add_node("rag_context",      node_rag_context)
    g.add_node("planner",          node_planner)
    g.add_node("code_generator",   node_code_generator)
    g.add_node("sandbox_execute",  node_sandbox_execute)
    g.add_node("test_generator",   node_test_generator)
    g.add_node("run_tests",        node_run_tests)
    g.add_node("debugger",         node_debugger)
    g.add_node("refactor",         node_refactor)
    g.add_node("finalise",         node_finalise)

    # Linear edges
    g.set_entry_point("rag_context")
    g.add_edge("rag_context",     "planner")
    g.add_edge("planner",         "code_generator")
    g.add_edge("test_generator",  "run_tests")
    g.add_edge("debugger",        "run_tests")   # Debug loop back
    g.add_edge("refactor",        "finalise")
    g.add_edge("finalise",        END)

    # Conditional edges
    g.add_conditional_edges(
        "code_generator",
        should_abort,
        {"sandbox_execute": "sandbox_execute", "finalise": "finalise"},
    )
    g.add_conditional_edges(
        "sandbox_execute",
        should_skip_tests,
        {"test_generator": "test_generator", "finalise": "finalise"},
    )
    g.add_conditional_edges(
        "run_tests",
        after_tests_run,
        {"refactor": "refactor", "debugger": "debugger", "finalise": "finalise"},
    )

    return g.compile()


# Singleton compiled graph
agent_graph = build_graph()