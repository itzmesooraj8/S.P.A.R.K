"""
SPARK Graph Memory — Persistent Knowledge Graph
SQLite-backed entity/relationship store with semantic recall.

Schema:
  entities   : id, type, name, properties (JSON), created_at, updated_at
  relations  : id, source_id, target_id, relation_type, weight, properties (JSON), created_at
  observations: id, entity_id, content, session_id, importance, created_at

This replaces project-level session memory with a world-level, cross-session
knowledge graph that persists across SPARK restarts.
"""
import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

_DB_PATH = Path(__file__).parent.parent.parent / "spark_memory_db" / "knowledge_graph.db"


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    properties  TEXT DEFAULT '{}',
    importance  REAL DEFAULT 1.0,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);

CREATE TABLE IF NOT EXISTS relations (
    id           TEXT PRIMARY KEY,
    source_id    TEXT NOT NULL,
    target_id    TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    weight       REAL DEFAULT 1.0,
    properties   TEXT DEFAULT '{}',
    created_at   REAL NOT NULL,
    FOREIGN KEY(source_id) REFERENCES entities(id),
    FOREIGN KEY(target_id) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
CREATE INDEX IF NOT EXISTS idx_relations_type   ON relations(relation_type);

CREATE TABLE IF NOT EXISTS observations (
    id          TEXT PRIMARY KEY,
    entity_id   TEXT,
    session_id  TEXT,
    content     TEXT NOT NULL,
    importance  REAL DEFAULT 1.0,
    tags        TEXT DEFAULT '[]',
    created_at  REAL NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_obs_entity    ON observations(entity_id);
CREATE INDEX IF NOT EXISTS idx_obs_session   ON observations(session_id);
CREATE INDEX IF NOT EXISTS idx_obs_created   ON observations(created_at);

CREATE TABLE IF NOT EXISTS strategic_objectives (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT DEFAULT 'active',
    priority    INTEGER DEFAULT 5,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);
"""


class KnowledgeGraph:
    """
    Async knowledge graph over SQLite.
    
    Usage:
        await knowledge_graph.init()
        entity_id = await knowledge_graph.upsert_entity("COUNTRY", "Ukraine", {"capital": "Kyiv"})
        await knowledge_graph.add_relation(entity_id, other_id, "BORDERING")
        results = await knowledge_graph.search_entities("Ukraine")
    """

    def __init__(self, db_path: Path = _DB_PATH):
        self._db_path = db_path
        self._initialized = False

    async def init(self):
        if self._initialized:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.executescript(_SCHEMA)
            await db.commit()
        self._initialized = True
        print(f"🧠 [GraphMemory] Knowledge graph initialized at {self._db_path}")

    # ── Entities ──────────────────────────────────────────────────────────────

    async def upsert_entity(
        self,
        entity_type: str,
        name: str,
        properties: Dict[str, Any] = None,
        importance: float = 1.0,
    ) -> str:
        """Create or update an entity by (type, name). Returns entity ID."""
        now = time.time()
        props_str = json.dumps(properties or {})
        async with aiosqlite.connect(str(self._db_path)) as db:
            # Check if exists
            async with db.execute(
                "SELECT id FROM entities WHERE type=? AND name=?", (entity_type, name)
            ) as cur:
                row = await cur.fetchone()

            if row:
                eid = row[0]
                await db.execute(
                    "UPDATE entities SET properties=?, importance=?, updated_at=? WHERE id=?",
                    (props_str, importance, now, eid)
                )
            else:
                eid = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO entities (id,type,name,properties,importance,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                    (eid, entity_type, name, props_str, importance, now, now)
                )
            await db.commit()
        return eid

    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(
                "SELECT id,type,name,properties,importance,created_at,updated_at FROM entities WHERE id=?",
                (entity_id,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "type": row[1], "name": row[2],
            "properties": json.loads(row[3]), "importance": row[4],
            "created_at": row[5], "updated_at": row[6],
        }

    async def search_entities(
        self, query: str, entity_type: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Full-text search on entity name."""
        sql = "SELECT id,type,name,properties,importance FROM entities WHERE name LIKE ?"
        params: list = [f"%{query}%"]
        if entity_type:
            sql += " AND type=?"
            params.append(entity_type)
        sql += " ORDER BY importance DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
        return [
            {"id": r[0], "type": r[1], "name": r[2], "properties": json.loads(r[3]), "importance": r[4]}
            for r in rows
        ]

    # ── Relations ─────────────────────────────────────────────────────────────

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        properties: Dict[str, Any] = None,
    ) -> str:
        rid = str(uuid.uuid4())
        now = time.time()
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO relations (id,source_id,target_id,relation_type,weight,properties,created_at) VALUES (?,?,?,?,?,?,?)",
                (rid, source_id, target_id, relation_type, weight, json.dumps(properties or {}), now)
            )
            await db.commit()
        return rid

    async def get_relations(
        self, entity_id: str, direction: str = "both", relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all relations for an entity. direction: 'out' | 'in' | 'both'"""
        if direction == "out":
            where = "r.source_id=?"
        elif direction == "in":
            where = "r.target_id=?"
        else:
            where = "(r.source_id=? OR r.target_id=?)"

        params: list = [entity_id] if direction != "both" else [entity_id, entity_id]
        type_clause = ""
        if relation_type:
            type_clause = " AND r.relation_type=?"
            params.append(relation_type)

        sql = f"""
            SELECT r.id, r.source_id, r.target_id, r.relation_type, r.weight,
                   e_src.name, e_tgt.name
            FROM relations r
            JOIN entities e_src ON e_src.id = r.source_id
            JOIN entities e_tgt ON e_tgt.id = r.target_id
            WHERE {where}{type_clause}
            ORDER BY r.weight DESC
        """
        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
        return [
            {
                "id": r[0], "source_id": r[1], "target_id": r[2],
                "relation_type": r[3], "weight": r[4],
                "source_name": r[5], "target_name": r[6],
            }
            for r in rows
        ]

    # ── Observations ──────────────────────────────────────────────────────────

    async def add_observation(
        self,
        content: str,
        entity_id: Optional[str] = None,
        session_id: Optional[str] = None,
        importance: float = 1.0,
        tags: List[str] = None,
    ) -> str:
        oid = str(uuid.uuid4())
        now = time.time()
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                "INSERT INTO observations (id,entity_id,session_id,content,importance,tags,created_at) VALUES (?,?,?,?,?,?,?)",
                (oid, entity_id, session_id, content, importance, json.dumps(tags or []), now)
            )
            await db.commit()
        return oid

    async def get_recent_observations(
        self,
        session_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
        min_importance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        where_parts = ["importance >= ?"]
        params: list = [min_importance]
        if session_id:
            where_parts.append("session_id=?")
            params.append(session_id)
        if entity_id:
            where_parts.append("entity_id=?")
            params.append(entity_id)
        where_str = " AND ".join(where_parts)
        params.append(limit)

        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(
                f"SELECT id,entity_id,session_id,content,importance,tags,created_at FROM observations WHERE {where_str} ORDER BY created_at DESC LIMIT ?",
                params
            ) as cur:
                rows = await cur.fetchall()
        return [
            {"id": r[0], "entity_id": r[1], "session_id": r[2], "content": r[3],
             "importance": r[4], "tags": json.loads(r[5]), "created_at": r[6]}
            for r in rows
        ]

    async def search_observations(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        text_query = (query or "").strip()
        if not text_query:
            return []

        where_parts = ["content LIKE ?"]
        params: list = [f"%{text_query}%"]
        if session_id:
            where_parts.append("session_id = ?")
            params.append(session_id)
        params.append(max(1, min(int(limit), 200)))

        where_str = " AND ".join(where_parts)
        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(
                f"""
                SELECT id, entity_id, session_id, content, importance, tags, created_at
                FROM observations
                WHERE {where_str}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            ) as cur:
                rows = await cur.fetchall()

        return [
            {
                "id": r[0],
                "entity_id": r[1],
                "session_id": r[2],
                "content": r[3],
                "importance": r[4],
                "tags": json.loads(r[5]),
                "created_at": r[6],
            }
            for r in rows
        ]

    async def delete_observation(self, observation_id: str) -> bool:
        target_id = (observation_id or "").strip()
        if not target_id:
            return False

        async with aiosqlite.connect(str(self._db_path)) as db:
            cursor = await db.execute("DELETE FROM observations WHERE id = ?", (target_id,))
            await db.commit()
            return (cursor.rowcount or 0) > 0

    # ── Strategic Objectives ──────────────────────────────────────────────────

    async def upsert_objective(
        self, title: str, description: str = "", priority: int = 5
    ) -> str:
        now = time.time()
        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(
                "SELECT id FROM strategic_objectives WHERE title=?", (title,)
            ) as cur:
                row = await cur.fetchone()
            if row:
                oid = row[0]
                await db.execute(
                    "UPDATE strategic_objectives SET description=?,priority=?,updated_at=? WHERE id=?",
                    (description, priority, now, oid)
                )
            else:
                oid = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO strategic_objectives (id,title,description,status,priority,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                    (oid, title, description, "active", priority, now, now)
                )
            await db.commit()
        return oid

    async def get_objectives(self, status: str = "active") -> List[Dict[str, Any]]:
        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(
                "SELECT id,title,description,status,priority,created_at,updated_at FROM strategic_objectives WHERE status=? ORDER BY priority ASC",
                (status,)
            ) as cur:
                rows = await cur.fetchall()
        return [
            {"id": r[0], "title": r[1], "description": r[2], "status": r[3],
             "priority": r[4], "created_at": r[5], "updated_at": r[6]}
            for r in rows
        ]

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_stats(self) -> Dict[str, int]:
        async with aiosqlite.connect(str(self._db_path)) as db:
            counts = {}
            for table in ("entities", "relations", "observations", "strategic_objectives"):
                async with db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
                    row = await cur.fetchone()
                    counts[table] = row[0] if row else 0
        return counts


# ── Singleton ─────────────────────────────────────────────────────────────────
knowledge_graph = KnowledgeGraph()
