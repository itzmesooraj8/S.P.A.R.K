from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import re
import socket
import subprocess
import time
from datetime import datetime
from typing import Any

import httpx
import requests

from core.orchestrator.action_decomposer import decompose_explicit_actions


log = logging.getLogger("spark.llm")


class SparkLLM:
    def __init__(self, config: dict[str, Any], memory, tools):
        self.config = config if isinstance(config, dict) else {}
        self.memory = memory
        self.tools = tools
        self._ollama_last_probe = 0.0
        self._ollama_probe_interval = 5.0

    def execute(self, task: dict[str, Any] | str) -> dict[str, Any]:
        """Execute task with full tool support and security checks."""
        if isinstance(task, str):
            task = {"prompt": task}
        
        prompt = task.get("prompt", "").strip()
        include_tools = task.get("include_tools", True)
        
        if not prompt:
            return {"reply": "", "tool_used": None, "tool_result": None}

        if not include_tools or not self._should_use_tools(prompt):
            reply = self._complete(prompt)
            return {"reply": reply, "tool_used": None, "tool_result": None}
        
        # Get context from memory for better responses
        context = self._build_context(prompt)
        enhanced_prompt = self._enhance_prompt(prompt, context)
        
        # Try to execute through spark_brain (which handles tool calling)
        try:
            result = self._execute_with_tools(prompt, include_tools=include_tools)
            # If tool-calling produced an error-like reply, retry without tools
            try:
                reply_text = str(result.get("reply", "") or "").lower()
                if ("tool" in reply_text and ("failed" in reply_text or "error" in reply_text)) and include_tools:
                    log.info("Tool call failed, retrying without tools")
                    fallback = {"reply": self._complete(enhanced_prompt), "tool_used": None, "tool_result": None}
                    return fallback
            except Exception:
                pass
            return result
        except Exception as exc:
            log.warning(f"Tool execution failed, falling back to simple chat: {exc}")
            # Fall back to simple completion
            reply = self._complete(enhanced_prompt)
            return {"reply": reply, "tool_used": None, "tool_result": None}

    def _build_context(self, prompt: str) -> dict[str, Any]:
        """Build context from memory for better understanding."""
        try:
            recent = self.memory.recent_interactions(5)
            if not recent:
                return {}
            return {
                "recent_count": len(recent),
                "recent_summaries": [
                    f"Q: {r.get('prompt', '')[:60]}... → A: {str(r.get('result', ''))[:60]}..."
                    for r in recent[-2:]
                ],
            }
        except Exception as e:
            log.debug(f"Context building failed: {e}")
            return {}

    def _should_use_tools(self, prompt: str) -> bool:
        text = (prompt or "").strip().lower()
        if not text:
            return False
        return bool(
            re.search(
                r"\b(open|launch|search|weather|news|system|clipboard|network|screen|read|click|play|pause|volume|map|remind|time|date|clock|memory|remember|recall|history|current)\b",
                text,
            )
        )

    def _enhance_prompt(self, prompt: str, context: dict[str, Any]) -> str:
        """Enhance prompt with memory context."""
        if not context.get("recent_summaries"):
            return prompt
        context_text = "\n".join([f"• {s}" for s in context["recent_summaries"]])
        return f"Recent interactions:\n{context_text}\n\nCurrent query: {prompt}"

    def _execute_with_tools(self, prompt: str, include_tools: bool = True) -> dict[str, Any]:
        """Execute through spark_brain which handles Groq tool calling.

        Runs the blocking `spark_brain.handle` in a worker thread with a timeout to
        avoid hanging the CLI. Timeout is longer (60s) to allow local CLI completion.
        """
        try:
            # Import handler lazily to avoid heavy imports at module load
            from core.spark_brain import handle as spark_brain_handle

            # Use longer timeout (60s) to allow local CLI to complete
            timeout = int(self._llm_config().get("call_timeout_seconds", 60) or 60)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(asyncio.run, spark_brain_handle(prompt, []))
                try:
                    result = fut.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    fut.cancel()
                    log.warning("spark_brain timed out after %s seconds", timeout)
                    raise TimeoutError(f"LLM/tool call timed out after {timeout}s")

            if isinstance(result, dict):
                return {
                    "reply": str(result.get("reply", "") or "").strip(),
                    "tool_used": result.get("tool_used"),
                    "tool_result": result.get("tool_result"),
                }

            return {"reply": str(result or "").strip(), "tool_used": None, "tool_result": None}

        except Exception as exc:
            log.warning("spark_brain execution failed: %s", exc)
            # Fallback to simple completion
            reply = self._complete(prompt)
            return {"reply": reply, "tool_used": None, "tool_result": None}

    def reflect(self, result: dict[str, Any], recent_history: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        recent_text = json.dumps(self._compact_history(recent_history or [], limit=6), ensure_ascii=False)
        prompt = (
            "Review the latest outcome and return a JSON array of next tasks. "
            "Each item must be an object with prompt, source, and optional due_at. "
            f"Outcome: {json.dumps(result, ensure_ascii=False)}\nHistory: {recent_text}"
        )
        try:
            response = self._complete(prompt, force_json=True)
            return self._extract_tasks(response)
        except Exception:
            return []

    def rewrite_system_prompt(self, recent_history: list[dict[str, Any]]) -> str:
        compact_history = self._compact_history(recent_history, limit=8)
        prompt = (
            "Rewrite SPARK's system prompt based on the last interactions. "
            "Preserve the user's preference for dense, structured, no-fluff responses. "
            "Return only the new prompt text.\n"
            f"History: {json.dumps(compact_history, ensure_ascii=False)}"
        )
        try:
            return self._complete(prompt)
        except Exception:
            return ""

    def _extract_tasks(self, text: str) -> list[dict[str, Any]]:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                tasks: list[dict[str, Any]] = []
                for item in parsed:
                    if isinstance(item, dict) and item.get("prompt"):
                        tasks.append(item)
                return tasks
        except Exception:
            return []
        return []

    def _compact_history(self, history: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        compacted: list[dict[str, Any]] = []
        for entry in history[-limit:]:
            if not isinstance(entry, dict):
                continue
            compacted.append({
                "task": str(entry.get("task", ""))[:160],
                "result": str(entry.get("result", ""))[:240],
            })
        return compacted

    def _llm_config(self) -> dict[str, Any]:
        return self.config.get("llm", {}) if isinstance(self.config, dict) else {}

    def _backend(self) -> str:
        return str(self._llm_config().get("backend", "ollama") or "ollama").strip().lower()

    def _ollama_host(self) -> str:
        return str(self._llm_config().get("ollama_host", "http://localhost:11434") or "http://localhost:11434").rstrip("/")

    def _ollama_model(self) -> str:
        return str(self._llm_config().get("ollama_model", "gemma4") or "gemma4").strip()

    def _candidate_ollama_models(self) -> list[str]:
        configured = self._ollama_model()
        env_model = str(os.getenv("OLLAMA_MODEL", "") or "").strip()
        candidates = [configured, env_model]
        seen: set[str] = set()
        result: list[str] = []
        for model in candidates:
            if model and model not in seen:
                seen.add(model)
                result.append(model)

        try:
            response = requests.get(f"{self._ollama_host()}/api/tags", timeout=3)
            response.raise_for_status()
            data = response.json()
            models = data.get("models", []) if isinstance(data, dict) else []
            if isinstance(models, list):
                sorted_models = sorted(
                    [model for model in models if isinstance(model, dict)],
                    key=lambda model: float(model.get("size", 0) or 0),
                )
                for model in sorted_models:
                    model_name = str(model.get("name") or model.get("model") or "").strip()
                    if model_name and model_name not in seen:
                        seen.add(model_name)
                        result.append(model_name)
        except Exception:
            pass

        return result

    def _ollama_prompt_from_messages(self, messages: list[dict[str, str]]) -> str:
        parts: list[str] = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "user") or "user").strip().lower()
            content = str(message.get("content", "") or "").strip()
            if not content:
                continue
            if role == "system":
                parts.append(f"[SYSTEM]\n{content}")
            elif role == "assistant":
                parts.append(f"[ASSISTANT]\n{content}")
            else:
                parts.append(f"[USER]\n{content}")
        return "\n\n".join(parts)

    def _build_messages(self, prompt: str, force_json: bool = False) -> list[dict[str, str]]:
        system_prompt = self.memory.load_system_prompt().strip()
        if force_json:
            system_prompt = f"{system_prompt}\nReturn only valid JSON."
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

    def _complete(self, prompt: str, force_json: bool = False) -> str:
        """Fallback completion without tools."""
        normalized = (prompt or "").strip().lower()
        if normalized in {"hi", "hello", "hey", "hii", "yo", "good morning", "good afternoon", "good evening"}:
            return "Hello! How can I help you today? 😊"

        messages = self._build_messages(prompt, force_json=force_json)
        try:
            # Try HTTP API first only when Ollama is actually reachable.
            self._ensure_ollama_available()
            if self._is_ollama_reachable():
                return self._chat_ollama_http(messages)
        except Exception as exc:
            log.debug(f"Ollama HTTP failed: {exc}")

        if self._backend() in {"groq", "cloud"}:
            try:
                from core.spark_brain import handle as spark_brain_handle

                response = self._run_async(spark_brain_handle(prompt, []))
                if isinstance(response, dict):
                    return str(response.get("reply", "") or "").strip()
                return str(response).strip()
            except Exception as exc:
                log.warning(f"Fallback completion failed: {exc}")

        local_fallback = self._local_action_fallback(prompt)
        if local_fallback:
            return local_fallback

        return "I am having trouble reaching the language model right now, but I am still running locally."

    def _local_action_fallback(self, prompt: str) -> str:
        """Best-effort local execution for common requests when both model backends are down."""
        text = (prompt or "").strip()
        if not text:
            return ""
        results: list[str] = []

        actions = decompose_explicit_actions(text)
        if not actions and any(word in text.lower() for word in ["time", "date", "clock"]):
            actions = [{"tool": "get_time", "args": {}}]

        for action in actions:
            tool_name = str(action.get("tool", ""))
            args = action.get("args", {}) if isinstance(action.get("args", {}), dict) else {}

            if tool_name == "get_weather":
                location = str(args.get("location") or "Palakkad")
                try:
                    from tools.weather import get_weather

                    weather = get_weather(location)
                    results.append(self._format_local_result(f"Weather for {location}", weather))
                except Exception as exc:
                    results.append(f"Weather lookup failed for {location}: {exc}")
                continue

            if tool_name == "open_app":
                target = str(args.get("app") or "").strip()
                if target:
                    try:
                        from tools.browser import open_app

                        results.append(open_app(target))
                    except Exception as exc:
                        results.append(f"Open request failed for {target}: {exc}")
                continue

            if tool_name == "open_url":
                url = str(args.get("url") or "")
                query = str(args.get("query") or "")
                try:
                    from tools.browser import open_url

                    results.append(open_url(url, query))
                except Exception as exc:
                    results.append(f"Open request failed: {exc}")
                continue

            if tool_name == "web_search":
                query = str(args.get("query") or "")
                if query:
                    try:
                        from tools.search import web_search

                        results.append(web_search(query))
                    except Exception as exc:
                        results.append(f"Search failed for {query}: {exc}")
                continue

            if tool_name == "get_time":
                results.append(datetime.now().strftime("The current time is %I:%M %p on %A, %B %d, %Y."))

        return "\n".join(result for result in results if str(result).strip())

    def _extract_open_target(self, text: str) -> str:
        match = re.search(r"\b(?:open|launch|start|run)\b\s+(?:the\s+|my\s+|app\s+|application\s+|program\s+)?(.+)$", text, flags=re.IGNORECASE)
        target = match.group(1) if match else text
        target = re.split(r"\b(?:and then|then|and|also|plus)\b|,", target, maxsplit=1, flags=re.IGNORECASE)[0]
        return re.sub(r"\b(?:please|now|for me|for us|on my pc|on my computer)\b", "", target, flags=re.IGNORECASE).strip(" .")

    def _extract_weather_location(self, text: str) -> str:
        lowered = text.lower()
        match = re.search(r"\b(?:in|for|at)\s+(.+)$", lowered, flags=re.IGNORECASE)
        candidate = match.group(1) if match and match.group(1) else lowered
        candidate = re.split(r"\b(?:and then|then|and|also|plus)\b|,", candidate, maxsplit=1, flags=re.IGNORECASE)[0]
        candidate = re.sub(r"\b(?:weather|forecast|temperature|what is|what's|is it|like|today|now|currently|the)\b", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"^\s*(?:in|for|at)\s+", "", candidate, flags=re.IGNORECASE)
        candidate = candidate.replace("india", "India")
        cleaned = candidate.strip(" .")
        return cleaned or "Palakkad"

    def _extract_search_query(self, text: str) -> str:
        match = re.search(r"\b(?:search|look up|lookup|find|research)\b\s*(.*)$", text, flags=re.IGNORECASE)
        query = match.group(1) if match else text
        query = re.split(r"\b(?:and then|then|and|also|plus)\b|,", query, maxsplit=1, flags=re.IGNORECASE)[0]
        return re.sub(r"\b(?:please|for me|for us|now)\b", "", query, flags=re.IGNORECASE).strip(" .")

    def _format_local_result(self, label: str, value: Any) -> str:
        if isinstance(value, dict):
            if value.get("error"):
                return f"{label}: {value['error']}"
            parts = [f"{key}={val}" for key, val in value.items()]
            return f"{label}: " + ", ".join(parts)
        return f"{label}: {value}"

    def _chat_ollama_http(self, messages: list[dict[str, str]]) -> str:
        """Call Ollama via persistent HTTP API (no subprocess spawning).
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Returns:
            Response text from Ollama
            
        Raises:
            Exception if all models fail or Ollama is unreachable
        """
        timeout = float(self._llm_config().get("ollama_http_timeout_seconds", 18) or 18)
        primary_timeout = float(os.getenv("SPARK_OLLAMA_PRIMARY_TIMEOUT_SECONDS", "8"))
        prompt = self._ollama_prompt_from_messages(messages)
        
        for model in self._candidate_ollama_models():
            candidate_timeout = primary_timeout if model == self._ollama_model() else min(timeout, 25.0)
            chat_unsupported = False

            try:
                response = requests.post(
                    f"{self._ollama_host()}/api/chat",
                    json={"model": model, "messages": messages, "stream": False},
                    timeout=candidate_timeout,
                )
                response.raise_for_status()

                data = response.json()
                if isinstance(data, dict):
                    if "message" in data:
                        return str(data["message"].get("content", "")).strip()
                    if "response" in data:
                        return str(data["response"]).strip()

                return str(data).strip() if data else ""
            except requests.exceptions.Timeout:
                log.warning(f"Ollama HTTP timeout for model {model} after {candidate_timeout}s")
                continue
            except requests.exceptions.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                if status == 400:
                    chat_unsupported = True
                else:
                    log.debug(f"Ollama HTTP error for model {model}: {exc}")
                    continue
            except Exception as exc:
                log.debug(f"Ollama HTTP error for model {model}: {exc}")
                continue

            if chat_unsupported:
                try:
                    response = requests.post(
                        f"{self._ollama_host()}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": False},
                        timeout=candidate_timeout,
                    )
                    response.raise_for_status()

                    data = response.json()
                    if isinstance(data, dict):
                        if "response" in data:
                            return str(data["response"]).strip()
                        if "message" in data:
                            return str(data["message"].get("content", "")).strip()

                    return str(data).strip() if data else ""
                except requests.exceptions.Timeout:
                    log.warning(f"Ollama generate timeout for model {model} after {candidate_timeout}s")
                    continue
                except Exception as exc:
                    log.debug(f"Ollama generate error for model {model}: {exc}")
                    continue
        
        raise RuntimeError(f"All Ollama models failed. Candidates: {self._candidate_ollama_models()}")

    async def _chat_ollama(self, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            prompt = "\n".join(m.get("content", "") for m in messages if m.get("content"))
            last_error: Exception | None = None

            for model in self._candidate_ollama_models():
                try:
                    response = await client.post(
                        f"{self._ollama_host()}/api/chat",
                        json={"model": model, "messages": messages, "stream": False},
                    )
                    if response.status_code == 404:
                        self._ensure_ollama_available(force_start=True)
                        response = await client.post(
                            f"{self._ollama_host()}/api/generate",
                            json={"model": model, "prompt": prompt, "stream": False},
                        )
                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data, dict) and "response" in data:
                        return str(data.get("response", "") or "").strip()
                    message = data.get("message", {}) if isinstance(data, dict) else {}
                    return str(message.get("content", "") or "").strip()
                except Exception as exc:
                    last_error = exc
                    continue

            if last_error:
                raise last_error
            raise RuntimeError("Ollama did not return a response")

    def _is_ollama_reachable(self) -> bool:
        host = self._ollama_host()
        try:
            from urllib.parse import urlparse

            parsed = urlparse(host)
            if not parsed.hostname or not parsed.port:
                return False
            with socket.create_connection((parsed.hostname, parsed.port), timeout=0.6):
                return True
        except Exception:
            return False

    def _ensure_ollama_available(self, force_start: bool = False) -> None:
        now = time.time()
        if not force_start and now - self._ollama_last_probe < self._ollama_probe_interval:
            return
        self._ollama_last_probe = now

        if self._is_ollama_reachable():
            return

        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            time.sleep(0.5)
        except Exception as exc:
            log.debug("Unable to auto-start Ollama service: %s", exc)

    def _run_async(self, coroutine):
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()
