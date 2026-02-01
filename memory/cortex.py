import sqlite3
import datetime
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cortex.db")

def init_db():
    """Initialize the memory database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Simple key-value store for specific facts, plus a log for general memories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS confident_facts (
            key TEXT PRIMARY KEY,
            value TEXT,
            category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            tags TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_fact(key, value, category="general"):
    """Save a specific fact (e.g., user_name = 'Sooraj'). Overwrites existing keys."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO confident_facts (key, value, category, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (key.lower(), value, category, datetime.datetime.now()))
    conn.commit()
    conn.close()
    print(f"💾 [Cortex] Saved Fact: {key} = {value}")

def save_memory(content, tags=""):
    """Save a general episodic memory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO episodic_memory (content, tags, timestamp)
        VALUES (?, ?, ?)
    ''', (content, tags, datetime.datetime.now()))
    conn.commit()
    conn.close()
    print(f"💾 [Cortex] Logged Memory: {content[:50]}...")

def get_fact(key):
    """Retrieve a specific fact by key."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM confident_facts WHERE key = ?', (key.lower(),))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def search_memories(query_text):
    """Simple keyword search in memories."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Simple LIKE query
    cursor.execute('SELECT content, timestamp FROM episodic_memory WHERE content LIKE ? ORDER BY timestamp DESC LIMIT 5', (f'%{query_text}%',))
    results = cursor.fetchall()
    conn.close()
    return results

def get_all_facts():
    """Get all confident facts to inject into context."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM confident_facts')
    results = cursor.fetchall()
    conn.close()
    return {k: v for k, v in results}

# Initialize on module load
init_db()
