"""
SPARK Neural Search — ChromaDB Vector Memory + Semantic Search
────────────────────────────────────────────────────────────────────────────────
Provides SPARK with persistent vector memory and neural semantic search.
Uses ChromaDB (already installed + sqlite3 store already on disk).

Collections:
  spark_knowledge   — general knowledge base documents
  spark_conversations — conversation history embeddings
  spark_code        — code snippets and patterns

Endpoints exposed (registered in main.py):
  POST /api/neural-search/index     — add document to vector store
  POST /api/neural-search/query     — semantic search
  GET  /api/neural-search/stats     — collection stats
  DELETE /api/neural-search/document/{id} — remove document
  POST /api/neural-search/bulk-index — bulk add documents
"""

import os
import time
import uuid
import io
from typing import Optional, List, Dict, Any

import chromadb
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

# ── ChromaDB setup ─────────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spark_memory_db")
os.makedirs(_DB_PATH, exist_ok=True)

_client: Optional[chromadb.PersistentClient] = None

def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=_DB_PATH)
    return _client


def get_collection(name: str):
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )


# ── FastAPI Router ─────────────────────────────────────────────────────────────
neural_router = APIRouter(prefix="/api/neural-search", tags=["neural_search"])

VALID_COLLECTIONS = {"spark_knowledge", "spark_conversations", "spark_code", "spark_notes"}


class IndexRequest(BaseModel):
    text: str
    collection: str = "spark_knowledge"
    collection_name: Optional[str] = None
    doc_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    tags: List[str] = []


class BulkIndexRequest(BaseModel):
    documents: List[IndexRequest]


class QueryRequest(BaseModel):
    query: str
    collection: str = "spark_knowledge"
    collection_name: Optional[str] = None
    n_results: int = 5
    where: Optional[Dict[str, Any]] = None
    include_distances: bool = True


class SearchResult(BaseModel):
    id: str
    text: str
    distance: float
    metadata: Dict[str, Any]
    collection: str


def _resolve_collection_name(collection: str, collection_name: Optional[str]) -> str:
    resolved = (collection_name or collection or "spark_knowledge").strip()
    return resolved if resolved in VALID_COLLECTIONS else "spark_knowledge"


def _extract_upload_text(upload: UploadFile, payload: bytes) -> str:
    filename = (upload.filename or "").lower()
    content_type = (upload.content_type or "").lower()

    if filename.endswith(".pdf") or "pdf" in content_type:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(payload))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages).strip()

    return payload.decode("utf-8", errors="ignore").strip()


@neural_router.post("/index")
async def index_document(req: IndexRequest):
    """Add a document to the neural vector store."""
    resolved_collection = _resolve_collection_name(req.collection, req.collection_name)
    if resolved_collection not in VALID_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choose from: {VALID_COLLECTIONS}")

    collection = get_collection(resolved_collection)
    doc_id = req.doc_id or str(uuid.uuid4())

    metadata = {**req.metadata, "tags": ",".join(req.tags), "indexed_at": time.time()}

    collection.upsert(
        ids=[doc_id],
        documents=[req.text],
        metadatas=[metadata],
    )

    return {
        "status": "indexed",
        "doc_id": doc_id,
        "collection": resolved_collection,
        "text_length": len(req.text),
    }


@neural_router.post("/bulk-index")
async def bulk_index(req: BulkIndexRequest):
    """Bulk add documents to the vector store."""
    results = []
    errors = []

    # Group by collection for efficiency
    by_collection: Dict[str, List] = {}
    for doc in req.documents:
        coll = _resolve_collection_name(doc.collection, doc.collection_name)
        by_collection.setdefault(coll, []).append(doc)

    for coll_name, docs in by_collection.items():
        collection = get_collection(coll_name)
        ids, texts, metas = [], [], []
        for doc in docs:
            doc_id = doc.doc_id or str(uuid.uuid4())
            ids.append(doc_id)
            texts.append(doc.text)
            metas.append({**doc.metadata, "tags": ",".join(doc.tags), "indexed_at": time.time()})
            results.append({"doc_id": doc_id, "collection": coll_name})

        try:
            collection.upsert(ids=ids, documents=texts, metadatas=metas)
        except Exception as e:
            errors.append({"collection": coll_name, "error": str(e)})

    return {"indexed": len(results), "results": results, "errors": errors}


