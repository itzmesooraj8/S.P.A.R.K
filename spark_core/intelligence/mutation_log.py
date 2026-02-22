import json
import os
import hashlib
import time
from typing import Dict, Any, List
from memory.dev_memory import dev_memory
from system.state import unified_state

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "mutation_log.json")
ARCHIVE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "mutation_log_archive.json")
MAX_LOG_ENTRIES = 50

def generate_patch_hash(patch_content: str) -> str:
    return hashlib.sha256(patch_content.encode('utf-8')).hexdigest()

def ensure_log_exists():
    if not os.path.exists(LOG_FILE):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def append_mutation_log(target_node: str, patch_content: str, success: bool, test_impact: Dict[str, Any], duration_ms: int, error_trace: str = None) -> dict:
    ensure_log_exists()
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
            
    patch_hash = generate_patch_hash(patch_content)
    
    entry = {
        "timestamp": time.time(),
        "target_node": target_node,
        "patch_hash": patch_hash,
        "patch_content": patch_content,
        "success": success,
        "duration_ms": duration_ms,
        "test_passed": test_impact.get("passed", 0),
        "test_failed": test_impact.get("failed", 0),
        "test_total": test_impact.get("passed", 0) + test_impact.get("failed", 0),
        "error_trace": error_trace
    }
    
    logs.append(entry)
    
    # Implement log rotation/compaction
    if len(logs) > MAX_LOG_ENTRIES:
        archive_logs = logs[:-MAX_LOG_ENTRIES]
        logs = logs[-MAX_LOG_ENTRIES:]
        
        # Append to archive
        if not os.path.exists(ARCHIVE_FILE):
            with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            try:
                arc_data = json.load(f)
            except json.JSONDecodeError:
                arc_data = []
        arc_data.extend(archive_logs)
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(arc_data, f, indent=2)
    
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2)
        
    unified_state.update("mutation_log", logs)
        
    try:
        dev_memory.embed_mutation(
            target_node=target_node,
            patch_hash=patch_hash,
            success=success,
            test_impact=test_impact,
            duration_ms=duration_ms,
            error_trace=error_trace
        )
    except Exception as e:
        print(f"⚠️ [DEV MEMORY] Failed to embed mutation vector: {e}")
        
    return entry

def get_all_mutations() -> List[Dict[str, Any]]:
    ensure_log_exists()
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []
