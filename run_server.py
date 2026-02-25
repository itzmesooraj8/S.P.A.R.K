import sys
import asyncio
import os

sys.setrecursionlimit(2000)

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
