import os
import sys
import json
from pathlib import Path
import numpy as np
from fastapi import APIRouter

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.vector_store import SparkVectorMemory

router = APIRouter()
memory = SparkVectorMemory()
TURN_LOG = Path("spark_dev_memory/turns.jsonl")


def _flatten_results(results: dict) -> list[dict]:
    docs = results.get("documents", []) or []
    metas = results.get("metadatas", []) or []
    ids = results.get("ids", []) or []
    embeddings = results.get("embeddings", []) or []
    items: list[dict] = []

    for index, doc_id in enumerate(ids):
        items.append(
            {
                "id": doc_id,
                "text": docs[index] if index < len(docs) else "",
                "metadata": metas[index] if index < len(metas) and metas[index] else {},
                "embedding": embeddings[index] if index < len(embeddings) else None,
            }
        )
    return items


def _read_turn_log() -> list[dict]:
    if not TURN_LOG.exists():
        return []
    turns: list[dict] = []
    for line in TURN_LOG.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            turns.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return turns

def cosine_similarity(a, b):
    try:
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return float(np.dot(a, b) / (a_norm * b_norm))
    except Exception:
        return 0.0

@router.get("/api/memory/graph")
async def get_memory_graph():
    results = memory.collection.get(include=["documents", "metadatas", "embeddings"])
    
    nodes = []
    links = []
    
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    ids = results.get("ids", [])
    embs = results.get("embeddings", [])
    
    # Always include User and S.P.A.R.K. base nodes
    nodes.append({"id": "User", "group": 1, "label": "Sooraj", "content": "The Architect", "radius": 25})
    nodes.append({"id": "SPARK", "group": 1, "label": "S.P.A.R.K.", "content": "Sovereign AI OS", "radius": 25})
    links.append({"source": "User", "target": "SPARK", "value": 5})

    for i, doc_id in enumerate(ids):
        meta = metas[i] if metas and metas[i] else {}
        doc = docs[i] if docs and docs[i] else ""
        role = meta.get("role", "system")
        
        group = 2 if role == "user" else 3 if role == "assistant" else 4
        
        nodes.append({
            "id": doc_id,
            "group": group,
            "label": doc[:30] + "..." if len(doc) > 30 else doc,
            "content": doc,
            "radius": 12
        })
        
        # Link every node to its creator (User or SPARK)
        links.append({
            "source": "User" if role == "user" else "SPARK",
            "target": doc_id,
            "value": 2
        })
        
    if embs and len(embs) > 0:
        threshold = 0.70 # cosine similarity threshold

        # Convert to numpy array for vectorized operations
        embs_array = np.array(embs)

        # Compute norms
        norms = np.linalg.norm(embs_array, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1e-10

        # Normalize embeddings
        embs_norm = embs_array / norms

        # Compute similarity matrix
        sim_matrix = np.dot(embs_norm, embs_norm.T)

        # Extract upper triangle indices (excluding diagonal)
        n = len(embs)
        rows, cols = np.triu_indices(n, k=1)

        # Filter by threshold
        mask = sim_matrix[rows, cols] > threshold

        valid_rows = rows[mask]
        valid_cols = cols[mask]
        valid_sims = sim_matrix[valid_rows, valid_cols]

        # Add links
        for i in range(len(valid_rows)):
            links.append({
                "source": ids[valid_rows[i]],
                "target": ids[valid_cols[i]],
                "value": round(float(valid_sims[i]) * 10, 1)
            })
            
    return {"nodes": nodes, "links": links}


@router.get("/api/memory/recent")
async def get_recent_turns(limit: int = 20):
    turns = _read_turn_log()
    return {"items": turns[-max(limit, 1):]}


@router.get("/api/memory/chroma/recent")
async def get_recent_chroma(limit: int = 30, session_id: str | None = None):
    where = {"session_id": session_id} if session_id else None
    results = memory.collection.get(include=["documents", "metadatas"], where=where)
    items = _flatten_results(results)

    def _sort_key(item: dict) -> float:
        metadata = item.get("metadata") or {}
        timestamp = metadata.get("timestamp")
        if isinstance(timestamp, str):
            try:
                from datetime import datetime

                return datetime.fromisoformat(timestamp).timestamp()
            except Exception:
                return 0.0
        return 0.0

    items.sort(key=_sort_key)
    items = items[-max(limit, 1):]
    for item in items:
        item["saved_at"] = item.get("metadata", {}).get("timestamp")
    return {"items": items}


@router.get("/api/memory/chroma/search")
async def search_chroma(q: str, limit: int = 25, session_id: str | None = None):
    where = {"session_id": session_id} if session_id else None
    results = memory.collection.query(query_texts=[q], n_results=max(limit, 1), where=where)
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    ids = (results.get("ids") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    items = []
    for index, doc_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        item = {
            "id": doc_id,
            "text": documents[index] if index < len(documents) else "",
            "metadata": metadata,
        }
        if index < len(distances) and distances[index] is not None:
            item["similarity"] = max(0.0, 1.0 - float(distances[index]))
        items.append(item)

    return {"items": items}


@router.delete("/api/memory/chroma/{item_id}")
async def delete_chroma_memory(item_id: str):
    memory.collection.delete(ids=[item_id])
    return {"status": "ok", "deleted": item_id}
