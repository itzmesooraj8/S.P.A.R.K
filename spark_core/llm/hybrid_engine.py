import asyncio
import os
import pathlib
import httpx
from typing import Optional

# Model can be overridden via env var (loaded from .env by run_server.py)
_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
_GEMINI_FALLBACK_MODEL = "gemini-2.0-flash"


def _load_google_key() -> str:
    """Load Google Gemini API key from env var or secrets.yaml."""
    val = os.getenv("GOOGLE_GEMINI_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    if not val:
        try:
            import yaml
            p = pathlib.Path(__file__).parent.parent.parent / "config" / "secrets.yaml"
            if p.exists():
                data = yaml.safe_load(p.read_text()) or {}
                val = data.get("keys", {}).get("google_gemini", "")
        except Exception:
            pass
    return val or ""


class HybridLLM:
    """
    Hybrid LLM engine to call Local Ollama as primary.
    If it fails or input is too large, fallback to Cloud (Gemini).
    """
    def __init__(self, model: str = _DEFAULT_MODEL, ollama_host: str = "http://127.0.0.1:11434"):
        self.model = model
        self.host = ollama_host
        self._google_api_key = _load_google_key()
        print(f"🧬 [LLM] Engine Booting. Primary: Local ({model}) | Fallback: Gemini ({_GEMINI_FALLBACK_MODEL})")

    async def is_local_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                await client.get(self.host)
            return True
        except:
            return False

    async def generate(self, system_prompt: str, user_text: str):
        """Call Local Model via Async HTTP. Uses streaming for speed."""
        import json
        
        # Determine if we should offload to cloud
        if not await self.is_local_available():
            print(f"⚠️ [LLM] Local engine offline at {self.host}. Gracefully falling back to Cloud.")
            yield await self.call_cloud_fallback(system_prompt, user_text)
            return

        # Example: if len(user_text) > 8000:
        #    yield await self.call_cloud_fallback(system_prompt, user_text)
        #    return

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "stream": True # Set to true to yield token stream.
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                print(f"🧠 [LLM] Calling local Ollama stream: {self.model} ...")
                async with client.stream("POST", f"{self.host}/api/chat", json=payload, timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    token = data.get("message", {}).get("content", "")
                                    if token:
                                        yield token
                                except json.JSONDecodeError:
                                    continue
                    else:
                        print(f"⚠️ [LLM] Local engine error: {response.status_code}")
                        yield await self.call_cloud_fallback(system_prompt, user_text)

        except Exception as e:
            print(f"⚠️ [LLM] Local engine stream error: {repr(e)}. Falling back to Cloud.")
            yield await self.call_cloud_fallback(system_prompt, user_text)

    async def call_cloud_fallback(self, system_prompt: str, user_text: str) -> str:
        """Call Gemini via google-generativeai as cloud fallback."""
        print(f"☁️ [LLM-CLOUD] Routing to Gemini ({_GEMINI_FALLBACK_MODEL})...")
        if not self._google_api_key:
            return "[SPARK] Cloud fallback unavailable: no Google API key configured in config/secrets.yaml."
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self._google_api_key)
            
            def _get_res():
                return client.models.generate_content(
                    model=_GEMINI_FALLBACK_MODEL,
                    contents=user_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    )
                )
            response = await asyncio.to_thread(_get_res)
            result = response.text if hasattr(response, "text") else str(response)
            print(f"☁️ [LLM-CLOUD] Gemini response received ({len(result)} chars).")
            return result
        except Exception as e:
            err_str = str(e)
            # Detect quota / rate-limit errors and return a clean user-facing message
            if any(kw in err_str for kw in ("429", "RESOURCE_EXHAUSTED", "quota", "rate", "FreeTier")):
                wait_hint = ""
                import re
                m = re.search(r'seconds: (\d+)', err_str)
                if m:
                    wait_hint = f" Please wait ~{m.group(1)}s and try again."
                print(f"⚠️ [LLM-CLOUD] Gemini rate limit hit.{wait_hint}")
                return f"I'm temporarily rate-limited by the cloud API (free tier).{wait_hint} Please try again in a moment."
            print(f"⚠️ [LLM-CLOUD] Gemini call failed: {repr(e)}")
            return f"[SPARK] Cloud LLM unavailable: {type(e).__name__}."
