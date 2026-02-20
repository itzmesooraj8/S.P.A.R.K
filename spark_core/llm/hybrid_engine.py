import asyncio
import httpx
from typing import Optional

class HybridLLM:
    """
    Hybrid LLM engine to call Local Ollama as primary.
    If it fails or input is too large, fallback to Cloud (Gemini/Claude/OpenAI).
    """
    def __init__(self, model: str = "llama3:8b", ollama_host: str = "http://localhost:11434"):
        self.model = model
        self.host = ollama_host
        print(f"🧬 [LLM] Engine Booting. Primary: Local ({model}) | Fallback: Cloud")

    async def generate(self, system_prompt: str, user_text: str):
        """Call Local Model via Async HTTP. Uses streaming for speed."""
        import json
        
        # Determine if we should offload to cloud
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
            async with httpx.AsyncClient(timeout=60.0) as client:
                print(f"🧠 [LLM] Calling local Ollama stream: {self.model} ...")
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
                    else:
                        print(f"⚠️ [LLM] Local engine error: {response.status_code}")
                        yield await self.call_cloud_fallback(system_prompt, user_text)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"⚠️ [LLM] Local engine unavailable. Error: {repr(e)}\nTraceback:\n{error_details}\nFallback to Cloud.")
            yield await self.call_cloud_fallback(system_prompt, user_text)

    async def call_cloud_fallback(self, system_prompt: str, user_text: str) -> str:
        # Implement provider logic later (e.g. Gemini via google-genai)
        print("☁️ [LLM-CLOUD] Processing via cloud fallback...")
        await asyncio.sleep(1) # simulate call
        return "I am processing this via cloud fallback due to local memory constraints or unavailability."
