"""
S.P.A.R.K Vectorized Knowledge Base Indexer
Implements a local document-chunking pipeline feeding ChromaDB (via core.vector_store.SparkVectorMemory),
facilitating semantic retrieval-augmented context injection into worker flows.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
from core.vector_store import SparkVectorMemory

logger = logging.getLogger("SPARK_VECTOR_INDEXER")

class DocumentChunker:
    """Chunks unstructured raw text streams into discrete overlap blocks."""
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """Split text into chunks of clean overlapping text blocks."""
        if not text:
            return []
            
        # Clean basic formatting whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split(' ')
        
        chunks = []
        start_idx = 0
        while start_idx < len(words):
            end_idx = min(start_idx + chunk_size, len(words))
            chunk_words = words[start_idx:end_idx]
            chunks.append(' '.join(chunk_words))
            
            # Step forward by chunk_size - chunk_overlap
            start_idx += (chunk_size - chunk_overlap)
            if start_idx >= len(words) or end_idx == len(words):
                break
                
        return chunks

class VectorKnowledgeIndexer:
    """Manages document ingestion, chunking, and semantic lookup via SparkVectorMemory."""
    
    def __init__(self, db_path: str = "knowledge_base/chroma_db"):
        self.vector_store = SparkVectorMemory(db_path=db_path)
        
    def index_file(self, filepath: str, chunk_size: int = 500, chunk_overlap: int = 50) -> int:
        """Inbound parser reading files, computing chunks, and loading to DB."""
        if not os.path.exists(filepath):
            logger.error(f"Cannot index non-existent file: {filepath}")
            return 0
            
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            filename = os.path.basename(filepath)
            chunks = DocumentChunker.chunk_text(content, chunk_size, chunk_overlap)
            
            logger.info(f"Indexing '{filename}': generated {len(chunks)} chunks.")
            
            for idx, chunk in enumerate(chunks):
                metadata = {
                    "source": filename,
                    "filepath": filepath,
                    "chunk_index": idx,
                    "total_chunks": len(chunks)
                }
                # Use remember to load chunk into ChromaDB
                self.vector_store.remember(
                    role="knowledge_chunk",
                    content=f"Document: {filename} (Chunk {idx+1}/{len(chunks)})\nContent: {chunk}",
                    metadata=metadata
                )
                
            return len(chunks)
        except Exception as e:
            logger.error(f"Failed indexing file {filepath}: {e}")
            return 0

    def query_semantic_context(self, query: str, top_n: int = 3) -> str:
        """Retrieve relevant context strings matching the query from vector memory."""
        results = self.vector_store.recall(query, n=top_n)
        if not results:
            return "No relevant system knowledge context found."
            
        context_block = "=== SEMANTIC RETRIEVAL CONTEXT ===\n"
        for idx, doc in enumerate(results):
            context_block += f"[{idx+1}] {doc}\n\n"
        return context_block.strip()
