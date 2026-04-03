"""
Tasks persistence — Synchronous SQLite with asyncio executor (Windows compatible).
Stores at: spark_memory_db/personal_tasks.db
"""

from __future__ import annotations
import asyncio, json, os, sqlite3, time, uuid
from typing import List, Optional

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "spark_memory_db", "personal_tasks.db"
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
    # Create tables individually to avoid threading issues with executescript
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
            status TEXT DEFAULT 'PENDING', priority INT DEFAULT 1, due_date REAL,
            tags TEXT DEFAULT '[]', recurring TEXT, created_at REAL NOT NULL,
            updated_at REAL NOT NULL, meta TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id TEXT PRIMARY KEY, original_task_id TEXT NOT NULL,
            status_snapshot TEXT NOT NULL, completed_at REAL NOT NULL,
            duration_seconds INT, meta TEXT DEFAULT '{}'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(original_task_id)")
    conn.commit()
    conn.close()
    _db_initialized = True

def _row_to_dict(row):
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["meta"] = json.loads(d.get("meta") or "{}")
    return d

def _sync_create_task(title, description="", status="PENDING", priority=1, due_date=None, tags=None, recurring=None, meta=None):
    _init_db()
    task_id, now = str(uuid.uuid4()), time.time()
    tags, meta = tags or [], meta or {}
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "INSERT INTO tasks (id,title,description,status,priority,due_date,tags,recurring,created_at,updated_at,meta) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (task_id, title, description, status, priority, due_date, json.dumps(tags), recurring, now, now, json.dumps(meta))
    )
    conn.commit()
    conn.close()
    return task_id

def _sync_get_task(task_id):
    _init_db()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None

def _sync_list_tasks(status=None, priority=None, limit=100, offset=0):
    _init_db()
    clauses, params = [], []
    if status: clauses.append("status=?"); params.append(status)
    if priority is not None: clauses.append("priority=?"); params.append(priority)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    total = conn.execute(f"SELECT COUNT(*) FROM tasks {where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM tasks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    conn.close()
    return ([_row_to_dict(r) for r in rows], total)

def _sync_update_task(task_id, updates):
    _init_db()
    allowed = {"title", "description", "status", "priority", "due_date", "tags", "recurring", "meta"}
    upd = {k: v for k, v in updates.items() if k in allowed}
    if not upd: return _sync_get_task(task_id)
    if "tags" in upd: upd["tags"] = json.dumps(upd["tags"])
    if "meta" in upd: upd["meta"] = json.dumps(upd["meta"])
    upd["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in upd)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", list(upd.values()) + [task_id])
    conn.commit()
    conn.close()
    return _sync_get_task(task_id)

def _sync_delete_task(task_id):
    _init_db()
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    result = cur.rowcount > 0
    conn.close()
    return result

def _sync_complete_task(task_id):
    _init_db()
    task = _sync_get_task(task_id)
    if not task: return None
    history_id, now = str(uuid.uuid4()), time.time()
    duration = int(now - task.get("created_at", now))
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ("COMPLETED", now, task_id))
    conn.execute("INSERT INTO task_history (id,original_task_id,status_snapshot,completed_at,duration_seconds,meta) VALUES (?,?,?,?,?,?)",
                (history_id, task_id, json.dumps(task), now, duration, json.dumps({})))
    conn.commit()
    conn.close()
    return _sync_get_task(task_id)

def _sync_get_task_history(task_id=None, limit=100, offset=0):
    _init_db()
    clauses, params = [], []
    if task_id: clauses.append("original_task_id=?"); params.append(task_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    total = conn.execute(f"SELECT COUNT(*) FROM task_history {where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM task_history {where} ORDER BY completed_at DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    conn.close()
    history = []
    for row in rows:
        h = dict(row)
        h["status_snapshot"] = json.loads(h.get("status_snapshot") or "{}")
        h["meta"] = json.loads(h.get("meta") or "{}")
        history.append(h)
    return (history, total)

# Async wrappers using executor to avoid threading issues
async def create_task(title, description="", status="PENDING", priority=1, due_date=None, tags=None, recurring=None, meta=None):
    async with _get_lock():
        loop = asyncio.get_event_loop()
        task_id = await loop.run_in_executor(None, _sync_create_task, title, description, status, priority, due_date, tags, recurring, meta)
    return await get_task(task_id)

async def get_task(task_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_task, task_id)

async def list_tasks(status=None, priority=None, tags=None, limit=100, offset=0):
    loop = asyncio.get_event_loop()
    tasks, total = await loop.run_in_executor(None, _sync_list_tasks, status, priority, limit, offset)
    if tags: tasks = [t for t in tasks if any(tag in t["tags"] for tag in tags)]
    return (tasks, total)

async def update_task(task_id, **fields):
    async with _get_lock():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_update_task, task_id, fields)

async def delete_task(task_id):
    async with _get_lock():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_delete_task, task_id)

async def complete_task(task_id):
    async with _get_lock():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_complete_task, task_id)

async def get_task_history(task_id=None, limit=100, offset=0):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_task_history, task_id, limit, offset)
