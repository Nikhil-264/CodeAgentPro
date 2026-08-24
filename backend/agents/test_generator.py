import asyncio
from core.llm_client import OllamaClient
from core.prompts import TEST_GENERATOR_SYSTEM, TEST_GENERATOR_PROMPT


class TestGeneratorAgent:
    """
    Stage 3 Agent: Generates Pytest / JS / C++ test suites for the produced code.
    Auto-retries up to max_attempts (default 3) on failure.
    """

    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.name = "TestGenerator"

    async def run(self, code: str, task: str, language: str = "Python", max_attempts: int = 3) -> dict:
        prompt = TEST_GENERATOR_PROMPT.format(code=code, task=task, language=language)

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                test_code = await self.llm.generate(prompt, system=TEST_GENERATOR_SYSTEM)
                test_code = self._clean_code(test_code)
                if test_code:
                    return {
                        "test_code": test_code,
                        "agent": self.name,
                        "success": True,
                        "error": None,
                        "attempts": attempt,
                    }
                last_error = "LLM returned empty test code"
            except Exception as e:
                last_error = str(e)

            if attempt < max_attempts:
                await asyncio.sleep(2 * attempt)

        return {
            "test_code": "",
            "agent": self.name,
            "success": False,
            "error": f"TestGenerator failed after {max_attempts} attempts: {last_error}",
            "attempts": max_attempts,
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