"""
Pipeline Orchestrator — Stage 6
Now powered by LangGraph. The manual agent loop is replaced by the compiled
graph in core/graph.py. This file is a thin async adapter that:
  1. Builds the initial PipelineState
  2. Runs the graph
  3. Streams events back to the API layer as SSE-compatible dicts

The old pipeline.py is kept compatible — same interface, new internals.
"""
import asyncio
from typing import AsyncGenerator
from core.graph import agent_graph
from core.state import PipelineState


class AgentPipeline:
    MAX_DEBUG_ATTEMPTS = 5

    def __init__(self, model: str = "deepseek-coder:6.7b", use_rag: bool = True):
        self.model = model
        self.use_rag = use_rag

    async def run(
        self,
        task: str,
        language: str = "Python",
        framework: str = "standard library",
        skip_tests: bool = False,
        skip_refactor: bool = False,
    ) -> AsyncGenerator[dict, None]:
        """
        Run the LangGraph pipeline and yield events as they are appended
        to state["events"] by each node.
        """
        initial_state: PipelineState = {
            "task": task,
            "language": language,
            "framework": framework,
            "model": self.model,
            "skip_tests": skip_tests,
            "skip_refactor": skip_refactor,
            # Defaults
            "plan": [],
            "rag_context": "",
            "current_code": "",
            "test_code": "",
            "exec_stdout": "",
            "exec_stderr": "",
            "exec_success": False,
            "debug_attempt": 0,
            "max_debug_attempts": self.MAX_DEBUG_ATTEMPTS,
            "tests_passed": False,
            "last_error": "",
            "pending_fix": None,
            "final_code": "",
            "events": [],
            "error": None,
        }

        seen_event_count = 0

        try:
            # LangGraph's astream yields state snapshots after each node
            async for state_snapshot in agent_graph.astream(initial_state):
                # Each snapshot is {node_name: updated_state_dict}
                for node_name, node_state in state_snapshot.items():
                    events = node_state.get("events", [])
                    # Yield only newly added events
                    new_events = events[seen_event_count:]
                    for event in new_events:
                        yield event
                    seen_event_count = len(events)
        except Exception as e:
            yield {
                "step": "Pipeline",
                "status": "failed",
                "data": {"error": f"Pipeline crashed: {str(e)}"}
            }

        yield {"step": "Done", "status": "success", "data": {}}