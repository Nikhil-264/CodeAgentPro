from rag.base_store import BaseVectorStore

class DocsStore(BaseVectorStore):
    COLLECTION_NAME: str = "docs"

    def seed_builtins(self) -> int:
        """
        Seed the documentation store with helper snippets about FastAPI, pytest, and python.
        """
        docs = [
            "FastAPI endpoint: To define a GET endpoint, use @app.get('/path'). Example:\n@app.get('/health')\nasync def health():\n    return {'status': 'ok'}",
            "FastAPI CORS: To enable CORS in FastAPI, add CORSMiddleware:\nfrom fastapi.middleware.cors import CORSMiddleware\napp.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])",
            "FastAPI StreamingResponse: Use StreamingResponse to stream data. Example:\nfrom fastapi.responses import StreamingResponse\nasync def event_stream():\n    yield 'data: hello\\n\\n'\nreturn StreamingResponse(event_stream(), media_type='text/event-stream')",
            "Pytest basics: Pytest runs tests in test_*.py or *_test.py. Test functions must start with test_. Example:\ndef test_addition():\n    assert 1 + 1 == 2",
            "Pytest async: To test async functions, use pytest-asyncio and mark the test with @pytest.mark.asyncio. Example:\n@pytest.mark.asyncio\nasync def test_async():\n    res = await async_func()\n    assert res is True",
            "Uvicorn: Run a FastAPI app using uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True) in the entrypoint file.",
        ]
        metadatas = [
            {"source": "fastapi_docs", "topic": "fastapi_get", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_cors", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_streaming", "language": "python"},
            {"source": "pytest_docs", "topic": "pytest_basics", "language": "python"},
            {"source": "pytest_docs", "topic": "pytest_asyncio", "language": "python"},
            {"source": "uvicorn_docs", "topic": "uvicorn_run", "language": "python"},
        ]
        ids = [f"doc_builtin_{i}" for i in range(len(docs))]
        
        # Add to the collection using the inherited add method
        self.add(docs, metadatas, ids)
        return len(docs)
