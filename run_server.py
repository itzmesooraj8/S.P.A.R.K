import sys
import asyncio
import os
import io
import socket

sys.setrecursionlimit(2000)

# Force UTF-8 on Windows so emoji in log messages don't crash with cp1252
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.environ.setdefault('PYTHONUTF8', '1')

# Auto-load .env from project root so SPARK_WORKSPACE_DIR and other vars are set
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        print(f"✅ [SPARK] Loaded .env from {_env_path}")
except ImportError:
    pass  # python-dotenv not installed; rely on shell env vars

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port, starting from start_port"""
    for offset in range(max_attempts):
        port = start_port + offset
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            sock.close()
            return port
        except OSError:
            continue
    return None

if __name__ == "__main__":
    # Get port from environment or default
    default_port = int(os.getenv("SPARK_PORT", 8000))
    host = os.getenv("SPARK_HOST", "0.0.0.0")

    # Find an available port
    available_port = find_available_port(default_port)

    if available_port is None:
        print(f"❌ [SPARK] Could not find available port starting from {default_port}")
        sys.exit(1)

    if available_port != default_port:
        print(f"⚠️ [SPARK] Port {default_port} in use, using {available_port} instead")

    os.environ["SPARK_PORT"] = str(available_port)
    print(f"🚀 [SPARK] Starting backend on {host}:{available_port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=available_port,
        reload=False,
        app_dir="spark_core"
    )
