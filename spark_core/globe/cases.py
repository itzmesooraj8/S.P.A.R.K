"""
Cases / Incidents persistence — SQLite via aiosqlite.

Stored at: spark_memory_db/cases.db
Endpoint contract matches src/types/contracts.ts :: CaseItem
"""

from __future__ import annotations
import asyncio
import json
import os
import time
import uuid
from typing import List, Optional

import aiosqlite

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "spark_memory_db", "cases.db"
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS cases (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    severity    TEXT NOT NULL DEFAULT 'medium',
    lat         REAL,
    lng         REAL,
    layer       TEXT,
    tags        TEXT NOT NULL DEFAULT '[]',   -- JSON array
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    meta        TEXT NOT NULL DEFAULT '{}'    -- JSON object
);
CREATE INDEX IF NOT EXISTS idx_cases_severity ON cases(severity);
CREATE INDEX IF NOT EXISTS idx_cases_created  ON cases(created_at DESC);
"""

_lock = asyncio.Lock()          # serialise concurrent writes


async def _db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = await aiosqlite.connect(_DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(_CREATE_TABLE)
    await conn.commit()
    return conn


def _row_to_dict(row: aiosqlite.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["meta"] = json.loads(d.get("meta") or "{}")
    return d


# ─────────────── Public API ────────────────────────────────────────────────

async def create_case(
    title: str,
    description: str = "",
    severity: str = "medium",
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    layer: Optional[str] = None,
    tags: List[str] = [],
    meta: dict = {},
) -> dict:
    case_id = str(uuid.uuid4())
    now = time.time()
    async with _lock:
        async with await _db() as conn:
            await conn.execute(
                """INSERT INTO cases
                   (id, title, description, severity, lat, lng, layer, tags, created_at, updated_at, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (case_id, title, description, severity, lat, lng, layer,
                 json.dumps(tags), now, now, json.dumps(meta)),
            )
            await conn.commit()
    return await get_case(case_id)  # type: ignore


async def get_case(case_id: str) -> Optional[dict]:
    async with await _db() as conn:
        async with conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None


async def list_cases(
    severity: Optional[str] = None,
    layer: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[dict], int]:
    clauses = []
    params: list = []
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if layer:
        clauses.append("layer = ?")
        params.append(layer)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    async with await _db() as conn:
        async with conn.execute(f"SELECT COUNT(*) FROM cases {where}", params) as cur:
            total: int = (await cur.fetchone())[0]
        async with conn.execute(
            f"SELECT * FROM cases {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ) as cur:
            rows = await cur.fetchall()
    return ([_row_to_dict(r) for r in rows], total)


async def update_case(case_id: str, **fields) -> Optional[dict]:
    """Partial update — only supplied fields are changed."""
    allowed = {"title", "description", "severity", "lat", "lng", "layer", "tags", "meta"}
    updates: dict = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return await get_case(case_id)

    # Serialise JSON fields
    if "tags" in updates:
        updates["tags"] = json.dumps(updates["tags"])
    if "meta" in updates:
        updates["meta"] = json.dumps(updates["meta"])
    updates["updated_at"] = time.time()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    async with _lock:
        async with await _db() as conn:
            await conn.execute(
                f"UPDATE cases SET {set_clause} WHERE id = ?",
                list(updates.values()) + [case_id],
            )
            await conn.commit()
    return await get_case(case_id)


async def delete_case(case_id: str) -> bool:
    async with _lock:
        async with await _db() as conn:
            cur = await conn.execute("DELETE FROM cases WHERE id=?", (case_id,))
            await conn.commit()
            return cur.rowcount > 0
