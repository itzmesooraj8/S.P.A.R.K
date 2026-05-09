from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "spark.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("spark.daemon")


@dataclass
class Service:
    name: str
    command: list[str]
    cwd: Path
    process: subprocess.Popen[str] | None = None
    last_restart_at: float = field(default=0.0)


def _python_executable() -> str:
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _tail_output(name: str, process: subprocess.Popen[str]) -> None:
    if not process.stdout:
        return
    for line in process.stdout:
        logger.info("[%s] %s", name, line.rstrip())


def launch(service: Service) -> subprocess.Popen[str]:
    logger.info("Starting %s: %s", service.name, " ".join(service.command))
    child_env = os.environ.copy()
    child_env.setdefault("PYTHONUTF8", "1")
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    process = subprocess.Popen(
        service.command,
        cwd=str(service.cwd),
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    service.process = process
    service.last_restart_at = time.time()
    threading.Thread(target=_tail_output, args=(service.name, process), daemon=True).start()
    return process


def stop_all(services: list[Service]) -> None:
    logger.info("Stopping SPARK services...")
    for service in services:
        process = service.process
        if not process or process.poll() is not None:
            continue
        try:
            process.terminate()
        except Exception:
            pass


def _build_services() -> list[Service]:
    python = _python_executable()
    hud_dir = ROOT
    npm_command = ["cmd.exe", "/c", "npm", "run", "dev"] if os.name == "nt" else ["npm", "run", "dev"]

    services = [
        Service(
            name="api",
            command=[python, "-m", "uvicorn", "api.server:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
        ),
        Service(
            name="core",
            command=[python, "-m", "core.main"],
            cwd=ROOT,
        ),
    ]

    package_json = hud_dir / "package.json"
    if package_json.exists():
        services.append(
            Service(
                name="hud",
                command=npm_command,
                cwd=hud_dir,
            )
        )
    else:
        logger.warning("HUD skipped because %s is missing.", package_json)

    return services


def main() -> int:
    services = _build_services()
    shutdown_requested = threading.Event()

    def _shutdown(*_args: object) -> None:
        shutdown_requested.set()
        stop_all(services)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    for service in services:
        try:
            launch(service)
        except Exception as exc:
            logger.exception("Failed to start %s: %s", service.name, exc)

    logger.info("S.P.A.R.K. daemon is running.")

    while not shutdown_requested.is_set():
        now = time.time()
        for service in services:
            process = service.process
            if not process:
                continue
            if process.poll() is None:
                continue
            if now - service.last_restart_at < 3:
                continue
            logger.warning("%s exited with code %s; restarting.", service.name, process.returncode)
            try:
                launch(service)
            except Exception as exc:
                logger.exception("Failed to restart %s: %s", service.name, exc)
        time.sleep(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())