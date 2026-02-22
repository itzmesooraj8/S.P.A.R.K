import os
import chromadb
from typing import List, Dict, Any, Optional

class DevMemory:
    """
    Persistent Vector Memory specifically engineered for Development operations.
    It embeds structured telemetry (mutation logs) to recall past failures and successes
    for a given code node or error trace.
    """
    def __init__(self, persist_dir: str = "./spark_dev_memory"):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name="mutation_history")
        print(f"🧠 [DEV MEMORY] Connected to persistent vector store at {self.persist_dir}")

    def embed_mutation(self, target_node: str, patch_hash: str, success: bool, test_impact: Dict[str, Any], duration_ms: int, error_trace: Optional[str] = None):
        """
        Embeds a detailed summary of a refactor attempt into the vector DB.
        """
        status = "SUCCESS" if success else "FAILURE"
        
        # We build a highly structured text representation for the embedding model to grasp context.
        text_content = (
            f"Mutation Attempt on {target_node}.\n"
            f"Outcome: {status}.\n"
            f"Tests Passed: {test_impact.get('passed', 0)}\n"
            f"Tests Failed: {test_impact.get('failed', 0)}\n"
        )
        
        if error_trace:
            text_content += f"Error Trace: {error_trace}\n"
            
        metadata = {
            "target_node": target_node,
            "patch_hash": patch_hash,
            "success": success,
            "duration_ms": duration_ms
        }
        
        self.collection.add(
            documents=[text_content],
            metadatas=[metadata],
            ids=[patch_hash] # Patch hash is practically unique per mutation iteration
        )
        print(f"🧠 [DEV MEMORY] Embedded mutation result for {target_node} ({status})")

    def recall_mutations_for_node(self, target_node: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Recalls historical mutation outcomes specifically for a structurally defined graph node.
        """
        results = self.collection.query(
            query_texts=[f"Mutation Attempt on {target_node}"],
            n_results=n_results,
            where={"target_node": target_node}
        )
        
        return self._format_results(results)

    def search_similar_errors(self, error_trace: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        If a new mutation crashes with a specific trace, search the DB to see if we've
        encountered and/or resolved a similar stack trace in the past.
        """
        if not error_trace:
            return []
            
        results = self.collection.query(
            query_texts=[f"Error Trace: {error_trace}"],
            n_results=n_results,
            where={"success": False}
        )
        
        return self._format_results(results)

    def _format_results(self, db_results: dict) -> List[Dict[str, Any]]:
        if not db_results.get("documents") or not db_results["documents"][0]:
            return []
            
        formatted = []
        for i in range(len(db_results["documents"][0])):
            formatted.append({
                "document": db_results["documents"][0][i],
                "metadata": db_results["metadatas"][0][i] if db_results.get("metadatas") else {},
                "distance": db_results["distances"][0][i] if db_results.get("distances") else 0.0
            })
            
        return formatted

dev_memory = DevMemory()
