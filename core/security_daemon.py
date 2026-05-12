"""
S.P.A.R.K Security Daemon - Continuous background threat detection and response.
Monitors for suspicious processes, file tampering, and network anomalies.
Auto-alerts, blocks threats via Windows Firewall, and logs to security_log.json.
"""

import asyncio
import hashlib
import json
import logging
import os
import psutil
import socket
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SecurityDaemon:
    """Background threat detector and responder."""

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize security daemon.
        
        Args:
            config: Config dict with security settings (from env or passed)
        """
        self.config = config or self._load_config()
        self.enabled = self.config.get("security.enabled", True)
        self.threat_log_file = Path(self.config.get("security.log_file", "security_log.json"))
        self.threat_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Default suspicious list: ONLY explicitly malicious processes
        # Standard Windows system processes are NOT included by default
        self.default_suspicious_processes = [
            "wscript.exe",  # VBScript
            "cscript.exe",  # JScript
        ]
        
        # Config thresholds - check for user-configured blocked processes
        self.suspicious_processes = self._get_suspicious_processes()
        
        self.file_watch_dirs = self.config.get("security.file_watch_dirs", [
            "core/",
            "spark/",
            "api/",
        ])
        self.network_anomaly_threshold = int(self.config.get("security.network_anomaly_threshold", 100))
        self.network_anomaly_check_enabled = self.config.get("security.network_anomaly_check_enabled", False)
        self.firewall_auto_block = self.config.get("security.firewall_auto_block", True)
        
        # Runtime state
        self.file_hashes = {}  # Track file hashes for tampering detection
        self.connection_count = {}  # Track connection counts per IP
        self.threat_throttle = {}  # Throttle repeated alerts (cache threat signatures + timestamps)
        self.daemon_thread = None
        self.running = False
    
    def _get_suspicious_processes(self) -> list[str]:
        """Get suspicious process list from user config or default.
        
        User can override with SPARK_BLOCKED_PROCESSES env var (comma-separated).
        This keeps the system processes (cmd.exe, powershell.exe, python.exe, etc.)
        off the default blocked list unless explicitly configured.
        """
        user_blocked = os.getenv("SPARK_BLOCKED_PROCESSES", "").strip()
        if user_blocked:
            blocked = [p.strip() for p in user_blocked.split(",") if p.strip()]
            logger.info(f"Using user-configured blocked processes: {blocked}")
            return blocked
        return self.default_suspicious_processes

    def _load_config(self) -> dict[str, Any]:
        """Load config from environment variables."""
        return {
            "security.enabled": os.getenv("SPARK_SECURITY_ENABLED", "true").lower() == "true",
            "security.log_file": os.getenv("SPARK_SECURITY_LOG_FILE", "security_log.json"),
            "security.file_watch_dirs": (
                os.getenv("SPARK_FILE_WATCH_DIRS", "core/,spark/,api/").split(",") if os.getenv("SPARK_FILE_WATCH_DIRS") else []
            ),
            "security.network_anomaly_threshold": int(
                os.getenv("SPARK_NETWORK_ANOMALY_THRESHOLD", "100")
            ),
            "security.network_anomaly_check_enabled": (
                os.getenv("SPARK_NETWORK_ANOMALY_CHECK", "false").lower() == "true"
            ),
            "security.firewall_auto_block": (
                os.getenv("SPARK_FIREWALL_AUTO_BLOCK", "false").lower() == "true"
            ),
        }

    def start(self) -> None:
        """Start the security daemon in background thread."""
        if not self.enabled:
            logger.info("Security daemon disabled via config")
            return
        
        if self.running:
            logger.warning("Security daemon already running")
            return
        
        self.running = True
        self.daemon_thread = threading.Thread(target=self._run_daemon, daemon=True)
        self.daemon_thread.start()
        logger.info("Security daemon started")

    def stop(self) -> None:
        """Stop the security daemon."""
        self.running = False
        if self.daemon_thread:
            self.daemon_thread.join(timeout=5)
        logger.info("Security daemon stopped")

    def _run_daemon(self) -> None:
        """Main daemon loop (runs in background thread)."""
        logger.info("Security daemon running")
        
        # Initialize file hashes
        self._scan_file_hashes()
        
        while self.running:
            try:
                # Run threat checks
                self._check_processes()
                self._check_file_integrity()
                self._check_network_anomalies()
                
                # Sleep before next scan
                time.sleep(int(os.getenv("SPARK_SECURITY_SCAN_INTERVAL", "30")))
            except Exception as e:
                logger.error(f"Security daemon error: {e}")

    def _check_processes(self) -> None:
        """Monitor for suspicious processes."""
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    proc_name = proc.info["name"].lower()
                    cmdline = (proc.info["cmdline"] or [])
                    cmdline_str = " ".join(str(c) for c in cmdline).lower()
                    
                    # Check for suspicious process names
                    for suspicious in self.suspicious_processes:
                        if suspicious.lower() in proc_name:
                            # Extra check: exclude legitimate system processes
                            if self._is_legitimate_process(proc.info, cmdline_str):
                                continue
                            
                            threat = {
                                "type": "suspicious_process",
                                "timestamp": datetime.now().isoformat(),
                                "pid": proc.info["pid"],
                                "process": proc_name,
                                "cmdline": cmdline_str[:200],
                                "severity": "high",
                            }
                            self._handle_threat(threat)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.debug(f"Process scanning error: {e}")

    def _check_file_integrity(self) -> None:
        """Monitor SPARK directories for file tampering."""
        try:
            workspace = os.getenv("SPARK_WORKSPACE_DIR", os.getcwd())
            
            for watch_dir in self.file_watch_dirs:
                watch_path = Path(workspace) / watch_dir.strip()
                if not watch_path.exists():
                    continue
                
                for file_path in watch_path.rglob("*.py"):
                    try:
                        # Skip __pycache__ and temporary files
                        if "__pycache__" in str(file_path) or file_path.suffix in {".pyc", ".pyo"}:
                            continue
                        
                        file_hash = self._compute_file_hash(file_path)
                        file_key = str(file_path)
                        
                        # Check if file was modified
                        if file_key in self.file_hashes:
                            if self.file_hashes[file_key] != file_hash:
                                threat = {
                                    "type": "file_tampering",
                                    "timestamp": datetime.now().isoformat(),
                                    "file": file_key,
                                    "old_hash": self.file_hashes[file_key],
                                    "new_hash": file_hash,
                                    "severity": "critical",
                                }
                                self._handle_threat(threat)
                        
                        # Update hash
                        self.file_hashes[file_key] = file_hash
                    except (OSError, IOError):
                        # File may have been deleted or is inaccessible
                        pass
                    except Exception as e:
                        logger.debug(f"File hash error for {file_path}: {e}")
        except Exception as e:
            logger.debug(f"File integrity scanning error: {e}")

    def _check_network_anomalies(self) -> None:
        """Monitor for unusual network connections."""
        if not self.network_anomaly_check_enabled:
            return
        
        try:
            current_connections = {}
            
            for conn in psutil.net_connections(kind="inet"):
                if conn.raddr:
                    remote_ip = conn.raddr[0]
                    current_connections[remote_ip] = current_connections.get(remote_ip, 0) + 1
            
            # Check for anomalies (rapid connections to same IP)
            for ip, count in current_connections.items():
                if count > self.network_anomaly_threshold:
                    old_count = self.connection_count.get(ip, 0)
                    if count > old_count * 1.5:  # 50% increase = anomaly
                        threat = {
                            "type": "network_anomaly",
                            "timestamp": datetime.now().isoformat(),
                            "remote_ip": ip,
                            "connection_count": count,
                            "threshold": self.network_anomaly_threshold,
                            "severity": "medium",
                        }
                        self._handle_threat(threat)
            
            self.connection_count = current_connections
        except Exception as e:
            logger.debug(f"Network anomaly scanning error: {e}")

    def _handle_threat(self, threat: dict[str, Any]) -> None:
        """Handle detected threat: alert, block, and log."""
        # Throttle repeated alerts (only alert once per threat type per resource per 60s)
        threat_key = f"{threat['type']}:{threat.get('process', threat.get('file', threat.get('remote_ip', 'unknown')))}"
        now = time.time()
        
        if threat_key in self.threat_throttle:
            last_alert_time = self.threat_throttle[threat_key]
            if now - last_alert_time < 60:  # Skip if alerted in last 60 seconds
                return
        
        self.threat_throttle[threat_key] = now
        
        logger.warning(f"SECURITY THREAT DETECTED: {threat['type']}")
        
        # Log threat
        self._log_threat(threat)
        
        # Alert user (minimal output to avoid spam)
        threat_summary = f"[{threat['type'].upper()}] {threat.get('process', threat.get('file', threat.get('remote_ip', 'unknown')))}"
        logger.warning(f"Security: {threat_summary}")
        
        # Auto-block if enabled
        if self.firewall_auto_block and threat.get("remote_ip"):
            self._block_ip(threat["remote_ip"])

    def _log_threat(self, threat: dict[str, Any]) -> None:
        """Log threat to security_log.json."""
        try:
            threats = []
            if self.threat_log_file.exists():
                with open(self.threat_log_file, "r") as f:
                    threats = json.load(f) or []
            
            threats.append(threat)
            
            with open(self.threat_log_file, "w") as f:
                json.dump(threats[-1000:], f, indent=2)  # Keep last 1000 threats
        except Exception as e:
            logger.error(f"Failed to log threat: {e}")

    def _block_ip(self, remote_ip: str) -> None:
        """Block IP via Windows Firewall."""
        if not self.firewall_auto_block:
            return
        
        try:
            # Construct firewall rule name
            rule_name = f"SPARK_BLOCK_{remote_ip.replace('.', '_')}"
            
            # Create inbound deny rule
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}",
                "dir=in",
                "action=block",
                f"remoteip={remote_ip}",
                "protocol=tcp",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            
            if result.returncode == 0:
                logger.info(f"Firewall blocked IP: {remote_ip}")
            else:
                logger.warning(f"Failed to block IP {remote_ip}: {result.stderr}")
        except Exception as e:
            logger.error(f"Firewall blocking error: {e}")

    def _scan_file_hashes(self) -> None:
        """Scan and hash all watched files."""
        try:
            workspace = os.getenv("SPARK_WORKSPACE_DIR", os.getcwd())
            
            for watch_dir in self.file_watch_dirs:
                watch_path = Path(workspace) / watch_dir
                if not watch_path.exists():
                    continue
                
                for file_path in watch_path.rglob("*.py"):
                    try:
                        file_hash = self._compute_file_hash(file_path)
                        self.file_hashes[str(file_path)] = file_hash
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"File hash scan error: {e}")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _is_legitimate_process(self, proc_info: dict, cmdline_str: str) -> bool:
        """Determine if process is legitimate (whitelist check).
        
        Whitelists development tools, system utilities, and known third-party security/service software.
        Prevents false positives on legitimate processes like VS Code terminals, AMD services, and 360 Security.
        """
        # Whitelist legitimate processes and system utilities
        whitelist_patterns = [
            # SPARK development
            "spark_cli",
            "spark_brain",
            
            # Python & Development
            "python.exe",
            "python.exe",
            "ollama",
            "pytest",
            "venv",
            "conda",
            "pip",
            "node.exe",
            "npm",
            "git",
            
            # VS Code (terminal, LSP, extensions)
            "code",
            "code.exe",
            "code-server",
            "electron",
            "vscode",
            "extensionhost",
            "debug.exe",
            ".vscode",
            
            # AMD CNxt Services & System
            "amd",
            "amdrsserv",  # AMD Remote Services daemon
            "cncmd",      # AMD CNxt Command tool
            "cnext",      # AMD CNxt service
            "amdaccelerator",
            
            # Windows System Processes (legitimately required)
            "svchost",
            "services.exe",
            "explorer.exe",
            "dwm.exe",
            "conhost.exe",
            "conhealth",
            "lsass.exe",
            "winlogon.exe",
            "spoolsv.exe",
            "searchindexer",
            "sppsvc",
            "cryptsvc",
            "trust installer",
            "rundll32.exe",
            "system",
            "smss.exe",
            "csrss.exe",
            "wininit.exe",
            "taskhostw.exe",
            "dllhost.exe",
            "svchost.exe",
            "WmiPrvSE.exe",
            
            # 360 Total Security & Antivirus
            "360",
            "360safe",
            "360tray",
            "360sd",
            "360defender",
            "deepscan",  # 360 deep scan engine
            "safemon",   # 360 safety monitor
            
            # Third-party Security & Utilities
            "avast",
            "kaspersky",
            "mcafee",
            "norton",
            "bitdefender",
            "sophos",
            "trend micro",
            "bullguard",
            "avg",
            
            # System Utilities & Services
            "backgroundtaskhost",
            "fontdrvhost",
            "useraccountcontrolhost",
            "setupapi",
            "installer",
            "windows defender",
            "msdefender",
            "wmiprvse",
            "devenv.exe",  # Visual Studio
            "cl.exe",      # C++ compiler
            "msbuild",
        ]
        
        for pattern in whitelist_patterns:
            if pattern.lower() in cmdline_str.lower():
                return True
        
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get daemon statistics."""
        return {
            "running": self.running,
            "enabled": self.enabled,
            "files_monitored": len(self.file_hashes),
            "active_connections": len(self.connection_count),
            "threat_log_file": str(self.threat_log_file),
        }
