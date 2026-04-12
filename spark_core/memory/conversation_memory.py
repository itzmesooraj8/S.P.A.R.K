"""
Persistent conversation memory for SPARK.

Stores chat messages in SQLite and returns a bounded, formatted context block
that can be injected into system prompts for continuity.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite


_DB_PATH = Path(__file__).parent.parent.parent / "spark_memory_db" / "conversation_memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
ON messages(session_id, id);
"""


class ConversationMemory:
    def __init__(
        self,
        db_path: Path = _DB_PATH,
        default_turns: int = 5,
        max_context_messages: int = 20,
    ):
        self._db_path = db_path
        self._default_turns = max(1, int(default_turns))
        self._max_context_messages = max(2, int(max_context_messages))
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def init(self):
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiosqlite.connect(str(self._db_path)) as db:
                await db.executescript(_SCHEMA)
                await db.commit()
            self._initialized = True
            print(f"🧠 [ConversationMemory] SQLite memory ready at {self._db_path}")

    @staticmethod
    def _normalize_session_id(session_id: Optional[str]) -> str:
        sid = (session_id or "").strip()
        return sid[:128] if sid else "default"

    async def save_message(self, session_id: Optional[str], role: str, content: str):
        role = (role or "").strip().lower()
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"Invalid role '{role}'")

        text = (content or "").strip()
        if not text:
            return

        await self.init()
        sid = self._normalize_session_id(session_id)

        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (sid, role, text),
            )
            await db.commit()

    async def get_recent_messages(
        self,
        session_id: Optional[str],
        limit: int,
    ) -> List[Dict[str, str]]:
        await self.init()
        sid = self._normalize_session_id(session_id)
        safe_limit = max(1, min(int(limit), self._max_context_messages))

        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(
                """
                SELECT role, content, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (sid, safe_limit),
            ) as cursor:
                rows = await cursor.fetchall()

        rows.reverse()
        return [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in rows
        ]

    async def get_recent_context(self, session_id: Optional[str], turns: Optional[int] = None) -> str:
        turns_count = self._default_turns if turns is None else max(1, int(turns))
        limit = min(turns_count * 2, self._max_context_messages)
        messages = await self.get_recent_messages(session_id, limit=limit)

        if not messages:
            return ""

        role_map = {
            "user": "User",
            "assistant": "SPARK",
            "system": "System",
        }
        lines = ["[Recent conversation context for continuity]"]
        for msg in messages:
            label = role_map.get(msg["role"], msg["role"].title())
            lines.append(f"{label}: {msg['content']}")
        return "\n".join(lines)
