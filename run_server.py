import sys
import asyncio
import os
import io

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, app_dir="spark_core")
