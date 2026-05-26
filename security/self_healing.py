"""
S.P.A.R.K Self-Healing Defensive Code Pipeline
Computes SHA-256 cryptographic signatures of essential manifests/config blocks,
monitoring and instantly restoring them from a read-only backup directory when altered.
"""

import os
import shutil
import hashlib
import logging
import threading
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger("SPARK_SELF_HEALING")

class SelfHealingDaemon:
    """Monitors config files and recovers them from a read-only backup directory if tampered with."""
    
    def __init__(
        self,
        monitored_files: Optional[List[str]] = None,
        backup_dir: str = "config/backups",
        workspace_dir: Optional[str] = None,
        check_interval_seconds: float = 2.0
    ):
        self.workspace_dir = workspace_dir or os.getcwd()
        self.backup_dir = os.path.join(self.workspace_dir, backup_dir)
        self.check_interval_seconds = check_interval_seconds
        
        # Default files to protect
        self.monitored_files = monitored_files or ["config.json", ".env"]
        self.running = False
        self.watch_thread: Optional[threading.Thread] = None
        
        # Track initial expected SHA-256 signatures
        self.expected_signatures: Dict[str, str] = {}
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        self._initialize_backups()

    def _compute_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _initialize_backups(self) -> None:
        """Cache initial copies of monitored files to the read-only backup directory."""
        for rel_path in self.monitored_files:
            source_path = os.path.join(self.workspace_dir, rel_path)
            backup_path = os.path.join(self.backup_dir, rel_path)
            
            # If the source exists but backup doesn't, create backup
            if os.path.exists(source_path):
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                if not os.path.exists(backup_path):
                    shutil.copy2(source_path, backup_path)
                    logger.info(f"Initialized backup file reference: {rel_path}")
                
                # Cache signature
                self.expected_signatures[rel_path] = self._compute_hash(backup_path)
            elif os.path.exists(backup_path):
                # If backup exists but source is missing, restore source
                self._restore_file(rel_path)
                self.expected_signatures[rel_path] = self._compute_hash(backup_path)

    def _restore_file(self, rel_path: str) -> None:
        """Restore file from backup store to the active workspace."""
        source_path = os.path.join(self.workspace_dir, rel_path)
        backup_path = os.path.join(self.backup_dir, rel_path)
        
        logger.warning(f"SELF-HEALING TRIGGERED: Restoring corrupted/deleted file '{rel_path}' from backup.")
        try:
            os.makedirs(os.path.dirname(source_path), exist_ok=True)
            shutil.copy2(backup_path, source_path)
            logger.info(f"Self-Healing: Successfully restored '{rel_path}' to clean state.")
        except Exception as e:
            logger.error(f"Failed to restore file '{rel_path}': {e}")

    def scan_and_heal(self) -> List[str]:
        """Scans watched configuration manifests, restoring any altered or deleted entries."""
        healed_files = []
        for rel_path in self.monitored_files:
            source_path = os.path.join(self.workspace_dir, rel_path)
            backup_path = os.path.join(self.backup_dir, rel_path)
            
            # Case 1: File has been deleted
            if not os.path.exists(source_path):
                logger.warning(f"Self-healing: Monitored file '{rel_path}' missing.")
                self._restore_file(rel_path)
                healed_files.append(rel_path)
                continue
                
            # Case 2: File exists but hash has diverged
            try:
                current_hash = self._compute_hash(source_path)
                expected_hash = self.expected_signatures.get(rel_path)
                
                if expected_hash and current_hash != expected_hash:
                    logger.warning(f"Self-healing: Hash discrepancy detected for '{rel_path}'. Expected: {expected_hash}, Got: {current_hash}")
                    self._restore_file(rel_path)
                    healed_files.append(rel_path)
            except Exception as e:
                logger.error(f"Failed scanning file '{rel_path}': {e}")
                
        return healed_files

    def start(self) -> None:
        """Start the daemon thread checking file integrity."""
        if self.running:
            return
        self.running = True
        self.watch_thread = threading.Thread(target=self._healing_loop, daemon=True)
        self.watch_thread.start()
        logger.info("Self-healing file system daemon started.")

    def stop(self) -> None:
        """Stop the daemon thread checking file integrity."""
        self.running = False
        if self.watch_thread:
            self.watch_thread.join(timeout=2.0)
        logger.info("Self-healing file system daemon stopped.")

    def _healing_loop(self) -> None:
        """Continuous execution loop analyzing cryptographic signatures."""
        while self.running:
            try:
                self.scan_and_heal()
                time.sleep(self.check_interval_seconds)
            except Exception as e:
                logger.error(f"Error in self-healing watch loop: {e}")
                time.sleep(self.check_interval_seconds)
