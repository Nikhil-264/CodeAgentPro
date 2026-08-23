import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.pipeline import AgentPipeline
from core.llm_client import OllamaClient

router = APIRouter()

# RAG optional import
try:
    from rag.rag_manager import RAGManager
    _rag = RAGManager()
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


# ── Request / Response models ─────────────────────────────────────────────────

import os

class GenerateRequest(BaseModel):
    task: str
    language: str = "Python"
    framework: str = "standard library"
    provider: str = "ollama"
    model: str = "deepseek-coder:6.7b"
    skip_tests: bool = False
    skip_refactor: bool = False


class QuickGenerateRequest(BaseModel):
    task: str
    language: str = "Python"
    provider: str = "ollama"
    model: str = "deepseek-coder:6.7b"


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
                "llama-3.3-70b-versatile",
                "llama3-70b-8192",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ]
        },
        "gemini": {
            "configured": bool(gemini_key),
            "models": [
                "gemini-3-pro",
                "gemini-3.6-flash",
                "gemini-3.7-pro-preview",
            ]
        }
    }


@router.post("/generate/stream")
async def generate_stream(req: GenerateRequest):
    """
    Stream the full agent pipeline as Server-Sent Events.
    Each event is a JSON object with shape: {step, status, data}

    The frontend subscribes to this and updates the UI in real time.
    """
    full_model = f"{req.provider}:{req.model}" if req.provider else req.model
    pipeline = AgentPipeline(model=full_model)

    async def event_stream():
        async for event in pipeline.run(
            task=req.task,
            language=req.language,
            framework=req.framework,
            skip_tests=req.skip_tests,
            skip_refactor=req.skip_refactor,
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate/quick")
async def generate_quick(req: QuickGenerateRequest):
    """
    Non-streaming single-shot code generation (no tests, no debug loop).
    Useful for quick checks and frontend testing.
    """
    from agents.code_generator import CodeGeneratorAgent
    llm = OllamaClient(model=req.model)
    agent = CodeGeneratorAgent(llm)
    result = await agent.run(req.task, language=req.language)
    return result


@router.get("/health/ollama")
async def ollama_health():
    """Check if Ollama is reachable."""
    client = OllamaClient()
    available = await client.is_available()
    return {"ollama_running": available}


# ── RAG Endpoints ─────────────────────────────────────────────────────────────

class IndexProjectRequest(BaseModel):
    directory: str


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
async def rag_index_project(req: IndexProjectRequest):
    """Index a local project directory into the codebase RAG store."""
    if not RAG_AVAILABLE:
        return {"available": False}
    result = _rag.index_project(req.directory)
    return {"available": True, **result}


@router.post("/rag/clear")
async def rag_clear():
    """Clear all RAG stores."""
    if not RAG_AVAILABLE:
        return {"available": False}
    result = _rag.clear_all()
    return {"available": True, **result}