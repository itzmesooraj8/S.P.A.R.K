from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "audio", "core", "hud", "security", "tools", "config"],
        reload_excludes=[".venv/*", "spark_dev_memory/*", "knowledge_base/chroma_db/*", "**/__pycache__/*"],
    )