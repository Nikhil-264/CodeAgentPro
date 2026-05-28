from core.llm_client import OllamaClient
from core.prompts import CODE_GENERATOR_SYSTEM, CODE_GENERATOR_PROMPT


class CodeGeneratorAgent:
    """
    Stage 1 Agent: Turns a plain-English task into working code.
    """

    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.name = "CodeGenerator"

    async def run(
        self,
        task: str,
        language: str = "Python",
        framework: str = "standard library",
        context: str = ""
    ) -> dict:
        """
        Generate code for the given task.

        Returns:
            {
                "code": str,          # Generated source code
                "language": str,
                "agent": str,
                "success": bool
            }
        """
        prompt = CODE_GENERATOR_PROMPT.format(
            task=task,
            language=language,
            framework=framework,
        )

        # Prepend any RAG context (Stage 5 will populate this)
        if context:
            prompt = f"RELEVANT CONTEXT:\n{context}\n\n{prompt}"

        try:
            code = await self.llm.generate(prompt, system=CODE_GENERATOR_SYSTEM)
            code = self._clean_code(code)
            return {
                "code": code,
                "language": language,
                "agent": self.name,
                "success": True,
                "error": None,
            }
        except Exception as e:
            return {
                "code": "",
                "language": language,
                "agent": self.name,
                "success": False,
                "error": str(e),
            }

    def _clean_code(self, raw: str) -> str:
        """Strip markdown fences if the model added them."""
        lines = raw.strip().splitlines()
        # Remove opening fence
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)