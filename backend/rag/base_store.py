"""
Base vector store wrapper around ChromaDB.
All three RAG stores (codebase, docs, error memory) inherit from this.
"""
import chromadb
from chromadb.config import Settings
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "chromadb"


def get_chroma_client() -> chromadb.PersistentClient:
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(DB_PATH),
        settings=Settings(anonymized_telemetry=False),
    )


class BaseVectorStore:
    COLLECTION_NAME: str = "base"

    def __init__(self):
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def clear(self):
        try:
            res = self.collection.get()
            if res and res.get("ids"):
                self.collection.delete(ids=res["ids"])
        except Exception:
            pass

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """
        Local embedding via sentence-transformers.
        Uses a small, fast model — no API calls needed.
        """
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")  # 80MB, fast
        return model.encode(texts, show_progress_bar=False).tolist()

    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        embeddings = self._embed(documents)
        self.collection.upsert(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        embedding = self._embed([query_text])
        results = self.collection.query(
            query_embeddings=embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({"content": doc, "metadata": meta, "score": 1 - dist})
        return output

    def count(self) -> int:
        return self.collection.count()