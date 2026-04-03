"""
Briefings persistence — Synchronous SQLite with asyncio executor (Windows compatible).
Stores at: spark_memory_db/personal_briefings.db
"""

from __future__ import annotations
import asyncio, json, os, sqlite3, time, uuid
from typing import List, Optional

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "spark_memory_db", "personal_briefings.db"
)

_lock = None
_db_initialized = False

def _get_lock():
    """Lazy initialize lock in the current event loop context."""
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock

def _ensure_dir():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

def _init_db():
    global _db_initialized
    if _db_initialized:
        return
    _ensure_dir()
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS briefings (
            id TEXT PRIMARY KEY, title TEXT DEFAULT 'Morning Briefing',
            content_text TEXT NOT NULL, content_audio_url TEXT,
            generated_at REAL NOT NULL, mood TEXT DEFAULT 'NEUTRAL',
            tags TEXT DEFAULT '[]', meta TEXT DEFAULT '{}'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_briefings_generated ON briefings(generated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_briefings_mood ON briefings(mood)")
    conn.commit()
    conn.close()
    _db_initialized = True

def _row_to_dict(row):
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["meta"] = json.loads(d.get("meta") or "{}")
    return d

def _sync_create_briefing(content_text, title="Morning Briefing", content_audio_url=None, mood="NEUTRAL", tags=None, meta=None):
    _init_db()
    briefing_id, now = str(uuid.uuid4()), time.time()
    tags, meta = tags or [], meta or {}
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "INSERT INTO briefings (id,title,content_text,content_audio_url,generated_at,mood,tags,meta) VALUES (?,?,?,?,?,?,?,?)",
        (briefing_id, title, content_text, content_audio_url, now, mood, json.dumps(tags), json.dumps(meta))
    )
    conn.commit()
    conn.close()
    return briefing_id

def _sync_get_briefing(briefing_id):
    _init_db()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM briefings WHERE id=?", (briefing_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None

def _sync_get_latest_briefing():
    _init_db()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM briefings ORDER BY generated_at DESC LIMIT 1").fetchone()
    conn.close()
    return _row_to_dict(row) if row else None

def _sync_list_briefings(mood=None, limit=100, offset=0):
    _init_db()
    clauses, params = [], []
    if mood: clauses.append("mood=?"); params.append(mood)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    total = conn.execute(f"SELECT COUNT(*) FROM briefings {where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM briefings {where} ORDER BY generated_at DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    conn.close()
    return ([_row_to_dict(r) for r in rows], total)

def _sync_update_briefing(briefing_id, updates):
    _init_db()
    allowed = {"title", "content_text", "content_audio_url", "mood", "tags", "meta"}
    upd = {k: v for k, v in updates.items() if k in allowed}
    if not upd: return _sync_get_briefing(briefing_id)
    if "tags" in upd: upd["tags"] = json.dumps(upd["tags"])
    if "meta" in upd: upd["meta"] = json.dumps(upd["meta"])
    set_clause = ", ".join(f"{k} = ?" for k in upd)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(f"UPDATE briefings SET {set_clause} WHERE id = ?", list(upd.values()) + [briefing_id])
    conn.commit()
    conn.close()
    return _sync_get_briefing(briefing_id)

def _sync_delete_briefing(briefing_id):
    _init_db()
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.execute("DELETE FROM briefings WHERE id=?", (briefing_id,))
    conn.commit()
    result = cur.rowcount > 0
    conn.close()
    return result

# Async wrappers using executor
async def create_briefing(content_text, title="Morning Briefing", content_audio_url=None, mood="NEUTRAL", tags=None, meta=None):
    async with _get_lock():
        loop = asyncio.get_event_loop()
        briefing_id = await loop.run_in_executor(None, _sync_create_briefing, content_text, title, content_audio_url, mood, tags, meta)
    return await get_briefing(briefing_id)

async def get_briefing(briefing_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_briefing, briefing_id)

async def get_latest_briefing():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_latest_briefing)

async def list_briefings(mood=None, limit=100, offset=0):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_list_briefings, mood, limit, offset)

async def update_briefing(briefing_id, **fields):
    async with _get_lock():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_update_briefing, briefing_id, fields)

async def delete_briefing(briefing_id):
    async with _get_lock():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_delete_briefing, briefing_id)
