"""Vision Understander — Uses Vision LLMs to understand what's on screen.

This is what makes SPARK actually UNDERSTAND what the user is doing.

Not just "VS Code opened" but:
- User is debugging Python code in main.py
- User is reading FastAPI documentation about routers
- User is reviewing a pull request for authentication
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.vision.understand")


class VisionUnderstander:
    """
    Understands screen content using Vision LLMs.

    Backends: Local Ollama Vision → API Vision (GPT-4V, Gemini, Qwen-VL)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._backend = self._config.get("vision_backend", "ollama")
        self._model = self._config.get("vision_model", "llava")
        self._api_key = self._config.get("vision_api_key", "")

    def understand(self, image_path: str, question: str = "Describe what the user is doing on screen in detail.") -> dict[str, Any]:
        """Analyze a screenshot and answer a question about it."""
        if self._backend == "ollama":
            return self._understand_ollama(image_path, question)
        elif self._backend == "api":
            return self._understand_api(image_path, question)
        return {"analysis": "", "activity": "unknown", "confidence": 0.0}

    def analyze_activity(self, image_path: str) -> dict[str, Any]:
        """Determine what the user is doing."""
        result = self.understand(image_path, "What is the user doing? Identify the application, the task, and any specific context. Be precise.")
        return {
            "activity": self._extract_activity(result.get("analysis", "")),
            "application": self._extract_application(result.get("analysis", "")),
            "task": self._extract_task(result.get("analysis", "")),
            "details": result.get("analysis", ""),
            "confidence": result.get("confidence", 0.0),
        }

    def detect_code(self, image_path: str) -> dict[str, Any]:
        """Detect if code is visible and what language/purpose."""
        result = self.understand(image_path, "Is there code visible? What language? What does it do? Identify any errors or issues.")
        return {
            "has_code": "code" in result.get("analysis", "").lower(),
            "details": result.get("analysis", ""),
        }

    def _understand_ollama(self, image_path: str, question: str) -> dict[str, Any]:
        try:
            import httpx
            import base64

            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()

            response = httpx.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "user",
                            "content": question,
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
            return {"analysis": content, "confidence": 0.8, "backend": "ollama"}
        except Exception as exc:
            logger.error("Ollama vision failed: %s", exc)
            return {"analysis": "", "confidence": 0.0, "error": str(exc)}

    def _understand_api(self, image_path: str, question: str) -> dict[str, Any]:
        try:
            import httpx

            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()

            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": question},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                            ],
                        }
                    ],
                    "max_tokens": 500,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return {"analysis": content, "confidence": 0.9, "backend": "api"}
        except Exception as exc:
            logger.error("API vision failed: %s", exc)
            return {"analysis": "", "confidence": 0.0, "error": str(exc)}

    def _extract_activity(self, analysis: str) -> str:
        analysis_lower = analysis.lower()
        if any(w in analysis_lower for w in ["code", "programming", "debugging", "coding"]):
            return "programming"
        if any(w in analysis_lower for w in ["browser", "web page", "website", "reading"]):
            return "browsing"
        if any(w in analysis_lower for w in ["terminal", "command", "shell", "console"]):
            return "terminal"
        if any(w in analysis_lower for w in ["email", "inbox", "message"]):
            return "communication"
        if any(w in analysis_lower for w in ["document", "writing", "editing"]):
            return "document_editing"
        return "general"

    def _extract_application(self, analysis: str) -> str:
        apps = ["vs code", "chrome", "firefox", "terminal", "discord", "slack", "notepad", "word", "excel"]
        for app in apps:
            if app in analysis.lower():
                return app
        return "unknown"

    def _extract_task(self, analysis: str) -> str:
        sentences = analysis.split(".")
        if sentences:
            return sentences[0].strip()
        return analysis[:100]
