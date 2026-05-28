import uuid
from rag.base_store import BaseVectorStore

class ErrorMemoryStore(BaseVectorStore):
    COLLECTION_NAME: str = "error_memory"

    def record_fix(self, error: str, broken_code: str, fixed_code: str, task: str, language: str):
        """
        Record a successful error->fix pair in error memory.
        We embed the task description and the error output to allow similarity search.
        """
        doc = (
            f"Task: {task}\n"
            f"Language: {language}\n"
            f"Error Output:\n{error}\n\n"
            f"Broken Code:\n{broken_code}\n\n"
            f"Fixed Code:\n{fixed_code}"
        )
        
        metadata = {
            "task": task,
            "language": language,
            "error_summary": error[:200].replace("\n", " ")
        }
        
        doc_id = f"fix_{uuid.uuid4().hex}"
        self.add([doc], [metadata], [doc_id])
