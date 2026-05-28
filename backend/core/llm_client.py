import httpx
import json
from typing import AsyncGenerator

OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaClient:
    """
    Thin async client for Ollama's local LLM API.
    Supports both streaming and non-streaming completions.
    """

    def __init__(self, model: str = "deepseek-coder:6.7b"):
        self.model = model
        self.base_url = OLLAMA_BASE_URL

    async def generate(self, prompt: str, system: str = "") -> str:
        """Single-shot completion — returns full response string."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": 0.2,   # Low temp = deterministic code
                "top_p": 0.9,
                "num_predict": 4096,
            }
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            return response.json()["response"]

    async def stream(self, prompt: str, system: str = "") -> AsyncGenerator[str, None]:
        """Streaming completion — yields tokens as they arrive."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": True,
            "options": {"temperature": 0.2, "top_p": 0.9, "num_predict": 4096},
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield chunk.get("response", "")
                        if chunk.get("done"):
                            break

    async def list_models(self) -> list[str]:
        """Return available local Ollama models."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]

    async def is_available(self) -> bool:
        """Ping Ollama to check if it's running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
