from rag.docs_store import DocsStore
from rag.codebase_store import CodebaseStore
from rag.error_memory_store import ErrorMemoryStore

class RAGManager:
    def __init__(self):
        self.docs_store = DocsStore()
        self.codebase_store = CodebaseStore()
        self.error_memory_store = ErrorMemoryStore()

    def get_generation_context(self, task: str, language: str = "Python") -> str:
        """
        Query codebase and docs to construct a RAG generation context prompt block.
        """
        try:
            doc_results = self.docs_store.query(task, n_results=3)
            code_results = self.codebase_store.query(task, n_results=3)
            
            context_blocks = []
            
            if doc_results:
                context_blocks.append("### Relevant Documentation Reference:")
                for res in doc_results:
                    context_blocks.append(f"- {res['content']}")
            
            if code_results:
                context_blocks.append("### Relevant Codebase Snippets:")
                for res in code_results:
                    file_name = res["metadata"].get("file_name", "unknown")
                    context_blocks.append(f"File: {file_name}\n```python\n{res['content']}\n```")
            
            if context_blocks:
                return "\n\n".join(context_blocks)
            return ""
        except Exception:
            return ""

    def get_debug_context(self, error_output: str) -> str:
        """
        Query error memory store to check if we solved a similar error before.
        """
        try:
            results = self.error_memory_store.query(error_output, n_results=1)
            if results and results[0]["score"] > 0.65:
                best_match = results[0]["content"]
                return f"\n### Found Past Fix for Similar Error:\n{best_match}\n"
            return ""
        except Exception:
            return ""

    def record_successful_fix(self, error: str, broken_code: str, fixed_code: str, task: str, language: str):
        """
        Record a successful bugfix to prevent repeating the same mistake.
        """
        try:
            self.error_memory_store.record_fix(error, broken_code, fixed_code, task, language)
        except Exception:
            pass

    def stats(self) -> dict:
        """
        Count entries in each database collection.
        """
        try:
            return {
                "codebase_chunks": self.codebase_store.count(),
                "docs_chunks": self.docs_store.count(),
                "error_memory_chunks": self.error_memory_store.count()
            }
        except Exception as e:
            return {"error": str(e)}

    def seed_docs(self) -> dict:
        """
        Seed built-in documentation.
        """
        try:
            count = self.docs_store.seed_builtins()
            return {"docs_seeded": count, "status": "success"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def index_project(self, directory: str) -> dict:
        """
        Scan and index a directory.
        """
        try:
            return self.codebase_store.index_directory(directory)
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def clear_all(self) -> dict:
        """
        Clear all vector stores.
        """
        try:
            self.docs_store.clear()
            self.codebase_store.clear()
            self.error_memory_store.clear()
            return {"status": "success"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
