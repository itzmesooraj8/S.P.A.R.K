"""
SPARK Music Router
Scans local drives for audio files and streams them via FastAPI.
Endpoints:
  GET  /api/music/files         — list discovered audio files
  POST /api/music/scan          — trigger rescan of known music directories
  GET  /api/music/stream/{id}   — stream an audio file by index ID
"""
import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/music", tags=["music"])

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma", ".opus"}

# Common music directories (Windows + Linux/Mac friendly)
_SCAN_DIRS: List[Path] = []

def _default_scan_dirs() -> List[Path]:
    candidates = []
    home = Path.home()
    for d in ["Music", "music", "Downloads", "Desktop", "Documents"]:
        p = home / d
        if p.exists():
            candidates.append(p)
    # Also check for external drives / OneDrive Music
    for drive in ["C:\\", "D:\\", "E:\\"]:
        for subdir in ["Music", "Users\\Public\\Music"]:
            p = Path(drive) / subdir
            if p.exists():
                candidates.append(p)
    return candidates


# In-memory catalog: id → file info
_catalog: Dict[str, dict] = {}
_last_scan_time: float = 0.0


def _scan_audio_files(directories: List[Path] = None) -> Dict[str, dict]:
    dirs = directories or _default_scan_dirs()
    found: Dict[str, dict] = {}
    for base in dirs:
        try:
            for root, _, files in os.walk(base):
                for fname in files:
                    ext = Path(fname).suffix.lower()
                    if ext in AUDIO_EXTENSIONS:
                        fullpath = Path(root) / fname
                        file_id = hashlib.md5(str(fullpath).encode()).hexdigest()[:12]
                        try:
                            stat = fullpath.stat()
                            found[file_id] = {
                                "id": file_id,
                                "name": fname,
                                "title": Path(fname).stem,
                                "path": str(fullpath),
                                "ext": ext.lstrip("."),
                                "size_mb": round(stat.st_size / 1_048_576, 2),
                                "modified": stat.st_mtime,
                            }
                        except Exception:
                            continue
        except PermissionError:
            continue
    return found


@router.get("/files")
async def list_files():
    """Return the current music catalog (auto-scans on first call)."""
    global _catalog, _last_scan_time
    if not _catalog or (time.time() - _last_scan_time) > 300:
        _catalog = _scan_audio_files()
        _last_scan_time = time.time()
    files = sorted(_catalog.values(), key=lambda x: x["title"])
    return {
        "count": len(files),
        "files": files,
        "scanned_at": _last_scan_time,
    }


@router.post("/scan")
async def trigger_scan(directories: List[str] = None):
    """Force a fresh audio file scan."""
    global _catalog, _last_scan_time
    dirs = [Path(d) for d in directories] if directories else None
    _catalog = _scan_audio_files(dirs)
    _last_scan_time = time.time()
    return {
        "status": "ok",
        "found": len(_catalog),
        "files": sorted(_catalog.values(), key=lambda x: x["title"]),
    }


@router.get("/stream/{file_id}")
async def stream_file(file_id: str):
    """Stream an audio file. The frontend can use this as an <audio> src."""
    global _catalog
    if not _catalog:
        _catalog = _scan_audio_files()
        
    entry = _catalog.get(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Track not found. Try rescanning.")
    
    path = Path(entry["path"])
    if not path.exists():
        # Remove stale entry
        _catalog.pop(file_id, None)
        raise HTTPException(status_code=404, detail="Audio file no longer exists on disk.")
    
    media_type_map = {
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "wma": "audio/x-ms-wma",
        "opus": "audio/opus",
    }
    media_type = media_type_map.get(entry["ext"], "audio/mpeg")
    return FileResponse(path=str(path), media_type=media_type, filename=entry["name"])
