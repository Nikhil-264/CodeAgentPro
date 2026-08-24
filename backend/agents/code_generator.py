import asyncio
from core.llm_client import OllamaClient
from core.prompts import CODE_GENERATOR_SYSTEM, CODE_GENERATOR_PROMPT


class CodeGeneratorAgent:
    """
    Stage 1 Agent: Turns a plain-English task into working code.
    Auto-retries up to max_attempts (default 3) on failure.
    """

    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.name = "CodeGenerator"

    async def run(
        self,
        task: str,
        language: str = "Python",
        framework: str = "standard library",
        context: str = "",
        max_attempts: int = 3,
    ) -> dict:
        prompt = CODE_GENERATOR_PROMPT.format(
            task=task,
            language=language,
            framework=framework,
        )

        if context:
            prompt = f"RELEVANT CONTEXT:\n{context}\n\n{prompt}"

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                code = await self.llm.generate(prompt, system=CODE_GENERATOR_SYSTEM)
                code = self._clean_code(code)
                if code:
                    return {
                        "code": code,
                        "language": language,
                        "agent": self.name,
                        "success": True,
                        "error": None,
                        "attempts": attempt,
                    }
                last_error = "LLM returned empty code"
            except Exception as e:
                last_error = str(e)

            if attempt < max_attempts:
                await asyncio.sleep(2 * attempt)

        return {
            "code": "",
            "language": language,
            "agent": self.name,
            "success": False,
            "error": f"CodeGenerator failed after {max_attempts} attempts: {last_error}",
            "attempts": max_attempts,
        }

    def _clean_code(self, raw: str) -> str:
        """Extract source code block from raw LLM output, discarding preambles/reasoning text."""
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