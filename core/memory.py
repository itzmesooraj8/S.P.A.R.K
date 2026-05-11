"""Memory v2 - categorized, fact-extracting, context-injecting."""

from __future__ import annotations

import datetime
import os
import sqlite3
import time
import uuid
from enum import Enum

import chromadb

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None


class SparkMemory:
    def __init__(self, db_path="knowledge_base/spark_memory.db"):
        print("Initializing S.P.A.R.K. Memory Core...")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                role TEXT,
                content TEXT
            )
            """
        )
        self.conn.commit()

    def remember(self, role, content):
        """Saves a single message to the database."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO conversation (timestamp, role, content) VALUES (?, ?, ?)",
            (timestamp, role, content),
        )
        self.conn.commit()

    def get_context_string(self, limit=4):
        """Fetches the last few messages to feed to the LLM so it remembers."""
        self.cursor.execute(
            "SELECT role, content FROM conversation ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = self.cursor.fetchall()

        context = ""
        for role, content in reversed(rows):
            context += f"{role}: {content}\n"

        return context

chroma_client = chromadb.PersistentClient(path="knowledge_base/chroma_db")
chroma_collection = chroma_client.get_or_create_collection("spark_episodes")


class MemoryCategory(str, Enum):
    FACT = "fact"
    PREFERENCE = "pref"
    TASK = "task"
    CONVERSATION = "conv"


class MemoryStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=".spark_memory")
        self.collection = self.client.get_or_create_collection("spark_v2")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2") if SentenceTransformer else None
        self._legacy = SparkMemory(db_path="knowledge_base/spark_memory.db")

    def _store_document(self, text: str, category: MemoryCategory) -> None:
        if self.encoder is None:
            self._legacy.remember("assistant", text)
            return

        embedding = self.encoder.encode([text])[0].tolist()
        self.collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[{"category": category.value}],
            ids=[str(uuid.uuid4())],
        )

    def store(self, text: str, category: MemoryCategory = MemoryCategory.CONVERSATION) -> None:
        if not text:
            return
        try:
            self._store_document(text, category)
        except Exception:
            try:
                self._legacy.remember("assistant", text)
            except Exception:
                pass

    def recall(self, query: str, top_k: int = 5, category: MemoryCategory | None = None) -> list[str]:
        if not query or len(query.strip()) < 2:
            return []
        try:
            if self.collection.count() == 0 or self.encoder is None:
                return []

            embedding = self.encoder.encode([query])[0].tolist()
            where = {"category": category.value} if category else None
            kwargs = {"query_embeddings": [embedding], "n_results": min(top_k, self.collection.count())}
            if where:
                kwargs["where"] = where
            results = self.collection.query(**kwargs)
            return results["documents"][0] if results.get("documents") else []
        except Exception:
            pass
        return self._legacy.get_context_string(limit=top_k).splitlines()

    def extract_and_store_facts(self, user_input: str) -> None:
        fact_triggers = [
            "my name is", "i am", "i live in", "i work at",
            "remember that", "don't forget", "i prefer", "i like",
            "i have", "i need to", "my exam", "my birthday",
        ]
        lower = user_input.lower()
        if any(trigger in lower for trigger in fact_triggers):
            try:
                self._store_document(user_input, MemoryCategory.FACT)
            except Exception:
                pass

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0

async def get_context(query: str, top_k: int = 5) -> str:
    """Retrieve relevant memories for the current query."""
    results = chroma_collection.query(query_texts=[query], n_results=top_k)
    if not results.get("documents") or not results["documents"][0]:
        return ""
    return "\n".join(results["documents"][0])

async def save_memory(query: str, response: str):
    """Write this interaction to long-term memory."""
    chroma_collection.add(
        documents=[f"User: {query}\nSPARK: {response}"],
        ids=[f"mem_{int(time.time()*1000)}"],
        metadatas=[{"timestamp": time.time(), "type": "conversation"}]
    )