"""S.P.A.R.K Secure Defensive Backplane Interceptor.

Wraps workspace generation to assert file integrity, verify network telemetry,
and isolate execution threads inside low-priority supervisor workers.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import psutil

from security.self_healing import SelfHealingDaemon
from security.network_anomaly_detector import NetworkAnomalyDetector
from core.orchestrator.supervisor import WorkerSupervisor
from core.workspace_generator import verify_safe_path, SANDBOX_DIR

logger = logging.getLogger("SPARK_DEFENSE_INTERCEPTOR")


class DefensiveInterceptor:
    """Cybernetic defensive backplane checking system states before active operations."""

    @classmethod
    def pre_flight_checks(cls) -> bool:
        """Executes integrity scans and processes table checks to ensure safe workspace conditions."""
        # 1. Assert absolute SHA-256 state configuration signatures via self-healing
        try:
            healer = SelfHealingDaemon()
            healed_files = healer.scan_and_heal()
            if healed_files:
                logger.warning("DEFENSE INTERCEPTOR: Self-healing restored tampered config files: %s", healed_files)
        except Exception as exc:
            logger.error("DEFENSE INTERCEPTOR: Self-healing check failed: %s", exc)

        # 2. Cross-reference active process tables with network anomaly detector
        detector = NetworkAnomalyDetector(
            active_sockets_threshold=float(os.getenv("SPARK_ACTIVE_SOCKETS_THRESHOLD", "120")),
        )
        metrics = detector.sample_network_telemetry()
        detector.evaluate_metrics(metrics)

        # Check connection density for the active process
        try:
            current_proc = psutil.Process(os.getpid())
            connections = current_proc.net_connections(kind="inet")
            active_est = len([c for c in connections if c.status == "ESTABLISHED"])
            logger.info("DEFENSE INTERCEPTOR: Active process ESTABLISHED connections: %d", active_est)
            
            # Flag connection density anomaly if established connections exceed safe threshold (e.g. 15)
            if active_est > 15:
                anomaly_payload = {
                    "timestamp": os.getpid(),
                    "severity": "CRITICAL",
                    "details": f"Excessive established connections ({active_est}) in current process table."
                }
                detector.anomaly_history.append(anomaly_payload)
                logger.warning("DEFENSE INTERCEPTOR: Active process table anomaly: %s", anomaly_payload)
        except Exception as exc:
            logger.debug("DEFENSE INTERCEPTOR: Process table inspection skipped: %s", exc)

        # If any network anomaly is flagged in the anomaly history, drop execution instantly
        if detector.anomaly_history:
            logger.critical("DEFENSE INTERCEPTOR: THREAD TERMINATION. Outbound network anomaly flagged. Execution dropped.")
            raise PermissionError(
                f"Security Exception: Active network anomaly or threat signature detected. "
                f"Details: {detector.anomaly_history[-1]}"
            )
        return True


async def secure_generate_workspace(project_name: str, prompt: str) -> Dict[str, Any]:
    """Intercepts workspace creation to run self-healing, network scans, and worker fork routing."""
    logger.info("DEFENSE INTERCEPTOR: Intercepting generate_workspace for '%s'", project_name)

    # Execute system security pre-flight checks
    DefensiveInterceptor.pre_flight_checks()

    # 3. Generate the workspace JSON manifest using the LLM routing
    # Clean project name
    clean_project_name = re.sub(r'[^a-zA-Z0-9_]', '', project_name.replace(" ", "_")).strip()
    if not clean_project_name:
        clean_project_name = "default_project"

    system_prompt = (
        "You are the SPARK Workspace Generator. Translate the user's coding request into a structured JSON manifest.\n"
        "You must return ONLY a valid raw JSON object. Do NOT wrap in Markdown code blocks, do NOT include conversational text.\n"
        "Format schema:\n"
        "{\n"
        '  "project_name": "string (no spaces)",\n'
        '  "frameworks": ["string (e.g. bootstrap, fontawesome, vanilla)"],\n'
        '  "block_locations": {\n'
        '    "header": "string description",\n'
        '    "content": "string description",\n'
        '    "footer": "string description"\n'
        '  },\n'
        '  "view_parameters": {\n'
        '    "theme": "string (dark or light)",\n'
        '    "viewport": "string"\n'
        '  },\n'
        '  "files": [\n'
        '    {\n'
        '      "path": "string (filename, e.g. index.html or style.css or app.js)",\n'
        '      "content": "string (full source code content)"\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Generate a complete, fully functioning and styled index.html page (and optionally CSS/JS) for the request."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Build a project named '{clean_project_name}' for this prompt: '{prompt}'"}
    ]

    from core.spark_brain import _chat_completion, _local_chat_completion, client
    import asyncio

    llm_output = ""
    try:
        if client is not None:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: _chat_completion(messages, allow_tools=False))
            llm_output = (response.choices[0].message.content or "").strip()
        else:
            llm_output = await _local_chat_completion(messages)
    except Exception as exc:
        logger.warning("DEFENSE INTERCEPTOR: LLM call failed, falling back to local chain: %s", exc)
        try:
            llm_output = await _local_chat_completion(messages)
        except Exception as local_exc:
            logger.error("DEFENSE INTERCEPTOR: Local fallback failed: %s", local_exc)

    clean_json_str = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", llm_output, flags=re.DOTALL).strip()

    manifest: Dict[str, Any] = {}
    try:
        manifest = json.loads(clean_json_str)
    except Exception as parse_exc:
        logger.warning("DEFENSE INTERCEPTOR: Failed to parse manifest JSON, building default emergency manifest: %s", parse_exc)
        manifest = {
            "project_name": clean_project_name,
            "frameworks": ["vanilla"],
            "block_locations": {"header": "Default Header", "content": "Default Content", "footer": "Default Footer"},
            "view_parameters": {"theme": "dark", "viewport": "width=device-width, initial-scale=1.0"},
            "files": [
                {
                    "path": "index.html",
                    "content": f"<!DOCTYPE html><html><head><title>{clean_project_name}</title></head><body><h1>{clean_project_name}</h1><p>Prompt: {prompt}</p></body></html>"
                }
            ]
        }

    # Verify project name matches target folder to prevent path traversal
    safe_proj_dir = verify_safe_path(clean_project_name)
    html_target = os.path.abspath(safe_proj_dir / "index.html")

    # 4. Check for isolation metrics violations
    violation_found = False
    reasons = []

    # Criteria A: Prompt analysis (requesting system level operations)
    unsafe_keywords = ["system", "subprocess", "exec", "shell", "run command", "terminal", "ping", "outbound", "fetch", "websocket"]
    for keyword in unsafe_keywords:
        if keyword in prompt.lower():
            violation_found = True
            reasons.append(f"Prompt requested unsafe keyword: '{keyword}'")

    # Criteria B: Generated files inspection
    files_list = manifest.get("files", [])
    if not isinstance(files_list, list):
        files_list = []

    for file_info in files_list:
        file_path = file_info.get("path", "")
        file_content = file_info.get("content", "")
        
        # B1: Executable script extensions
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".py", ".sh", ".bat", ".ps1", ".exe", ".cmd", ".js"]:
            # Standard Web App JS files are OK if they don't contain backend commands, but non-HTML static files are flagged for safety
            if ext in [".py", ".sh", ".bat", ".ps1", ".exe", ".cmd"]:
                violation_found = True
                reasons.append(f"Executable script file generated: '{file_path}'")
        
        # B2: Malicious coding patterns (system process triggers, websockets, local storage traversal)
        malicious_patterns = [
            r"child_process", r"require\s*\(\s*['\"]os['\"]\s*\)", r"require\s*\(\s*['\"]child_process['\"]\s*\)",
            r"eval\s*\(", r"exec\s*\(", r"os\.system", r"subprocess\.", r"fetch\s*\(", r"WebSocket\s*\(", r"ActiveXObject"
        ]
        for pattern in malicious_patterns:
            if re.search(pattern, file_content):
                violation_found = True
                reasons.append(f"Malicious coding pattern matched: '{pattern}' in '{file_path}'")

    # 5. Handle creation and preview routing based on violation checks
    if violation_found:
        logger.warning("DEFENSE INTERCEPTOR: Strict isolation violation detected! Routing to low-priority worker. Reasons: %s", reasons)
        
        # Spawn via low-priority worker in supervisor
        supervisor = WorkerSupervisor()
        proc = supervisor.fork_worker(
            worker_name=f"isolate_{clean_project_name}",
            script_path="scripts/preview_worker.py",
            args=[clean_project_name, html_target, json.dumps(manifest)]
        )
        
        return {
            "status": "success",
            "project_name": clean_project_name,
            "manifest": manifest,
            "created_files": [f.get("path") for f in files_list],
            "shell_triggered": True,
            "html_preview_path": html_target,
            "isolation_mode": "strict_low_priority_worker",
            "worker_pid": proc.pid if proc else None,
            "violation_reasons": reasons
        }
    else:
        # Static, clean page -> Write files directly in the sandbox and launch preview normal process
        logger.info("DEFENSE INTERCEPTOR: No isolation violations found. Standard sandbox execution.")
        
        safe_proj_dir.mkdir(parents=True, exist_ok=True)
        created_files = []
        for file_info in files_list:
            file_path = file_info.get("path", "")
            file_content = file_info.get("content", "")
            safe_file_path = verify_safe_path(safe_proj_dir / Path(file_path).name)
            safe_file_path.write_text(file_content, encoding="utf-8")
            created_files.append(str(safe_file_path.relative_to(SANDBOX_DIR)))

        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer.exe", html_target])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", html_target])
            else:
                subprocess.Popen(["xdg-open", html_target])
            shell_triggered = True
        except Exception as shell_exc:
            logger.error("DEFENSE INTERCEPTOR: Standard preview spawn failed: %s", shell_exc)
            shell_triggered = False

        return {
            "status": "success",
            "project_name": clean_project_name,
            "manifest": manifest,
            "created_files": created_files,
            "shell_triggered": shell_triggered,
            "html_preview_path": html_target,
            "isolation_mode": "standard_sandbox"
        }
