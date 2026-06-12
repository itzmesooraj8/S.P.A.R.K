"""Semantic Memory — Facts, knowledge, and user model."""

from __future__ import annotations

import json
import logging
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.memory.semantic")


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    USER_PROFILE = "user_profile"
    KNOWLEDGE = "knowledge"


class SemanticMemory:
    """Persistent semantic memory using ChromaDB."""

    def __init__(self, storage_path: str = ".spark_memory", collection: str = "spark_semantic") -> None:
        self._path = Path(storage_path)
        self._collection_name = collection
        self._client = None
        self._col = None
        self._encoder = None
        self._ensure()

    def _ensure(self) -> None:
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self._path))
            self._col = self._client.get_or_create_collection(self._collection_name)
        except Exception as exc:
            logger.warning("ChromaDB init failed: %s", exc)

    def _get_encoder(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as exc:
                logger.warning("Encoder load failed: %s", exc)
        return self._encoder

    def store(self, text: str, memory_type: MemoryType = MemoryType.FACT, metadata: dict[str, Any] | None = None) -> str:
        encoder = self._get_encoder()
        if encoder is None or self._col is None:
            return ""
        embedding = encoder.encode([text])[0].tolist()
        doc_id = uuid.uuid4().hex[:12]
        meta = {"type": memory_type.value, **(metadata or {})}
        self._col.add(documents=[text], embeddings=[embedding], metadatas=[meta], ids=[doc_id])
        logger.debug("Stored %s: %s", memory_type.value, text[:50])
        return doc_id

    def recall(self, query: str, top_k: int = 5, memory_type: MemoryType | None = None) -> list[str]:
        encoder = self._get_encoder()
        if encoder is None or self._col is None or self._col.count() == 0:
            return []
        embedding = encoder.encode([query])[0].tolist()
        kwargs = dict(query_embeddings=[embedding], n_results=min(top_k, self._col.count()))
        if memory_type:
            kwargs["where"] = {"type": memory_type.value}
        results = self._col.query(**kwargs)
        return results.get("documents", [[]])[0]

    def store_fact(self, fact: str, metadata: dict[str, Any] | None = None) -> str:
        return self.store(fact, MemoryType.FACT, metadata)

    def store_preference(self, pref: str, metadata: dict[str, Any] | None = None) -> str:
        return self.store(pref, MemoryType.PREFERENCE, metadata)

    def extract_facts(self, text: str) -> list[str]:
        triggers = [
            "my name is", "i am", "i live in", "i work at",
            "remember that", "don't forget", "i prefer", "i like",
            "i have", "i need to", "my exam", "my birthday",
        ]
        lower = text.lower()
        found = []
        for trigger in triggers:
            if trigger in lower:
                self.store_fact(text)
                found.append(text)
                break
        return found

    def count(self) -> int:
        if self._col is None:
            return 0
        return self._col.count()
