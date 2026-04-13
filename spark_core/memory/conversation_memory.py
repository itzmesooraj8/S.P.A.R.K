"""
Persistent conversation memory for SPARK.

Stores chat messages in SQLite and returns a bounded, formatted context block
that can be injected into system prompts for continuity.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite


_DB_PATH = Path(__file__).parent.parent.parent / "spark_memory_db" / "conversation_memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    source TEXT,
    channel TEXT DEFAULT 'chat',
    metadata_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id TEXT,
    source TEXT,
    channel TEXT DEFAULT 'chat',
    transport_session_id TEXT,
    platform_message_id TEXT,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
ON messages(session_id, id);
"""

_MESSAGE_MIGRATION_COLUMNS = {
    "user_id": "TEXT",
    "source": "TEXT",
    "channel": "TEXT DEFAULT 'chat'",
    "transport_session_id": "TEXT",
    "platform_message_id": "TEXT",
    "metadata_json": "TEXT",
}

_SESSIONS_MIGRATION_COLUMNS = {
    "user_id": "TEXT",
    "source": "TEXT",
    "channel": "TEXT DEFAULT 'chat'",
    "metadata_json": "TEXT",
    "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
    "last_seen_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
}


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

    @staticmethod
    def _normalize_optional_text(value: Optional[str], max_len: int = 256) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text[:max_len] if text else None

    @staticmethod
    def _serialize_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(metadata, dict) or not metadata:
            return None
        try:
            return json.dumps(metadata, ensure_ascii=True, default=str)
        except Exception:
            return json.dumps({"serialization_error": True}, ensure_ascii=True)

    @staticmethod
    def _deserialize_metadata(metadata_json: Optional[str]) -> Dict[str, Any]:
        if not metadata_json:
            return {}
        try:
            loaded = json.loads(metadata_json)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}

    async def _ensure_column(
        self,
        db: aiosqlite.Connection,
        table: str,
        column: str,
        ddl: str,
    ):
        async with db.execute(f"PRAGMA table_info({table})") as cursor:
            rows = await cursor.fetchall()
        existing = {row[1] for row in rows}
        if column not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    async def _apply_migrations(self, db: aiosqlite.Connection):
        for column, ddl in _MESSAGE_MIGRATION_COLUMNS.items():
            await self._ensure_column(db, "messages", column, ddl)

        for column, ddl in _SESSIONS_MIGRATION_COLUMNS.items():
            await self._ensure_column(db, "sessions", column, ddl)

        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_platform_message_id ON messages(platform_message_id)"
        )

    async def init(self):
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiosqlite.connect(str(self._db_path)) as db:
                await db.executescript(_SCHEMA)
                await self._apply_migrations(db)
                await db.commit()
            self._initialized = True
            print(f"[ConversationMemory] SQLite memory ready at {self._db_path}")

    @staticmethod
    def _normalize_session_id(session_id: Optional[str]) -> str:
        sid = (session_id or "").strip()
        return sid[:128] if sid else "default"

    async def _touch_session(
        self,
        db: aiosqlite.Connection,
        session_id: str,
        user_id: Optional[str],
        source: Optional[str],
        channel: str,
        metadata_json: Optional[str],
    ):
        await db.execute(
            """
            INSERT INTO sessions (session_id, user_id, source, channel, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                user_id = COALESCE(excluded.user_id, sessions.user_id),
                source = COALESCE(excluded.source, sessions.source),
                channel = COALESCE(excluded.channel, sessions.channel),
                metadata_json = COALESCE(excluded.metadata_json, sessions.metadata_json),
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (session_id, user_id, source, channel, metadata_json),
        )

    async def save_message(
        self,
        session_id: Optional[str],
        role: str,
        content: str,
        *,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
        channel: str = "chat",
        transport_session_id: Optional[str] = None,
        platform_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        role = (role or "").strip().lower()
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"Invalid role '{role}'")

        text = (content or "").strip()
        if not text:
            return

        await self.init()
        sid = self._normalize_session_id(session_id)
        channel_value = self._normalize_optional_text(channel, max_len=32) or "chat"
        user_value = self._normalize_optional_text(user_id, max_len=128)
        source_value = self._normalize_optional_text(source, max_len=64)
        transport_session_value = self._normalize_optional_text(transport_session_id, max_len=128)
        platform_message_value = self._normalize_optional_text(platform_message_id, max_len=128)
        metadata_json = self._serialize_metadata(metadata)

        async with aiosqlite.connect(str(self._db_path)) as db:
            await self._touch_session(
                db,
                sid,
                user_value,
                source_value,
                channel_value,
                metadata_json,
            )
            await db.execute(
                """
                INSERT INTO messages (
                    session_id,
                    user_id,
                    source,
                    channel,
                    transport_session_id,
                    platform_message_id,
                    role,
                    content,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    user_value,
                    source_value,
                    channel_value,
                    transport_session_value,
                    platform_message_value,
                    role,
                    text,
                    metadata_json,
                ),
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

    async def get_last_user_route(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        await self.init()
        sid = self._normalize_session_id(session_id)

        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(
                """
                SELECT user_id, source, channel, transport_session_id, platform_message_id, metadata_json
                FROM messages
                WHERE session_id = ? AND role = 'user'
                ORDER BY id DESC
                LIMIT 1
                """,
                (sid,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return {
            "session_id": sid,
            "user_id": row[0],
            "source": row[1],
            "channel": row[2],
            "transport_session_id": row[3],
            "platform_message_id": row[4],
            "metadata": self._deserialize_metadata(row[5]),
        }

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
