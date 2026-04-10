import asyncio
import os
import pathlib
import httpx
import json

_DEFAULT_MODEL = "gemma3:4b"  # Strictly enforced local target
_GEMINI_FALLBACK_MODEL = "gemini-2.0-flash"

def _load_google_key() -> str:
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
    Hybrid LLM engine strictly prioritizing Local Ollama (gemma3:4b).
    Fallback to Gemini only after 3 failed retries.
    """
    def __init__(self, model: str = _DEFAULT_MODEL, ollama_host: str = "http://127.0.0.1:11434"):
        self.model = _DEFAULT_MODEL # Hardcode overrides to perfectly match OS requirements
        self.host = ollama_host
        self._google_api_key = _load_google_key()
        
        # ───────────────────────────────────────────────────────────────────────
        # FIX 1: Health check at server boot pinging /api/tags
        # ───────────────────────────────────────────────────────────────────────
        try:
            res = httpx.get(f"{self.host}/api/tags", timeout=2.0)
            if res.status_code == 200:
                print(f"[LLM] Ollama ONLINE — {self.model} ready")
            else:
                print("[LLM] WARNING: Ollama offline — will use Gemini fallback")
        except:
            print("[LLM] WARNING: Ollama offline — will use Gemini fallback")

    async def generate(self, system_prompt: str, user_text: str):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "stream": True 
        }

        retries = 3
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2.0, read=120.0, write=10.0, pool=5.0)) as client:
                    async with client.stream("POST", f"{self.host}/api/chat", json=payload) as response:
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
                            # Standard Exit: Successfully returned response entirely from local
                            return 
                        else:
                            raise Exception(f"HTTP {response.status_code}")
                            
            except Exception as e:
                # Mute inner loop failures silently, exception triggers if retries are totally exhausted.
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                else:
                    print(f"⚠️ [LLM] Ollama stream error after retries: {repr(e)}. Falling back to Gemini.")

        # Reached ONLY if all local Ollama retries hard fail
        yield await self.call_cloud_fallback(system_prompt, user_text)

    async def call_cloud_fallback(self, system_prompt: str, user_text: str) -> str:
        if not self._google_api_key:
            return "[SPARK] Gemini Fallback unavailable (no API key configured)."
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
            return response.text if hasattr(response, "text") else str(response)
        except Exception as e:
            return f"[SPARK] Cloud API connection lost: {str(e)}"
