"""
Persistent ChromaDB store used for long-term semantic memory.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
except Exception:
    chromadb = None


class ChromaStore:
    def __init__(self, persist_dir: Optional[str] = None, collection_name: str = "spark_memory"):
        base_dir = persist_dir or os.getenv(
            "SPARK_CHROMA_DIR",
            str(Path(__file__).resolve().parents[2] / "spark_memory_db" / "chroma"),
        )
        self.persist_dir = str(base_dir)
        self.collection_name = collection_name
        self.available = chromadb is not None
        self._client = None
        self._collection = None

        if self.available:
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"[ChromaStore] Ready at {self.persist_dir} (collection={self.collection_name})")
        else:
            print("[ChromaStore] chromadb not available. Semantic memory disabled.")

    async def add_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> Optional[str]:
        if not self.available or not self._collection:
            return None

        content = (text or "").strip()
        if not content:
            return None

        final_id = doc_id or str(uuid.uuid4())
        final_meta = dict(metadata or {})
        final_meta.setdefault("saved_at", time.time())

        await asyncio.to_thread(
            self._collection.upsert,
            ids=[final_id],
            documents=[content],
            metadatas=[final_meta],
        )
        return final_id

    async def add_chat_turn(
        self,
        *,
        session_id: str,
        role: str,
        text: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> Optional[str]:
        merged = {
            "session_id": (session_id or "default")[:128],
            "role": (role or "unknown")[:32],
            "source": (source or "unknown")[:64],
        }
        if metadata:
            merged.update(metadata)
        return await self.add_text(text=text, metadata=merged, doc_id=doc_id)

    async def semantic_search(
        self,
        query: str,
        *,
        session_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not self.available or not self._collection:
            return []

        q = (query or "").strip()
        if not q:
            return []

        params: Dict[str, Any] = {
            "query_texts": [q],
            "n_results": max(1, min(int(limit), 20)),
            "include": ["documents", "metadatas", "distances"],
        }
        if session_id:
            params["where"] = {"session_id": (session_id or "default")[:128]}

        result = await asyncio.to_thread(lambda: self._collection.query(**params))

        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]

        out: List[Dict[str, Any]] = []
        for idx, doc in enumerate(docs):
            distance = float(dists[idx]) if idx < len(dists) else 1.0
            out.append(
                {
                    "id": ids[idx] if idx < len(ids) else "",
                    "text": doc,
                    "metadata": metas[idx] if idx < len(metas) else {},
                    "distance": distance,
                    "similarity": round(1.0 - distance, 4),
                }
            )

        out.sort(key=lambda item: item["distance"])
        return out

    async def stats(self) -> Dict[str, Any]:
        if not self.available or not self._collection:
            return {"available": False, "collection": self.collection_name}
        count = await asyncio.to_thread(self._collection.count)
        return {
            "available": True,
            "collection": self.collection_name,
            "documents": int(count),
            "persist_dir": self.persist_dir,
        }


chroma_store = ChromaStore()
