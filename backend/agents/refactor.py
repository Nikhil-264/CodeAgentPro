from core.llm_client import OllamaClient
from core.prompts import REFACTOR_SYSTEM, REFACTOR_PROMPT


class RefactorAgent:
    """
    Stage 6 Agent: Polishes working code for readability and quality.
    Only runs after tests pass — never on broken code.
    """

    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.name = "Refactor"

    async def run(self, code: str, language: str = "Python") -> dict:
        prompt = REFACTOR_PROMPT.format(code=code, language=language)

        try:
            refactored = await self.llm.generate(prompt, system=REFACTOR_SYSTEM)
            refactored = self._clean_code(refactored)
            return {
                "refactored_code": refactored,
                "agent": self.name,
                "success": True,
                "error": None,
            }
        except Exception as e:
            # On failure, pass original code through unchanged
            return {
                "refactored_code": code,
                "agent": self.name,
                "success": False,
                "error": str(e),
            }

    def _clean_code(self, raw: str) -> str:
        if not raw:
            return ""
        import re
        text = raw.strip()
        pattern = r"```(?:[a-zA-Z0-9_+#-]+)?\n([\s\S]*?)\n```"
        matches = list(re.finditer(pattern, text))
        if matches:
            largest = max(matches, key=lambda m: len(m.group(1)))
            return largest.group(1).strip()

        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()