@neural_router.post("/query")
async def query_documents(req: QueryRequest):
    """Semantic vector search across a collection."""
    resolved_collection = _resolve_collection_name(req.collection, req.collection_name)
    if resolved_collection not in VALID_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choose from: {VALID_COLLECTIONS}")

    collection = get_collection(resolved_collection)

    try:
        count = collection.count()
        if count == 0:
            return {"results": [], "query": req.query, "collection": req.collection, "total_docs": 0}

        n = min(req.n_results, count)
        include = ["documents", "metadatas", "distances"] if req.include_distances else ["documents", "metadatas"]

        kwargs: Dict[str, Any] = {
            "query_texts": [req.query],
            "n_results": n,
            "include": include,
        }
        if req.where:
            kwargs["where"] = req.where

        results = collection.query(**kwargs)

        hits = []
        docs_list  = results.get("documents",  [[]])[0]
        metas_list = results.get("metadatas",  [[]])[0]
        ids_list   = results.get("ids",        [[]])[0]
        dists_list = results.get("distances",  [[]])[0] if req.include_distances else [0.0] * len(docs_list)

        for doc, meta, rid, dist in zip(docs_list, metas_list, ids_list, dists_list):
            hits.append({
                "id": rid,
                "text": doc,
                "distance": round(float(dist), 4),
                "similarity": round(1 - float(dist), 4),
                "metadata": meta or {},
                "collection": req.collection,
            })

        # Sort by similarity (closest first)
        hits.sort(key=lambda x: x["distance"])

        return {
            "results": hits,
            "query": req.query,
            "collection": resolved_collection,
            "total_docs": count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@neural_router.get("/stats")
async def neural_stats():
    """Return stats across all collections."""
    stats = {}
    for coll_name in VALID_COLLECTIONS:
        try:
            collection = get_collection(coll_name)
            count = collection.count()
            stats[coll_name] = {"documents": count}
        except Exception as e:
            stats[coll_name] = {"documents": 0, "error": str(e)}

    total = sum(v.get("documents", 0) for v in stats.values())
    return {"collections": stats, "total_documents": total, "db_path": _DB_PATH}


@neural_router.delete("/document/{doc_id}")
async def delete_document(doc_id: str, collection: str = "spark_knowledge", collection_name: Optional[str] = None):
    """Remove a document from the vector store."""
    resolved_collection = _resolve_collection_name(collection, collection_name)
    if resolved_collection not in VALID_COLLECTIONS:
        raise HTTPException(status_code=400, detail="Invalid collection")

    coll = get_collection(resolved_collection)
    try:
        coll.delete(ids=[doc_id])
        return {"status": "deleted", "doc_id": doc_id, "collection": resolved_collection}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found or delete failed: {e}")


@neural_router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form("spark_knowledge"),
    tags: str = Form(""),
):
    """Upload a file (txt/md/pdf) and index extracted text into ChromaDB."""
    resolved_collection = _resolve_collection_name(collection, None)
    if resolved_collection not in VALID_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choose from: {VALID_COLLECTIONS}")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    text = _extract_upload_text(file, raw)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    metadata = {
        "source": "upload",
        "filename": file.filename or "upload",
        "content_type": file.content_type or "application/octet-stream",
        "indexed_at": time.time(),
        "tags": ",".join(tag_list),
    }

    collection_ref = get_collection(resolved_collection)
    doc_id = str(uuid.uuid4())
    collection_ref.upsert(ids=[doc_id], documents=[text], metadatas=[metadata])

    return {
        "status": "indexed",
        "doc_id": doc_id,
        "collection": resolved_collection,
        "filename": file.filename,
        "text_length": len(text),
    }


@neural_router.post("/index-knowledge-base")
async def index_knowledge_base():
    """
    Auto-index all files from the knowledge_base/ directory.
    Useful for bootstrapping neural memory on first run.
    """
    kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_base")
    if not os.path.exists(kb_path):
        return {"status": "no_kb_dir", "indexed": 0}

    collection = get_collection("spark_knowledge")
    indexed = 0
    errors = []

    for fname in os.listdir(kb_path):
        fpath = os.path.join(kb_path, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().strip()
            if not text:
                continue
            doc_id = f"kb:{fname}"
            collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[{"source": "knowledge_base", "filename": fname, "indexed_at": time.time()}],
            )
            indexed += 1
        except Exception as e:
            errors.append({"file": fname, "error": str(e)})

    return {"status": "done", "indexed": indexed, "errors": errors}
