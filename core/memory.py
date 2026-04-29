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