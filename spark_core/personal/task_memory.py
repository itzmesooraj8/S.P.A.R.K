"""Tasks persistence — SQLite + aiosqlite (simplified for aiosqlite compatibility)."""
from __future__ import annotations
import asyncio, json, os, time, uuid
from typing import List, Optional
import aiosqlite

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "spark_memory_db", "personal_tasks.db")
_lock = asyncio.Lock()

def _ensure_dir():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

async def _init_schema(conn):
    """Initialize schema if needed (idempotent, CREATE TABLE IF NOT EXISTS)."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
            status TEXT DEFAULT 'PENDING', priority INT DEFAULT 1, due_date REAL,
            tags TEXT DEFAULT '[]', recurring TEXT, created_at REAL NOT NULL,
            updated_at REAL NOT NULL, meta TEXT DEFAULT '{}'
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id TEXT PRIMARY KEY, original_task_id TEXT NOT NULL,
            status_snapshot TEXT, completed_at REAL NOT NULL, duration_seconds INT, meta TEXT DEFAULT '{}'
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC)")
    await conn.commit()

def _row_to_dict(row):
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["meta"] = json.loads(d.get("meta") or "{}")
    return d

async def create_task(title, description="", status="PENDING", priority=1, due_date=None, tags=None, recurring=None, meta=None):
    _ensure_dir()
    task_id, now = str(uuid.uuid4()), time.time()
    tags, meta = tags or [], meta or {}
    
    async with _lock:
        async with aiosqlite.connect(_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await _init_schema(db)
            await db.execute(
                "INSERT INTO tasks (id,title,description,status,priority,due_date,tags,recurring,created_at,updated_at,meta) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (task_id, title, description, status, priority, due_date, json.dumps(tags), recurring, now, now, json.dumps(meta))
            )
            await db.commit()
    return await get_task(task_id)

async def get_task(task_id):
    _ensure_dir()
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None

async def list_tasks(status=None, priority=None, tags=None, limit=100, offset=0):
    _ensure_dir()
    clauses, params = [], []
    if status: clauses.append("status=?"); params.append(status)
    if priority is not None: clauses.append("priority=?"); params.append(priority)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _init_schema(db)
        async with db.execute(f"SELECT COUNT(*) FROM tasks {where}", params) as cur:
            total = (await cur.fetchone())[0]
        async with db.execute(f"SELECT * FROM tasks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, offset]) as cur:
            rows = await cur.fetchall()
    
    return ([_row_to_dict(r) for r in rows], total)

async def update_task(task_id, **fields):
    _ensure_dir()
    allowed = {"title", "description", "status", "priority", "due_date", "tags", "recurring", "meta"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates: return await get_task(task_id)
    
    if "tags" in updates: updates["tags"] = json.dumps(updates["tags"])
    if "meta" in updates: updates["meta"] = json.dumps(updates["meta"])
    updates["updated_at"] = time.time()
    
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    async with _lock:
        async with aiosqlite.connect(_DB_PATH) as db:
            await _init_schema(db)
            await db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", list(updates.values()) + [task_id])
            await db.commit()
    return await get_task(task_id)

async def delete_task(task_id):
    _ensure_dir()
    async with _lock:
        async with aiosqlite.connect(_DB_PATH) as db:
            await _init_schema(db)
            cur = await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            await db.commit()
            return cur.rowcount > 0

async def complete_task(task_id):
    _ensure_dir()
    task = await get_task(task_id)
    if not task: return None
    
    history_id, now = str(uuid.uuid4()), time.time()
    created_time, duration = task.get("created_at", now), int(now - (task.get("created_at") or now))
    
    async with _lock:
        async with aiosqlite.connect(_DB_PATH) as db:
            await _init_schema(db)
            await db.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ("COMPLETED", now, task_id))
            await db.execute("INSERT INTO task_history (id,original_task_id,status_snapshot,completed_at,duration_seconds,meta) VALUES (?,?,?,?,?,?)",
                           (history_id, task_id, json.dumps(task), now, duration, json.dumps({})))
            await db.commit()
    return await get_task(task_id)

async def get_task_history(task_id=None, limit=100, offset=0):
    _ensure_dir()
    clauses, params = [], []
    if task_id: clauses.append("original_task_id=?"); params.append(task_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _init_schema(db)
        async with db.execute(f"SELECT COUNT(*) FROM task_history {where}", params) as cur:
            total = (await cur.fetchone())[0]
        async with db.execute(f"SELECT * FROM task_history {where} ORDER BY completed_at DESC LIMIT ? OFFSET ?", params + [limit, offset]) as cur:
            rows = await cur.fetchall()
    
    history = []
    for row in rows:
        h = dict(row)
        h["status_snapshot"] = json.loads(h.get("status_snapshot") or "{}")
        h["meta"] = json.loads(h.get("meta") or "{}")
        history.append(h)
    return (history, total)
