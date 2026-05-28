from core.llm_client import OllamaClient
from core.prompts import DEBUGGER_SYSTEM, DEBUGGER_PROMPT


class DebuggerAgent:
    """
    Stage 4 Agent: The heart of CodeAgent Pro.
    Takes failing code + error output → returns fixed code.
    Called repeatedly by the orchestrator until tests pass or max retries hit.
    """

    def __init__(self, llm: OllamaClient, max_attempts: int = 5):
        self.llm = llm
        self.max_attempts = max_attempts
        self.name = "Debugger"

    async def run(self, code: str, error: str, attempt: int = 1) -> dict:
        """
        Analyze the error and return patched code.

        Args:
            code:     The failing source code
            error:    stdout + stderr from the failed run / tests
            attempt:  Current retry number (shown to the LLM for context)

        Returns:
            {
                "fixed_code": str,
                "agent": str,
                "attempt": int,
                "success": bool
            }
        """
        prompt = DEBUGGER_PROMPT.format(
            code=code,
            error=error,
            attempt=attempt,
            max_attempts=self.max_attempts,
        )

        try:
            fixed = await self.llm.generate(prompt, system=DEBUGGER_SYSTEM)
            fixed = self._clean_code(fixed)
            return {
                "fixed_code": fixed,
                "agent": self.name,
                "attempt": attempt,
                "success": True,
                "error": None,
            }
        except Exception as e:
            return {
                "fixed_code": code,   # Return original so loop can continue
                "agent": self.name,
                "attempt": attempt,
                "success": False,
                "error": str(e),
            }

    def _clean_code(self, raw: str) -> str:
        lines = raw.strip().splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)