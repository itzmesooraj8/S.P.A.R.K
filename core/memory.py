import datetime
import os
import sqlite3


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

import time
import chromadb

chroma_client = chromadb.PersistentClient(path="knowledge_base/chroma_db")
chroma_collection = chroma_client.get_or_create_collection("spark_episodes")

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