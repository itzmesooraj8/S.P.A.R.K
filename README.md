# S.P.A.R.K. (Sovereign Personal AI & Reasoning Kernel)

S.P.A.R.K. is a high-performance, single-screen AI assistant HUD with an autonomous backend. Built for the modern local-AI ecosystem, it is designed from the ground up to operate offline, adapt continuously, and securely orchestrate agents.

## 🚀 True Local Architecture

* **100% Local Processing Priority**: Falls back to external only when necessary.
* **Semantic Memory Engine**: ChromaDB-powered contextual retention for historical pattern matching.
* **Hot-Loadable Skill Engine**: A `watchdog`-driven execution environment. Drop Python skills like the `HackerNewsSkill` into the `skills/` directory, and the system absorbs them without a server reboot.
* **Single-Screen React HUD**: A pure WebSocket-driven SPA interface. No bloated multi-page static routing.

## ⚙️ Quick Start
1. Ensure Python 3.11+ is installed.
2. `pip install -r requirements.txt`
3. Launch the core environment: `python run_server.py`
