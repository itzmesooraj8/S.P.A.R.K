import chromadb
import uuid
from datetime import datetime

class SparkMemory:
    def __init__(self, persist_directory="./spark_memory_db"):
        """
        Initializes the local ChromaDB client for persistent storage.
        """
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="hive_mind")
        print(f"[MEMORY] Initialized ChromaDB at {persist_directory}")

    def add_memory(self, text, metadata=None):
        """
        Adds a new memory fragment to the vector store.
        """
        if not text or not text.strip():
            return
        
        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()
        
        doc_id = str(uuid.uuid4())
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        print(f"[MEMORY] Stored: {text[:50]}...")

    def retrieve_memory(self, query, n_results=3):
        """
        Retrieves contextually relevant memories for a given query.
        """
        if not query or not query.strip():
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Flatten the results to return just the documents
        documents = results.get("documents", [[]])[0]
        return documents

# Singleton instance for global access
memory_engine = SparkMemory()

if __name__ == "__main__":
    # Quick test
    test_memory = SparkMemory("./test_spark_db")
    test_memory.add_memory("The secret code is 7734.", {"source": "test"})
    print(f"Retrieved: {test_memory.retrieve_memory('What is the secret code?')}")
