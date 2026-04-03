"""Briefings persistence — SQLite + aiosqlite (simplified)."""
from __future__ import annotations
import asyncio, json, os, time, uuid
from typing import List, Optional
import aiosqlite

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "spark_memory_db", "personal_briefings.db")
_lock = asyncio.Lock()

def _ensure_dir():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

async def _init_schema(conn):
    """Initialize schema if needed (idempotent)."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS briefings (
            id TEXT PRIMARY KEY, title TEXT DEFAULT 'Morning Briefing',
            content_text TEXT NOT NULL, content_audio_url TEXT,
            generated_at REAL NOT NULL, mood TEXT DEFAULT 'NEUTRAL',
            tags TEXT DEFAULT '[]', meta TEXT DEFAULT '{}'
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_briefings_generated ON briefings(generated_at DESC)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_briefings_mood ON briefings(mood)")
    await conn.commit()

def _row_to_dict(row):
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["meta"] = json.loads(d.get("meta") or "{}")
    return d

async def create_briefing(content_text, title="Morning Briefing", content_audio_url=None, mood="NEUTRAL", tags=None, meta=None):
    _ensure_dir()
    briefing_id, now = str(uuid.uuid4()), time.time()
    tags, meta = tags or [], meta or {}
    
    async with _lock:
        async with aiosqlite.connect(_DB_PATH) as db:
            await _init_schema(db)
            await db.execute(
                "INSERT INTO briefings (id,title,content_text,content_audio_url,generated_at,mood,tags,meta) VALUES (?,?,?,?,?,?,?,?)",
                (briefing_id, title, content_text, content_audio_url, now, mood, json.dumps(tags), json.dumps(meta))
            )
            await db.commit()
    return await get_briefing(briefing_id)

async def get_briefing(briefing_id):
    _ensure_dir()
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM briefings WHERE id=?", (briefing_id,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None

async def get_latest_briefing():
    _ensure_dir()
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM briefings ORDER BY generated_at DESC LIMIT 1") as cur:
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None

async def list_briefings(mood=None, limit=100, offset=0):
    _ensure_dir()
    clauses, params = [], []
    if mood: clauses.append("mood=?"); params.append(mood)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _init_schema(db)
        async with db.execute(f"SELECT COUNT(*) FROM briefings {where}", params) as cur:
            total = (await cur.fetchone())[0]
        async with db.execute(f"SELECT * FROM briefings {where} ORDER BY generated_at DESC LIMIT ? OFFSET ?", params + [limit, offset]) as cur:
            rows = await cur.fetchall()
    
    return ([_row_to_dict(r) for r in rows], total)

async def update_briefing(briefing_id, **fields):
    _ensure_dir()
    allowed = {"title", "content_text", "content_audio_url", "mood", "tags", "meta"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates: return await get_briefing(briefing_id)
    
    if "tags" in updates: updates["tags"] = json.dumps(updates["tags"])
    if "meta" in updates: updates["meta"] = json.dumps(updates["meta"])
    
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    async with _lock:
        async with aiosqlite.connect(_DB_PATH) as db:
            await _init_schema(db)
            await db.execute(f"UPDATE briefings SET {set_clause} WHERE id = ?", list(updates.values()) + [briefing_id])
            await db.commit()
    return await get_briefing(briefing_id)

async def delete_briefing(briefing_id):
    _ensure_dir()
    async with _lock:
        async with aiosqlite.connect(_DB_PATH) as db:
            await _init_schema(db)
            cur = await db.execute("DELETE FROM briefings WHERE id=?", (briefing_id,))
            await db.commit()
            return cur.rowcount > 0
