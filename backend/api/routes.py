import asyncio
import json
from pathlib import Path
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.pipeline import AgentPipeline
from core.llm_client import OllamaClient

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Caps concurrent pipeline/sandbox runs so a burst of requests can't spin up
# unbounded Docker containers or exhaust host resources.
MAX_CONCURRENT_PIPELINES = 3
_PIPELINE_SLOTS = asyncio.Semaphore(MAX_CONCURRENT_PIPELINES)
_PIPELINE_WAIT_TIMEOUT = 5.0  # seconds to wait for a free slot before failing fast

SupportedLanguage = Literal["Python", "JavaScript", "C++"]
SupportedProvider = Literal["ollama", "groq", "gemini"]

# Repo root = two levels up from backend/api/routes.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _safe_index_path(raw: str) -> Optional[Path]:
    """Resolve `raw` and confirm it stays inside the project root.

    Prevents the index-project endpoint from being used to walk / disclose
    arbitrary files on the host.
    """
    try:
        base = Path(raw)
        candidate = (base if base.is_absolute() else _PROJECT_ROOT / base).resolve()
    except Exception:
        return None
    if candidate == _PROJECT_ROOT or _PROJECT_ROOT in candidate.parents:
        return candidate
    return None

# RAG optional import
try:
    from rag.rag_manager import RAGManager
    _rag = RAGManager()
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


# ── Request / Response models ─────────────────────────────────────────────────

import os

def _non_blank_task(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("task must not be blank")
    return v


class GenerateRequest(BaseModel):
    task: str = Field(..., min_length=3, max_length=4000)
    language: SupportedLanguage = "Python"
    framework: str = Field(default="standard library", max_length=100)
    provider: SupportedProvider = "ollama"
    model: str = Field(default="deepseek-coder:6.7b", min_length=1, max_length=200)
    skip_tests: bool = False
    skip_refactor: bool = False

    _validate_task = field_validator("task")(_non_blank_task)


class QuickGenerateRequest(BaseModel):
    task: str = Field(..., min_length=3, max_length=4000)
    language: SupportedLanguage = "Python"
    provider: SupportedProvider = "ollama"
    model: str = Field(default="deepseek-coder:6.7b", min_length=1, max_length=200)

    _validate_task = field_validator("task")(_non_blank_task)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models():
    """Return available models and API key config status for all providers."""
    client = OllamaClient()
    ollama_ok = await client.is_available()
    ollama_models = await client.list_models() if ollama_ok else []

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

    return {
        "ollama": {
            "available": ollama_ok,
            "models": ollama_models,
        },
        "groq": {
            "configured": bool(groq_key),
            "models": [
                "openai/gpt-oss-20b",
                "qwen/qwen3.6-27b",
                "openai/gpt-oss-120b",
            ]
        },
        "gemini": {
            "configured": bool(gemini_key),
            "models": [
                "gemini-3.6-flash",
                "gemini-3.7-flash",
                "gemini-3.5-flash",
            ]
        }
    }


@router.post("/generate/stream")
@limiter.limit("5/minute")
async def generate_stream(request: Request, req: GenerateRequest):
    """
    Stream the full agent pipeline as Server-Sent Events.
    Each event is a JSON object with shape: {step, status, data}

    The frontend subscribes to this and updates the UI in real time.
    """
    full_model = f"{req.provider}:{req.model}" if req.provider else req.model
    pipeline = AgentPipeline(model=full_model)

    async def event_stream():
        try:
            await asyncio.wait_for(_PIPELINE_SLOTS.acquire(), timeout=_PIPELINE_WAIT_TIMEOUT)
        except asyncio.TimeoutError:
            busy_event = {
                "step": "Pipeline",
                "status": "failed",
                "data": {"error": "Server is busy running other generations. Please retry shortly."},
            }
            yield f"data: {json.dumps(busy_event)}\n\n"
            yield "data: [DONE]\n\n"
            return

        try:
            async for event in pipeline.run(
                task=req.task,
                language=req.language,
                framework=req.framework,
                skip_tests=req.skip_tests,
                skip_refactor=req.skip_refactor,
            ):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            _PIPELINE_SLOTS.release()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate/quick")
@limiter.limit("10/minute")
async def generate_quick(request: Request, req: QuickGenerateRequest):
    """
    Non-streaming single-shot code generation (no tests, no debug loop).
    Useful for quick checks and frontend testing.
    """
    from agents.code_generator import CodeGeneratorAgent
    try:
        await asyncio.wait_for(_PIPELINE_SLOTS.acquire(), timeout=_PIPELINE_WAIT_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=429,
            detail="Server is busy running other generations. Please retry shortly.",
        )
    try:
        llm = OllamaClient(model=req.model)
        agent = CodeGeneratorAgent(llm)
        result = await agent.run(req.task, language=req.language)
        return result
    finally:
        _PIPELINE_SLOTS.release()


@router.get("/health/ollama")
async def ollama_health():
    """Check if Ollama is reachable."""
    client = OllamaClient()
    available = await client.is_available()
    return {"ollama_running": available}


# ── RAG Endpoints ─────────────────────────────────────────────────────────────

class IndexProjectRequest(BaseModel):
    directory: str = Field(..., min_length=1, max_length=500)


@router.get("/rag/stats")
async def rag_stats():
    """Return how many chunks are stored in each RAG knowledge base."""
    if not RAG_AVAILABLE:
        return {"available": False, "reason": "chromadb not installed"}
    return {"available": True, **_rag.stats()}


@router.post("/rag/seed-docs")
async def rag_seed_docs():
    """Seed the docs store with built-in FastAPI / Pytest / Python snippets."""
    if not RAG_AVAILABLE:
        return {"available": False}
    result = _rag.seed_docs()
    return {"available": True, **result}


@router.post("/rag/index-project")
@limiter.limit("3/minute")
async def rag_index_project(request: Request, req: IndexProjectRequest):
    """Index a local project directory into the codebase RAG store.

    The directory is confined to the project root; paths outside it are rejected.
    """
    if not RAG_AVAILABLE:
        return {"available": False}
    safe_dir = _safe_index_path(req.directory)
    if safe_dir is None:
        return {"available": True, "status": "failed",
                "error": "directory must be inside the project root"}
    if not safe_dir.exists():
        return {"available": True, "status": "failed",
                "error": f"path does not exist: {safe_dir}"}
    result = _rag.index_project(str(safe_dir))
    return {"available": True, **result}


@router.post("/rag/clear")
async def rag_clear():
    """Clear all RAG stores."""
    if not RAG_AVAILABLE:
        return {"available": False}
    result = _rag.clear_all()
    return {"available": True, **result}