"""
SPARK Self-Build — Debrief Synthesizer
========================================
After an engagement closes, this module reads the full chain-of-custody log
and asks the SPARK LLM (Ollama) to produce a structured debrief report.

The debrief is stored in the engagement directory as debrief.md and also
written to ChromaDB for long-term memory recall.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_ENGAGEMENTS_DIR = Path(__file__).parent.parent.parent.parent / "spark_dev_memory" / "engagements"
_OLLAMA_URL      = "http://localhost:11434"
_TIMEOUT         = 90

_DEBRIEF_PROMPT = """You are a senior cybersecurity analyst writing a post-engagement debrief.

Engagement: {engagement_id}
Target: {target}
Duration: {duration}

Chain of Custody Events:
{events}

Write a comprehensive debrief report in Markdown with these sections:
## Executive Summary
## Techniques Used
## Key Findings
## Vulnerabilities Identified
## Recommendations
## Lessons Learned

Be specific, professional, and actionable."""


async def _call_ollama(prompt: str) -> str:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_OLLAMA_URL}/api/generate",
                json={"model": "llama3", "prompt": prompt, "stream": False},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                return r.json().get("response", "")
    except Exception as e:
        log.warning("Ollama call failed: %s", e)
    return ""


async def synthesize_debrief(engagement_id: str) -> dict:
    eng_dir   = _ENGAGEMENTS_DIR / engagement_id
    meta_path = eng_dir / "meta.json"
    log_path  = eng_dir / "custody_chain.jsonl"

    if not eng_dir.exists():
        return {"error": f"Engagement '{engagement_id}' not found."}

    meta   = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    events = []
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    duration = "unknown"
    if meta.get("started_at") and meta.get("closed_at"):
        duration = f"{meta['started_at']} → {meta['closed_at']}"

    events_text = "\n".join(
        f"[{e.get('ts', '')}] {e.get('action', '')} — {json.dumps(e.get('data', {}))}"
        for e in events[:100]
    )

    prompt   = _DEBRIEF_PROMPT.format(
        engagement_id = engagement_id,
        target        = meta.get("target", "unknown"),
        duration      = duration,
        events        = events_text or "No events recorded.",
    )
    debrief_md = await _call_ollama(prompt)

    if not debrief_md:
        debrief_md = f"""# Debrief — Engagement {engagement_id}

## Executive Summary
LLM synthesis unavailable (Ollama not running). Manual analysis required.

## Events Recorded
{events_text or 'None'}

## Meta
{json.dumps(meta, indent=2)}
"""

    # Save to disk
    debrief_path = eng_dir / "debrief.md"
    debrief_path.write_text(debrief_md, encoding="utf-8")

    # Attempt ChromaDB storage for long-term memory
    _store_in_chroma(engagement_id, meta.get("target", ""), debrief_md)

    return {
        "engagement_id": engagement_id,
        "target":        meta.get("target"),
        "debrief_path":  str(debrief_path),
        "debrief_md":    debrief_md,
    }


def _store_in_chroma(engagement_id: str, target: str, text: str) -> None:
    try:
        import chromadb
        client = chromadb.PersistentClient(
            path=str(Path(__file__).parent.parent.parent.parent / "spark_dev_memory")
        )
        coll = client.get_or_create_collection("combat_debriefs")
        coll.upsert(
            ids=[engagement_id],
            documents=[text],
            metadatas=[{"target": target, "ts": datetime.now(timezone.utc).isoformat()}],
        )
    except Exception as e:
        log.warning("ChromaDB store failed (non-critical): %s", e)
