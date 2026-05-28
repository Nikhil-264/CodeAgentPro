import json
from core.llm_client import OllamaClient
from core.prompts import PLANNER_SYSTEM, PLANNER_PROMPT


class PlannerAgent:
    """
    Stage 6 Agent (wired in early): Decomposes a high-level task
    into ordered sub-tasks for other agents to execute.
    """

    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.name = "Planner"

    async def run(self, task: str) -> dict:
        """
        Break down task into sub-tasks.

        Returns:
            {
                "plan": list[dict],   # [{id, title, description, files}]
                "agent": str,
                "success": bool
            }
        """
        prompt = PLANNER_PROMPT.format(task=task)

        try:
            raw = await self.llm.generate(prompt, system=PLANNER_SYSTEM)
            plan = self._parse_plan(raw)
            return {"plan": plan, "agent": self.name, "success": True, "error": None}
        except Exception as e:
            # Fallback: single-task plan so the pipeline never breaks
            fallback = [{"id": 1, "title": task, "description": task, "files": ["solution.py"]}]
            return {"plan": fallback, "agent": self.name, "success": False, "error": str(e)}

    def _parse_plan(self, raw: str) -> list[dict]:
        """Safely parse JSON plan from LLM output."""
        # Strip markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.splitlines()[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.splitlines()[:-1])

        parsed = json.loads(cleaned.strip())
        if not isinstance(parsed, list):
            raise ValueError("Expected a JSON array from planner")
        return parsed