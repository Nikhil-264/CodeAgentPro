from core.llm_client import OllamaClient
from core.prompts import TEST_GENERATOR_SYSTEM, TEST_GENERATOR_PROMPT


class TestGeneratorAgent:
    """
    Stage 3 Agent: Generates Pytest test suites for the produced code.
    These tests feed into the self-repair loop.
    """

    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.name = "TestGenerator"

    async def run(self, code: str, task: str, language: str = "Python") -> dict:
        """
        Generate a test file for the given code.
        """
        prompt = TEST_GENERATOR_PROMPT.format(code=code, task=task, language=language)

        try:
            test_code = await self.llm.generate(prompt, system=TEST_GENERATOR_SYSTEM)
            test_code = self._clean_code(test_code)
            return {
                "test_code": test_code,
                "agent": self.name,
                "success": True,
                "error": None,
            }
        except Exception as e:
            return {
                "test_code": "",
                "agent": self.name,
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