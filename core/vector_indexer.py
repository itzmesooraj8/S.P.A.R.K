"""S.P.A.R.K Vectorized Knowledge Base Indexer.

Indexes local documents into ChromaDB while enforcing absolute-path allowlists so
offline retrieval stays inside trusted workspace trees.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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
    
    def __init__(self, db_path: str = "knowledge_base/chroma_db", authorized_roots: Optional[Iterable[str]] = None):
        self.vector_store = SparkVectorMemory(db_path=db_path)
        self.authorized_roots = self._normalize_roots(authorized_roots)

    @staticmethod
    def _normalize_roots(authorized_roots: Optional[Iterable[str]]) -> List[Path]:
        roots = list(authorized_roots or [os.getcwd(), os.path.join(os.getcwd(), "knowledge_base")])
        normalized: List[Path] = []
        for root in roots:
            try:
                normalized.append(Path(root).resolve())
            except Exception:
                continue
        return normalized

    def _resolve_authorized_path(self, filepath: str) -> Path:
        candidate = Path(filepath).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Cannot index non-existent file: {filepath}")
        if self.authorized_roots:
            allowed = any(candidate == root or root in candidate.parents for root in self.authorized_roots)
            if not allowed:
                raise PermissionError(f"Security violation: '{candidate}' is outside authorized local roots.")
        return candidate

    def _ingest_chunks(self, filepath: Path, chunks: List[str]) -> int:
        filename = filepath.name
        for idx, chunk in enumerate(chunks):
            metadata = {
                "source": filename,
                "filepath": str(filepath),
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "path_depth": len(filepath.parents),
            }
            self.vector_store.remember(
                role="knowledge_chunk",
                content=f"Document: {filename} (Chunk {idx + 1}/{len(chunks)})\nContent: {chunk}",
                metadata=metadata,
            )
        return len(chunks)

    def index_text(self, text: str, source_name: str = "inline_document", chunk_size: int = 500, chunk_overlap: int = 50) -> int:
        chunks = DocumentChunker.chunk_text(text, chunk_size, chunk_overlap)
        if not chunks:
            return 0
        pseudo_path = Path(source_name).resolve()
        return self._ingest_chunks(pseudo_path, chunks)
        
    def index_file(self, filepath: str, chunk_size: int = 500, chunk_overlap: int = 50) -> int:
        """Inbound parser reading files, computing chunks, and loading to DB."""
        try:
            resolved_path = self._resolve_authorized_path(filepath)
            with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            chunks = DocumentChunker.chunk_text(content, chunk_size, chunk_overlap)

            logger.info(f"Indexing '{resolved_path.name}': generated {len(chunks)} chunks.")
            return self._ingest_chunks(resolved_path, chunks)
        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"Failed indexing file {filepath}: {e}")
            return 0

    def index_directory(self, directory_path: str, recursive: bool = True, extensions: Optional[Iterable[str]] = None) -> int:
        """Indexes a directory tree after enforcing the local root allowlist."""
        resolved_dir = Path(directory_path).expanduser().resolve()
        if self.authorized_roots:
            allowed = any(resolved_dir == root or root in resolved_dir.parents for root in self.authorized_roots)
            if not allowed:
                raise PermissionError(f"Security violation: '{resolved_dir}' is outside authorized local roots.")

        indexed = 0
        ext_filter = {ext.lower() for ext in extensions} if extensions else None
        iterator = resolved_dir.rglob("*") if recursive else resolved_dir.glob("*")
        for path in iterator:
            if not path.is_file():
                continue
            if ext_filter and path.suffix.lower() not in ext_filter:
                continue
            indexed += self.index_file(str(path))
        return indexed

    def query_semantic_context(self, query: str, top_n: int = 3) -> str:
        """Retrieve relevant context strings matching the query from vector memory."""
        results = self.vector_store.recall(query, n=top_n)
        if not results:
            return "No relevant system knowledge context found."
            
        context_block = "=== SEMANTIC RETRIEVAL CONTEXT ===\n"
        for idx, doc in enumerate(results):
            context_block += f"[{idx+1}] {doc}\n\n"
        return context_block.strip()

    def local_search(self, query: str, top_n: int = 3) -> list[str]:
        """Returns raw semantic matches without any cloud lookup."""
        return self.vector_store.recall(query, n=top_n)
