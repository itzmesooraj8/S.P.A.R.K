"""
Token counter for Groq API usage tracking and daily budgeting.
Automatically switches to Ollama-only mode at configurable threshold (default: 80k).
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TokenCounter:
    """Track daily Groq token usage and auto-switch to local model at threshold."""

    def __init__(self, log_file: str | None = None):
        """
        Initialize token counter.
        
        Args:
            log_file: Path to token_log.json (from config or default)
        """
        if log_file:
            self.log_file = Path(log_file)
        else:
            workspace = os.getenv("SPARK_WORKSPACE_DIR", os.getcwd())
            self.log_file = Path(workspace) / "spark_dev_memory" / "token_log.json"
        
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.daily_limit = int(os.getenv("GROQ_DAILY_TOKEN_LIMIT", "80000"))
        self.data = self._load_log()

    def _load_log(self) -> dict:
        """Load token log from disk."""
        try:
            if self.log_file.exists():
                with open(self.log_file, "r") as f:
                    return json.load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load token log: {e}")
        return {}

    def _save_log(self) -> None:
        """Persist token log to disk."""
        try:
            with open(self.log_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save token log: {e}")

    def get_today_key(self) -> str:
        """Get today's date key (YYYY-MM-DD)."""
        return datetime.now().strftime("%Y-%m-%d")

    def log_usage(self, tokens_used: int, model: str = "llama-3.3-70b-versatile") -> None:
        """
        Log token usage for a Groq API call.
        
        Args:
            tokens_used: Number of tokens used in this call
            model: Groq model used (for tracking model-specific usage)
        """
        today = self.get_today_key()
        if today not in self.data:
            self.data[today] = {"total": 0, "calls": 0, "models": {}}
        
        self.data[today]["total"] += tokens_used
        self.data[today]["calls"] += 1
        
        if model not in self.data[today]["models"]:
            self.data[today]["models"][model] = 0
        self.data[today]["models"][model] += tokens_used
        
        self._save_log()
        logger.debug(f"Logged {tokens_used} tokens for {model}. Daily total: {self.get_daily_usage()}")

    def get_daily_usage(self) -> int:
        """Get total tokens used today."""
        today = self.get_today_key()
        return self.data.get(today, {}).get("total", 0)

    def get_remaining_budget(self) -> int:
        """Get remaining token budget for today."""
        return max(0, self.daily_limit - self.get_daily_usage())

    def get_remaining_today(self) -> int:
        """Get remaining token budget for today (alias for get_remaining_budget).
        
        Preferred method name for session-start checks to ensure clear intent.
        """
        return self.get_remaining_budget()

    def should_skip_groq(self) -> bool:
        """Check if daily token limit reached; if so, skip Groq and use Ollama only."""
        daily_usage = self.get_daily_usage()
        if daily_usage >= self.daily_limit:
            logger.warning(
                f"Daily Groq token limit reached ({daily_usage}/{self.daily_limit}). "
                "Switching to Ollama-only mode."
            )
            return True
        return False

    def get_stats(self) -> dict:
        """Get detailed stats for today."""
        today = self.get_today_key()
        today_data = self.data.get(today, {"total": 0, "calls": 0, "models": {}})
        return {
            "date": today,
            "total_tokens": today_data["total"],
            "total_calls": today_data["calls"],
            "remaining_budget": self.get_remaining_budget(),
            "models": today_data["models"],
            "should_skip_groq": self.should_skip_groq(),
        }

    def reset_daily_log(self) -> None:
        """Reset today's log (useful for testing)."""
        today = self.get_today_key()
        if today in self.data:
            del self.data[today]
        self._save_log()
