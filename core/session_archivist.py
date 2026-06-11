"""S.P.A.R.K Session Context Archivist.

Manages persistent session context, conversational sliding-windows, and agent
state loading/restoration from SQLite database partitions.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, List, Optional
from core.db_partitioner import DatabasePartitioner

logger = logging.getLogger("SPARK_SESSION_ARCHIVIST")


class SessionContextArchivist:
    """Dynamic session context archivist tracking conversation and system state."""

    def __init__(self, partitioner: Optional[DatabasePartitioner] = None, token_threshold: int = 1500) -> None:
        self.partitioner = partitioner or DatabasePartitioner()
        self.token_threshold = token_threshold
        self._lock = threading.Lock()

    async def save_turn(
        self, conversation_id: str, role: str, content: str, state_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Persists a single chat turn and updates system states in a thread-safe manner."""
        with self._lock:
            try:
                metadata_str = json.dumps(state_metadata or {})
                self.partitioner.log_conversation_history(conversation_id, role, content, metadata_str)
                if state_metadata:
                    persona_state = state_metadata.get("active_persona") or state_metadata.get("persona")
                    agent_state_payload: Dict[str, Any] = {
                        "conversation_id": conversation_id,
                        "role": role,
                        "content": content,
                        "state_metadata": state_metadata,
                    }
                    if isinstance(persona_state, dict) and persona_state.get("name"):
                        agent_state_payload["active_persona"] = persona_state
                    self.partitioner.log_agent_state(
                        agent_name="SPARK_BRAIN",
                        mode="cli_repl",
                        state_data=json.dumps(agent_state_payload),
                    )
            except Exception as exc:
                logger.error("Failed to save session turn: %s", exc)

    async def get_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieves conversation history for a given conversation_id from partition databases."""
        try:
            conn = self.partitioner.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, metadata FROM conversation_history WHERE conversation_id = ? ORDER BY timestamp ASC",
                (conversation_id,),
            )
            rows = cursor.fetchall()
            history = []
            for r in rows:
                try:
                    meta = json.loads(r[2]) if r[2] else {}
                except Exception:
                    meta = {}
                history.append({"role": r[0], "content": r[1], "metadata": meta})
            return history
        except Exception as exc:
            logger.error("Failed to load conversation history: %s", exc)
            return []

    async def compress_history_if_needed(self, conversation_id: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compresses conversation history when token length (approximated by word count) exceeds threshold."""
        total_words = sum(len(str(m.get("content", "")).split()) for m in messages)
        if total_words < self.token_threshold:
            return messages

        logger.info("Session history approaching token limit. Compressing context...")

        system_prompt = next((m for m in messages if m.get("role") == "system"), None)
        chat_msgs = [m for m in messages if m.get("role") in ("user", "assistant")]

        if len(chat_msgs) <= 2:
            return messages

        to_compress = chat_msgs[:-2]
        keep = chat_msgs[-2:]

        summary_prompt = "Summarize the key facts, tasks, and state values from this conversation history concisely:\n"
        for m in to_compress:
            summary_prompt += f"{str(m.get('role', '')).upper()}: {m.get('content', '')}\n"

        summary = "[Context Compressed due to token limit]"
        try:
            from core.spark_brain import _local_chat_completion, client, _chat_completion
            if client is not None:
                resp = _chat_completion([{"role": "user", "content": summary_prompt}], allow_tools=False)
                summary = (resp.choices[0].message.content or "").strip()
            else:
                summary = await _local_chat_completion([{"role": "user", "content": summary_prompt}])
        except Exception as exc:
            logger.error("Failed to compress history: %s", exc)

        compressed_msg = {
            "role": "system",
            "content": f"Summary of earlier conversation: {summary}",
        }

        new_messages = []
        if system_prompt:
            new_messages.append(system_prompt)
        new_messages.append(compressed_msg)
        new_messages.extend(keep)
        return new_messages

    async def load_last_calibration_states(self) -> Dict[str, Any]:
        """Inherits prior entity states, tool parameter memories, and hardware calibration results."""
        try:
            snapshots = await self.load_historical_calibration_snapshots(limit=1)
            if snapshots:
                latest_state = snapshots[0].get("state")
                if isinstance(latest_state, dict):
                    if isinstance(latest_state.get("state_metadata"), dict):
                        return latest_state["state_metadata"]
                    return latest_state
        except Exception as exc:
            logger.error("Failed to load calibration states: %s", exc)
        return {}

    async def load_last_persona(self) -> Dict[str, Any]:
        """Loads the most recently persisted persona state from the monthly partitions."""
        try:
            snapshots = await self.load_historical_calibration_snapshots(limit=10)
            for snapshot in snapshots:
                state = snapshot.get("state") if isinstance(snapshot, dict) else {}
                if not isinstance(state, dict):
                    continue
                persona = state.get("active_persona") or state.get("persona")
                if not isinstance(persona, dict):
                    state_metadata = state.get("state_metadata")
                    if isinstance(state_metadata, dict):
                        persona = state_metadata.get("active_persona") or state_metadata.get("persona")
                if isinstance(persona, dict) and persona.get("name"):
                    return persona
        except Exception as exc:
            logger.error("Failed to load last persona: %s", exc)
        return {}

    async def load_historical_calibration_snapshots(self, limit: int = 8) -> List[Dict[str, Any]]:
        """Loads recent calibration snapshots from the monthly SQLite partitions."""
        try:
            rows = self.partitioner.query_cross_partitions("agent_state_history", "2000-01", "2999-12")
        except Exception as exc:
            logger.error("Failed to query historical calibration snapshots: %s", exc)
            return []

        snapshots: List[Dict[str, Any]] = []
        for row in sorted(rows, key=lambda item: str(item.get("timestamp", "")), reverse=True):
            raw_state = row.get("state_data", "")
            try:
                state = json.loads(raw_state) if raw_state else {}
            except Exception:
                state = {}
            if not isinstance(state, dict):
                continue
            snapshots.append({
                "timestamp": row.get("timestamp", ""),
                "state": state,
                "agent_name": row.get("agent_name", "SPARK_BRAIN"),
                "mode": row.get("mode", "cli_repl"),
            })
            if len(snapshots) >= max(1, int(limit)):
                break
        return snapshots
