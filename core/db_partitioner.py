"""
S.P.A.R.K Dynamic Database Partitioning Engine
Implements monthly SQLite partitioning for agent state histories, tool execution registries,
and runtime logs, ensuring database lookups remain efficient over long operation intervals.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("SPARK_DB_PARTITIONER")

class DatabasePartitioner:
    """Manages separate SQLite database clusters partitioned on a monthly time-series basis."""
    
    def __init__(self, partition_dir: str = "knowledge_base/partitions"):
        self.partition_dir = partition_dir
        os.makedirs(self.partition_dir, exist_ok=True)
        self._current_db_path: Optional[str] = None
        self._current_conn: Optional[sqlite3.Connection] = None
        
    def _get_active_partition_path(self) -> str:
        """Determines the current active database file based on the system year and month."""
        now = datetime.now()
        partition_name = f"spark_history_{now.year}_{now.month:02d}.db"
        return os.path.join(self.partition_dir, partition_name)

    def get_connection(self) -> sqlite3.Connection:
        """Establishes or returns the connection to the active monthly partition database."""
        active_path = self._get_active_partition_path()
        if self._current_db_path == active_path and self._current_conn:
            return self._current_conn
            
        # Close old connection if open
        if self._current_conn:
            self._current_conn.close()
            
        logger.info(f"Connecting to active SQLite partition database: {active_path}")
        self._current_db_path = active_path
        self._current_conn = sqlite3.connect(active_path, check_same_thread=False)
        self._create_schema(self._current_conn)
        return self._current_conn

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Creates the runtime state, logs, and tool execution registries tables."""
        cursor = conn.cursor()
        
        # 1. Agent State History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_state_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                agent_name TEXT,
                mode TEXT,
                state_data TEXT
            )
        """)
        
        # 2. Runtime Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runtime_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                log_level TEXT,
                event_type TEXT,
                message TEXT
            )
        """)
        
        # 3. Tool Execution Registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_execution_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                tool_name TEXT,
                arguments TEXT,
                result TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cluster_state_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                cluster_id TEXT,
                state_blob TEXT,
                metadata TEXT
            )
        """)
        conn.commit()

    def log_agent_state(self, agent_name: str, mode: str, state_data: str) -> None:
        """Persists agent state snapshot into the active partition."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO agent_state_history (agent_name, mode, state_data) VALUES (?, ?, ?)",
                (agent_name, mode, state_data)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log agent state: {e}")

    def log_runtime_event(self, log_level: str, event_type: str, message: str) -> None:
        """Persists compressed runtime event logs into the active partition."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO runtime_logs (log_level, event_type, message) VALUES (?, ?, ?)",
                (log_level, event_type, message)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log runtime event: {e}")

    def log_tool_execution(self, tool_name: str, arguments: str, result: str) -> None:
        """Registers a completed tool execution into the active partition."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tool_execution_registry (tool_name, arguments, result) VALUES (?, ?, ?)",
                (tool_name, arguments, result)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log tool execution: {e}")

    def log_conversation_history(self, conversation_id: str, role: str, content: str, metadata: str = "") -> None:
        """Persists conversation history into the active monthly partition."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (conversation_id, role, content, metadata) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, metadata),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log conversation history: {e}")

    def log_cluster_state(self, cluster_id: str, state_blob: str, metadata: str = "") -> None:
        """Persists cluster state snapshots into the active monthly partition."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO cluster_state_history (cluster_id, state_blob, metadata) VALUES (?, ?, ?)",
                (cluster_id, state_blob, metadata),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log cluster state: {e}")

    def query_cross_partitions(self, table_name: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Queries across all monthly partitions covered within the start and end dates (YYYY-MM)."""
        results: List[Dict[str, Any]] = []
        
        # Parse years/months from range bounds
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m")
            end_dt = datetime.strptime(end_date, "%Y-%m")
        except ValueError:
            logger.error("Dates must conform to YYYY-MM format")
            return []
            
        # Discover all DB files in partition directory
        for filename in os.listdir(self.partition_dir):
            if not filename.startswith("spark_history_") or not filename.endswith(".db"):
                continue
                
            # Parse year/month from filename
            parts = filename.replace("spark_history_", "").replace(".db", "").split("_")
            if len(parts) != 2:
                continue
                
            try:
                db_year, db_month = int(parts[0]), int(parts[1])
                db_dt = datetime(db_year, db_month, 1)
                
                # Check if this partition falls within the date range window
                if start_dt <= db_dt <= end_dt:
                    db_path = os.path.join(self.partition_dir, filename)
                    temp_conn = sqlite3.connect(db_path)
                    temp_conn.row_factory = sqlite3.Row
                    cursor = temp_conn.cursor()
                    
                    # Read records
                    cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp ASC")
                    for row in cursor.fetchall():
                        results.append(dict(row))
                    temp_conn.close()
            except Exception as e:
                logger.error(f"Failed reading partition database {filename}: {e}")
                
        return results

    def close(self) -> None:
        """Close active database connection."""
        if self._current_conn:
            self._current_conn.close()
            self._current_conn = None
            self._current_db_path = None
