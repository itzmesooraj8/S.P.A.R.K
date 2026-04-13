from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

from memory.chroma_store import chroma_store
from security.policy import RiskLevel, ToolDefinition
from tools.sandbox import emit_telemetry


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(raw_path: str) -> Path:
    path = Path((raw_path or "").strip())
    if not path:
        raise ValueError("path is empty")
    if path.is_absolute():
        return path
    return (_workspace_root() / path).resolve()


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    content = (text or "").strip()
    if not content:
        return []

    size = max(300, min(chunk_size, 4000))
    ov = max(0, min(overlap, size // 2))
    chunks: List[str] = []
    start = 0
    while start < len(content):
        end = min(start + size, len(content))
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(content):
            break
        start = max(0, end - ov)
    return chunks


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError(f"pypdf is required to ingest PDF files: {exc}")

    reader = PdfReader(str(path))
    pages: List[str] = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_text_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


async def _ingest_chunks(
    chunks: List[str],
    metadata_base: Dict[str, Any],
    doc_prefix: str,
) -> int:
    inserted = 0
    total = len(chunks)
    for idx, chunk in enumerate(chunks):
        metadata = dict(metadata_base)
        metadata["chunk_index"] = idx
        metadata["chunk_total"] = total

        doc_id = f"{doc_prefix}:{idx}"
        saved = await chroma_store.add_text(
            text=chunk,
            metadata=metadata,
            doc_id=doc_id,
        )
        if saved:
            inserted += 1
    return inserted


async def rag_ingest_text(args: Dict[str, Any]) -> str:
    """Ingest raw text into persistent vector memory for retrieval-augmented generation."""
    text = (args or {}).get("text", "")
    if not str(text).strip():
        return "[ERROR] Missing 'text' argument."

    session_id = str((args or {}).get("session_id", "default") or "default")[:128]
    source = str((args or {}).get("source", "manual") or "manual")[:128]
    user_id = str((args or {}).get("user_id", "") or "")[:128]

    chunks = _chunk_text(str(text))
    if not chunks:
        return "[ERROR] Text produced no chunks for ingestion."

    prefix = f"text:{uuid.uuid4().hex[:12]}"
    metadata = {
        "session_id": session_id,
        "source": source,
        "user_id": user_id,
        "kind": "rag_text",
    }

    inserted = await _ingest_chunks(chunks, metadata, prefix)
    emit_telemetry(f"rag:ingest_text {session_id}", f"chunks={inserted}")
    return f"RAG ingest complete. Inserted {inserted}/{len(chunks)} chunks for session '{session_id}'."


async def rag_ingest_file(args: Dict[str, Any]) -> str:
    """Ingest a text or PDF file into persistent vector memory."""
    raw_path = str((args or {}).get("path", "") or "").strip()
    if not raw_path:
        return "[ERROR] Missing 'path' argument."

    try:
        path = _resolve_path(raw_path)
    except Exception as exc:
        return f"[ERROR] Invalid path: {exc}"

    if not path.exists() or not path.is_file():
        return f"[ERROR] File not found: {path}"

    session_id = str((args or {}).get("session_id", "default") or "default")[:128]
    source = str((args or {}).get("source", "file") or "file")[:128]

    try:
        if path.suffix.lower() == ".pdf":
            text = _extract_pdf_text(path)
        else:
            text = _extract_text_file(path)
    except Exception as exc:
        return f"[ERROR] Failed to read file: {exc}"

    if not text:
        return f"[ERROR] No text extracted from file: {path}"

    chunks = _chunk_text(text)
    if not chunks:
        return "[ERROR] File content produced no chunks for ingestion."

    prefix = f"file:{path.name}:{uuid.uuid4().hex[:8]}"
    metadata = {
        "session_id": session_id,
        "source": source,
        "kind": "rag_file",
        "file_name": path.name,
        "file_path": str(path),
    }

    inserted = await _ingest_chunks(chunks, metadata, prefix)
    emit_telemetry(f"rag:ingest_file {path.name}", f"chunks={inserted}")
    return (
        f"RAG file ingest complete for {path.name}. "
        f"Inserted {inserted}/{len(chunks)} chunks into semantic memory."
    )


async def rag_query(args: Dict[str, Any]) -> str:
    """Query semantic memory and return top matching chunks."""
    query = str((args or {}).get("query", "") or "").strip()
    if not query:
        return "[ERROR] Missing 'query' argument."

    session_id = str((args or {}).get("session_id", "") or "").strip()
    try:
        top_k = int((args or {}).get("top_k", 5))
    except Exception:
        top_k = 5
    top_k = max(1, min(top_k, 10))

    try:
        min_similarity = float((args or {}).get("min_similarity", 0.0))
    except Exception:
        min_similarity = 0.0
    min_similarity = max(0.0, min(min_similarity, 1.0))

    rows = await chroma_store.semantic_search(
        query,
        session_id=session_id or None,
        limit=top_k,
    )
    if min_similarity > 0:
        rows = [row for row in rows if float(row.get("similarity", 0.0)) >= min_similarity]

    if not rows:
        scope = f"session '{session_id}'" if session_id else "global"
        return f"No semantic matches found for query in {scope} scope."

    lines = [f"Semantic matches for: {query}"]
    for idx, row in enumerate(rows, start=1):
        text = str(row.get("text", "")).strip().replace("\n", " ")
        snippet = text[:260] + ("..." if len(text) > 260 else "")
        lines.append(f"{idx}. similarity={row.get('similarity', 0.0)} id={row.get('id', '')}")
        lines.append(f"   {snippet}")

    emit_telemetry(f"rag:query {query[:24]}", f"hits={len(rows)}")
    return "\n".join(lines)


async def rag_stats(args: Dict[str, Any]) -> str:
    """Get semantic memory collection statistics."""
    stats = await chroma_store.stats()
    return json.dumps(stats, indent=2, ensure_ascii=True)


rag_tools = [
    ToolDefinition(
        name="rag_ingest_text",
        handler=rag_ingest_text,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"],
    ),
    ToolDefinition(
        name="rag_ingest_file",
        handler=rag_ingest_file,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"],
    ),
    ToolDefinition(
        name="rag_query",
        handler=rag_query,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"],
    ),
    ToolDefinition(
        name="rag_stats",
        handler=rag_stats,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"],
    ),
]
