from __future__ import annotations

import json
import logging
import re
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any


logger = logging.getLogger("SPARK_MEMORY_LOOP")
MEMORY_FILE = Path("spark_dev_memory/turns.jsonl")
MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


@lru_cache(maxsize=1)
def _load_sentence_model():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as exc:
        logger.warning("SentenceTransformer unavailable; falling back to lexical retrieval: %s", exc)
        return None


def _encode(text: str) -> list[float] | None:
    model = _load_sentence_model()
    if model is None:
        return None
    try:
        return model.encode(text).tolist()
    except Exception as exc:
        logger.debug("Embedding encode failed: %s", exc)
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b))
    a_norm = sum(x * x for x in a) ** 0.5
    b_norm = sum(x * x for x in b) ** 0.5
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return numerator / (a_norm * b_norm)


def read_turns() -> list[dict[str, Any]]:
    if not MEMORY_FILE.exists():
        return []

    turns: list[dict[str, Any]] = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            turns.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return turns


def write_turn(role: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = {
        "id": uuid.uuid4().hex,
        "ts": time.time(),
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "tokens": _tokenize(content),
    }
    embedding = _encode(content)
    if embedding is not None:
        entry["embedding"] = embedding

    with MEMORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def retrieve(query: str, k_recent: int = 6, k_semantic: int = 4) -> list[dict[str, Any]]:
    turns = read_turns()
    if not turns:
        return []

    recent = turns[-k_recent:] if k_recent > 0 else []
    semantic: list[dict[str, Any]] = []
    semantic_pool = turns[:-k_recent] if k_recent > 0 else turns

    query_embedding = _encode(query)
    if query_embedding is not None:
        scored: list[tuple[float, dict[str, Any]]] = []
        for turn in semantic_pool:
            embedding = turn.get("embedding")
            if not isinstance(embedding, list):
                continue
            scored.append((_cosine(query_embedding, embedding), turn))
        scored.sort(key=lambda item: item[0], reverse=True)
        semantic = [turn for score, turn in scored[:k_semantic] if score > 0]
    else:
        query_tokens = set(_tokenize(query))
        scored_lexical: list[tuple[float, dict[str, Any]]] = []
        for turn in semantic_pool:
            tokens = set(turn.get("tokens") or _tokenize(str(turn.get("content", ""))))
            if not query_tokens or not tokens:
                continue
            overlap = len(query_tokens & tokens)
            union = len(query_tokens | tokens)
            score = overlap / union if union else 0.0
            scored_lexical.append((score, turn))
        scored_lexical.sort(key=lambda item: item[0], reverse=True)
        semantic = [turn for score, turn in scored_lexical[:k_semantic] if score > 0]

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for turn in semantic + recent:
        key = turn.get("id") or f"{turn.get('ts')}:{turn.get('role')}:{turn.get('content')}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(turn)

    merged.sort(key=lambda item: float(item.get("ts", 0.0)))
    return merged


def summarize_recent(max_turns: int = 50) -> dict[str, Any]:
    """Create a lightweight summary of recent conversation turns.

    Writes a system 'summary' turn to the memory file and returns the summary entry.
    This is intentionally conservative: when embedding models are unavailable it
    falls back to a token-frequency based extractive summary.
    """
    turns = read_turns()
    if not turns:
        return {}

    recent = turns[-max_turns:]
    texts = [str(t.get("content", "")) for t in recent if t.get("content")]
    joined = "\n".join(texts)

    # Try an abstractive summary if sentence-transformers is available
    try:
        from transformers import pipeline
        summarizer = pipeline("summarization")
        # keep input reasonably small
        chunk = joined[:2000]
        summary_text = summarizer(chunk, max_length=120, min_length=30, do_sample=False)[0]["summary_text"]
    except Exception:
        # Fallback: simple keyword-driven extractive summary
        import collections
        tokens = []
        for t in texts:
            tokens.extend(re.findall(r"[a-z0-9_]+", t.lower()))
        counter = collections.Counter(tokens)
        most = [word for word, _ in counter.most_common(12) if len(word) > 3]
        summary_text = "Recent topics: " + ", ".join(most)

    # Persist the summary as a system turn
    entry = write_turn(role="system", content=f"Summary: {summary_text}", metadata={"summary": True, "summarized_turns": len(recent)})
    return entry