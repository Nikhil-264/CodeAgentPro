"""
Evaluation Harness for CodeAgentPro
Executes evaluation tasks against the compiled LangGraph agent_graph and runs
held-out acceptance test suites inside ExecutionSandbox.
"""
import time
import asyncio
from typing import Any, Dict, List, Optional
from core.graph import agent_graph
from core.sandbox import ExecutionSandbox
from core.state import PipelineState


class AsyncEvalHarness:
    """
    Async harness for evaluating LLMs and graph pipeline variants.
    """

    def __init__(self, model: str = "deepseek-coder:6.7b", max_debug_attempts: int = 5):
        self.model = model
        self.max_debug_attempts = max_debug_attempts
        self.sandbox = ExecutionSandbox()

    async def run_task(self, task_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs a single task through agent_graph and tests the output against
        the task's held-out acceptance_test.
        """
        task_id = task_def["id"]
        language = task_def["language"]
        framework = task_def.get("framework", "standard library")
        difficulty = task_def.get("difficulty", "medium")
        acceptance_test = task_def["acceptance_test"]

        initial_state: PipelineState = {
            "task": task_def["task"],
            "language": language,
            "framework": framework,
            "model": self.model,
            "skip_tests": False,
            "skip_refactor": False,
            "plan": [],
            "rag_context": "",
            "current_code": "",
            "test_code": "",
            "exec_stdout": "",
            "exec_stderr": "",
            "exec_success": False,
            "debug_attempt": 0,
            "max_debug_attempts": self.max_debug_attempts,
            "tests_passed": False,
            "last_error": "",
            "pending_fix": None,
            "final_code": "",
            "events": [],
            "error": None,
        }

        start_time = time.perf_counter()
        node_latencies: Dict[str, float] = {}
        final_state: PipelineState = initial_state.copy()

        current_node_start = time.perf_counter()
        try:
            async for snapshot in agent_graph.astream(initial_state):
                node_end = time.perf_counter()
                for node_name, updated_state in snapshot.items():
                    elapsed = node_end - current_node_start
                    node_latencies[node_name] = node_latencies.get(node_name, 0.0) + elapsed
                    final_state.update(updated_state)
                current_node_start = time.perf_counter()
        except Exception as e:
            total_latency = time.perf_counter() - start_time
            return {
                "task_id": task_id,
                "language": language,
                "difficulty": difficulty,
                "passed": False,
                "agent_tests_passed": False,
                "debug_attempts": 0,
                "hit_max_debug": False,
                "pass_at_1": False,
                "pass_at_k": False,
                "total_latency": total_latency,
                "node_latencies": node_latencies,
                "sandbox_error": False,
                "fatal_error": f"Graph execution failed: {str(e)}",
                "sandbox_output": {"stdout": "", "stderr": f"Graph execution failed: {str(e)}", "exit_code": -1},
                "final_code": "",
                "events": final_state.get("events", []),
            }

        total_latency = time.perf_counter() - start_time
        final_code = final_state.get("final_code") or final_state.get("current_code", "")
        debug_attempts = final_state.get("debug_attempt", 0)
        agent_tests_passed = final_state.get("tests_passed", False)
        hit_max_debug = (debug_attempts >= self.max_debug_attempts) and (not agent_tests_passed)

        # Execute held-out acceptance tests against final_code
        acceptance_res = await self.sandbox.run_tests(
            code=final_code,
            test_code=acceptance_test,
            language=language
        )

        passed = acceptance_res.get("success", False)
        stderr_msg = acceptance_res.get("stderr", "")

        # Categorize sandbox error vs code error
        is_sandbox_error = False
        if acceptance_res.get("exit_code") == -1 or acceptance_res.get("timed_out", False):
            is_sandbox_error = True
        elif "Execution binary not found" in stderr_msg or "Make sure Docker Desktop" in stderr_msg:
            is_sandbox_error = True

        pass_at_1 = passed and (debug_attempts == 0)
        pass_at_k = passed and (debug_attempts <= self.max_debug_attempts)

        return {
            "task_id": task_id,
            "language": language,
            "difficulty": difficulty,
            "passed": passed,
            "agent_tests_passed": agent_tests_passed,
            "debug_attempts": debug_attempts,
            "hit_max_debug": hit_max_debug,
            "pass_at_1": pass_at_1,
            "pass_at_k": pass_at_k,
            "total_latency": round(total_latency, 3),
            "node_latencies": {k: round(v, 3) for k, v in node_latencies.items()},
            "sandbox_error": is_sandbox_error,
            "fatal_error": None if not final_state.get("error") else final_state.get("error"),
            "sandbox_output": {
                "stdout": acceptance_res.get("stdout", ""),
                "stderr": acceptance_res.get("stderr", ""),
                "exit_code": acceptance_res.get("exit_code", -1),
            },
            "final_code": final_code,
            "events": final_state.get("events", []),
        }

    async def run_dataset(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Runs evaluation over a list of tasks sequentially."""
        results = []
        for task in tasks:
            res = await self.run_task(task)
            results.append(res)
        return results
