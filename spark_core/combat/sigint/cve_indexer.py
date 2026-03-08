"""
SPARK SIGINT — Local CVE Index
================================
Maintains a local SQLite database of CVE records sourced from the NIST NVD 2.0 API.
Supports full-text search, CVSS severity filtering, and incremental sync.

Database location: spark_memory_db/cve_index.sqlite3
"""
import asyncio
import logging
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)

try:
    import aiosqlite
    _AIOSQLITE = True
except ImportError:
    _AIOSQLITE = False

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

_DB_PATH    = Path(__file__).parent.parent.parent.parent / "spark_memory_db" / "cve_index.sqlite3"
_NVD_URL    = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_PER_PAGE   = 2000
_TIMEOUT    = 30


async def _ensure_schema() -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cves (
                cve_id      TEXT PRIMARY KEY,
                description TEXT,
                base_score  REAL,
                severity    TEXT,
                published   TEXT,
                modified    TEXT,
                raw_json    TEXT
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_severity ON cves(severity)"
        )
        await db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS cves_fts USING fts5(cve_id, description, content=cves)"
        )
        await db.commit()


async def _upsert_cves(cve_list: list[dict]) -> int:
    inserted = 0
    async with aiosqlite.connect(_DB_PATH) as db:
        for item in cve_list:
            cve       = item.get("cve", {})
            cve_id    = cve.get("id", "")
            descs     = cve.get("descriptions", [])
            desc      = next((d["value"] for d in descs if d.get("lang") == "en"), "")
            metrics   = cve.get("metrics", {})
            cvss_list = metrics.get("cvssMetricV31", metrics.get("cvssMetricV30", []))
            base_score: Optional[float] = None
            severity: Optional[str]    = None
            if cvss_list:
                cvss_data = cvss_list[0].get("cvssData", {})
                base_score = cvss_data.get("baseScore")
                severity   = cvss_data.get("baseSeverity")

            await db.execute(
                """INSERT OR REPLACE INTO cves
                   (cve_id, description, base_score, severity, published, modified, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    cve_id, desc[:1000], base_score, severity,
                    cve.get("published"), cve.get("lastModified"),
                    json.dumps(cve)[:8000],
                ),
            )
            inserted += 1
        # Rebuild FTS index
        await db.execute("INSERT INTO cves_fts(cves_fts) VALUES('rebuild')")
        await db.commit()
    return inserted


async def sync_nvd_feed() -> dict:
    """Download latest CVEs from NVD and store them in the local DB."""
    if not _AIOSQLITE or not _HTTPX:
        return {"error": "aiosqlite or httpx not available."}

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    await _ensure_schema()

    total_fetched = 0
    start_index   = 0

    async with httpx.AsyncClient(follow_redirects=True) as client:
        while True:
            r = await client.get(
                _NVD_URL,
                params={
                    "resultsPerPage": _PER_PAGE,
                    "startIndex":     start_index,
                },
                headers={"Accept": "application/json"},
                timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                log.error("NVD sync HTTP %s at index %d", r.status_code, start_index)
                break

            data           = r.json()
            total_results  = data.get("totalResults", 0)
            vulns          = data.get("vulnerabilities", [])
            count          = await _upsert_cves(vulns)
            total_fetched += count
            start_index   += len(vulns)

            log.info("NVD sync: %d/%d", start_index, total_results)

            if start_index >= total_results:
                break

            # NVD public rate limit: 5 req/30s without API key
            await asyncio.sleep(6)

    return {
        "status":        "SYNC_COMPLETE",
        "total_indexed": total_fetched,
        "synced_at":     datetime.now(timezone.utc).isoformat(),
    }


async def search_cves(query: str = "", limit: int = 50) -> list[dict]:
    """Search the local CVE index by keyword, CVE-ID, or severity."""
    if not _AIOSQLITE:
        return [{"error": "aiosqlite not available."}]
    if not _DB_PATH.exists():
        return [{"error": "CVE database not yet synced. Call POST /api/combat/sigint/cve/sync first."}]

    await _ensure_schema()

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if query:
            cursor = await db.execute(
                """SELECT c.cve_id, c.description, c.base_score, c.severity, c.published
                   FROM cves c
                   JOIN cves_fts f ON c.cve_id = f.cve_id
                   WHERE cves_fts MATCH ?
                   ORDER BY c.base_score DESC NULLS LAST
                   LIMIT ?""",
                (query, limit),
            )
        else:
            cursor = await db.execute(
                """SELECT cve_id, description, base_score, severity, published
                   FROM cves
                   ORDER BY published DESC
                   LIMIT ?""",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
