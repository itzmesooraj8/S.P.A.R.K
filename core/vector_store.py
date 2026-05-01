import os
import chromadb
from datetime import datetime
import logging

logger = logging.getLogger("SPARK_MEMORY")

class SparkVectorMemory:
    def __init__(self, db_path="knowledge_base/chroma_db"):
        logger.info("Initializing S.P.A.R.K. Semantic Memory Core (ChromaDB)...")
        os.makedirs(db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection("spark_episodes")
        # Keep an ephemeral log for immediate context, while vector handles long term
        self.ephemeral_context = []

    def remember(self, role: str, content: str, metadata: dict = None):
        """Store a memory with timestamp in both short-term buffer and long-term vector DB."""
        # Short-term buffer
        self.ephemeral_context.append(f"{role}: {content}")
        if len(self.ephemeral_context) > 6:
            self.ephemeral_context.pop(0)
            
        # Long-term semantic store
        if not metadata: metadata = {}
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc_id = f"mem_{datetime.now().timestamp()}_{role}"
        
        # We store the role context together to maintain meaning
        memory_text = f"[{timestamp_str}] {role}: {content}"
        
        self.collection.add(
            documents=[memory_text],
            metadatas=[{"timestamp": timestamp_str, "role": role, **metadata}],
            ids=[doc_id]
        )

    def recall(self, query: str, n=3) -> list:
        """Retrieve top-N semantically relevant memories."""
        if not query or len(query) < 2:
            return []
            
        results = self.collection.query(query_texts=[query], n_results=n)
        if results and results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []

    def get_context_string(self, limit=4, query: str = None):
        """Builds the context block for the LLM. Merges short-term and semantic retrieval."""
        context = "--- RECENT CHAT HISTORY ---\n"
        context += "\n".join(self.ephemeral_context[-limit:])
        
        if query:
            semantic_memories = self.recall(query, n=3)
            if semantic_memories:
                context += "\n\n--- RELEVANT PAST MEMORIES ---\n"
                context += "\n".join(semantic_memories)
                
        return context
        
    def clear_ephemeral(self):
        """Clears the short-term buffer (e.g. on new F9 trigger)."""
        self.ephemeral_context = []
