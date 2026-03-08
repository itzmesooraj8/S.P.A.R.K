"""
SPARK Music Router
Scans local drives for audio files and streams them via FastAPI.
Endpoints:
  GET  /api/music/files         — list discovered audio files
  POST /api/music/scan          — trigger rescan of known music directories
  GET  /api/music/stream/{id}   — stream an audio file by index ID (supports HTTP Range requests)
"""
import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse, StreamingResponse

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
async def stream_file(file_id: str, range: Optional[str] = Header(None)):
    """
    Stream an audio file. Supports HTTP Range requests for seeking.
    
    Features:
    - Full file streaming: returns 200 OK + entire file
    - Partial content: if Range header provided, returns 206 Partial Content + byte range
    - Prevents seeking beyond file size
    
    Range header examples:
      Range: bytes=0-999         (first 1000 bytes)
      Range: bytes=1000-         (from byte 1000 to end)
      Range: bytes=-500          (last 500 bytes)
    """
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
    
    # Get file size
    file_size = path.stat().st_size
    
    # Parse Range header if provided
    if range:
        try:
            start, end = _parse_range_header(range, file_size)
            
            # Stream only the requested range
            async def range_generator():
                with open(path, "rb") as f:
                    f.seek(start)
                    remaining = end - start + 1
                    chunk_size = 1024 * 256  # 256 KB chunks
                    while remaining > 0:
                        to_read = min(chunk_size, remaining)
                        chunk = f.read(to_read)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
            
            headers = {
                "Content-Length": str(end - start + 1),
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
            }
            return StreamingResponse(
                range_generator(),
                status_code=206,
                media_type=media_type,
                headers=headers,
            )
        except ValueError:
            # Invalid range — fall through to full file response
            pass
    
    # Return full file
    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=entry["name"],
        headers={"Accept-Ranges": "bytes"},
    )


def _parse_range_header(range_header: str, file_size: int) -> Tuple[int, int]:
    """
    Parse HTTP Range header and return (start, end) byte offsets (inclusive).
    
    Raises ValueError if the range is invalid.
    Expected format: 'bytes=<start>-<end>' (either can be omitted).
    """
    if not range_header.startswith("bytes="):
        raise ValueError("Invalid Range header format")
    
    range_spec = range_header[6:]  # Remove 'bytes='
    
    if "-" not in range_spec:
        raise ValueError("Invalid Range format")
    
    parts = range_spec.split("-", 1)
    
    start_str, end_str = parts[0].strip(), parts[1].strip()
    
    # Case 1: bytes=start-end (both specified)
    if start_str and end_str:
        start = int(start_str)
        end = int(end_str)
        if start > end or start >= file_size:
            raise ValueError("Invalid range boundaries")
        end = min(end, file_size - 1)
        return (start, end)
    
    # Case 2: bytes=start- (start specified, to end of file)
    if start_str and not end_str:
        start = int(start_str)
        if start >= file_size:
            raise ValueError("Start offset beyond file size")
        return (start, file_size - 1)
    
    # Case 3: bytes=-length (last N bytes)
    if not start_str and end_str:
        length = int(end_str)
        start = max(0, file_size - length)
        return (start, file_size - 1)
    
    raise ValueError("Invalid Range header")
