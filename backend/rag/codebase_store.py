import os
import uuid
from pathlib import Path
from rag.base_store import BaseVectorStore

class CodebaseStore(BaseVectorStore):
    COLLECTION_NAME: str = "codebase"

    def index_directory(self, directory_path: str) -> dict:
        """
        Recursively scan the directory, chunk all Python files, and index them.
        """
        path = Path(directory_path)
        if not path.exists():
            return {"files_indexed": 0, "chunks_added": 0, "error": f"Path '{directory_path}' does not exist"}

        files_indexed = 0
        chunks_added = 0
        documents = []
        metadatas = []
        ids = []

        # List of directories to ignore
        ignore_dirs = {".venv", "venv", ".git", "__pycache__", "data", "chromadb", "node_modules", "dist", "build"}

        for root, dirs, files in os.walk(path):
            # Prune directories in place to prevent os.walk from visiting them
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        if not content.strip():
                            continue

                        # Simple character-based sliding chunking
                        chunk_size = 800
                        overlap = 150
                        
                        i = 0
                        chunk_idx = 0
                        while i < len(content):
                            chunk = content[i:i + chunk_size]
                            if chunk.strip():
                                documents.append(chunk)
                                metadatas.append({
                                    "file_path": str(file_path.absolute().as_posix()),
                                    "file_name": file_path.name,
                                    "chunk_index": chunk_idx
                                })
                                ids.append(f"code_{uuid.uuid4().hex[:12]}_{chunk_idx}")
                                chunks_added += 1
                                chunk_idx += 1
                            
                            i += chunk_size - overlap
                            if i >= len(content):
                                break
                        
                        files_indexed += 1
                    except Exception as e:
                        # Skip files that can't be read
                        pass

        if documents:
            self.add(documents, metadatas, ids)

        return {
            "files_indexed": files_indexed,
            "chunks_added": chunks_added,
            "status": "success"
        }
