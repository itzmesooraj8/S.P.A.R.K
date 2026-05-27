from __future__ import annotations

import os
import uvicorn
from security.swarm_guard import SwarmProtocolGuard


if __name__ == "__main__":
    guard = SwarmProtocolGuard()
    reload_enabled = True
    try:
        guard.enforce_launch_gate()
    except Exception as exc:
        os.environ.update(guard.build_isolated_launch_env())
        reload_enabled = False
        print(f"Swarm launch guard fell back to isolated mode: {exc}")

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
        reload_dirs=["api", "audio", "core", "hud", "security", "tools", "config"],
        reload_excludes=[".venv/*", "spark_dev_memory/*", "knowledge_base/chroma_db/*", "**/__pycache__/*"],
    )