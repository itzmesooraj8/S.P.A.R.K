import os
import sys
import numpy as np
from fastapi import APIRouter

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.vector_store import SparkVectorMemory

router = APIRouter()
memory = SparkVectorMemory()

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
        for i in range(len(embs)):
            for j in range(i + 1, len(embs)):
                sim = cosine_similarity(embs[i], embs[j])
                if sim > threshold:
                    links.append({
                        "source": ids[i],
                        "target": ids[j],
                        "value": round(sim * 10, 1) # scale up for d3 link width/distance
                    })
            
    return {"nodes": nodes, "links": links}
