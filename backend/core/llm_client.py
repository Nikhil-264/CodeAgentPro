import os
import json
import asyncio
import httpx
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class OllamaClient:
    """
    Multi-provider async LLM client supporting Ollama, Groq, and Google Gemini.
    """

    def __init__(self, model: str = "deepseek-coder:6.7b", provider: str = None):
        self.raw_model = model
        self.provider = provider
        
        # Parse provider prefix if present (e.g. "groq:llama-3.3-70b-versatile")
        if ":" in model and not provider:
            parts = model.split(":", 1)
            if parts[0].lower() in ["ollama", "groq", "gemini"]:
                self.provider = parts[0].lower()
                self.model = parts[1]
            else:
                self.model = model
        else:
            self.model = model

        if not self.provider:
            # Auto-detect by model name pattern
            if "gemini" in self.model.lower():
                self.provider = "gemini"
            elif any(k in self.model.lower() for k in ["groq", "gpt-oss", "qwen", "llama-3.3", "mixtral", "gemma2-9b"]):
                self.provider = "groq"
            else:
                self.provider = "ollama"

        self.base_url = OLLAMA_BASE_URL

    async def generate(self, prompt: str, system: str = "") -> str:
        """Generate single-shot completion from selected provider."""
        if self.provider == "groq":
            return await self._generate_groq(prompt, system)
        elif self.provider == "gemini":
            return await self._generate_gemini(prompt, system)
        else:
            return await self._generate_ollama(prompt, system)

    # ── Ollama Provider ───────────────────────────────────────────────────────
    async def _generate_ollama(self, prompt: str, system: str = "") -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": 0.2,
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
            return response.json().get("response", "")

    # ── Groq Provider ─────────────────────────────────────────────────────────
    async def _generate_groq(self, prompt: str, system: str = "") -> str:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing from environment / .env file.")

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        
        for attempt in range(4):
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 429 and attempt < 3:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                response.raise_for_status()
                res_json = response.json()
                return res_json["choices"][0]["message"]["content"]

    # ── Gemini Provider ───────────────────────────────────────────────────────
    async def _generate_gemini(self, prompt: str, system: str = "") -> str:
        api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment / .env file.")

        model_name = self.model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        
        full_text = f"System Instruction: {system}\n\nUser Request: {prompt}" if system else prompt
        payload = {
            "contents": [
                {
                    "parts": [{"text": full_text}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
            }
        }
        for attempt in range(4):
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 429 and attempt < 3:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                response.raise_for_status()
                res_json = response.json()
                candidates = res_json.get("candidates", [])
                if not candidates:
                    raise ValueError(f"Gemini returned empty candidates: {res_json}")
                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                return text

    # ── Helpers ───────────────────────────────────────────────────────────────
    async def list_models(self) -> list[str]:
        """Return available local Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    async def is_available(self) -> bool:
        """Ping Ollama to check if local server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

# Alias for backward compatibility
LLMClient = OllamaClient
