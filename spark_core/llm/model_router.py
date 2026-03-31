"""
SPARK ModelRouter — Intelligent model selection engine.

Routes tasks to the optimal LLM based on:
  - Task type     (code | reasoning | search | creative | safety | fast)
  - Context size  (short / medium / long)
  - Cost budget   (free / paid)
  - Latency class (realtime / background)
  - Provider availability (Ollama health, API keys present)

Maintains live performance stats (latency, success rate) per provider.
"""
import asyncio
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional

import httpx


class TaskType(str, Enum):
    CODE       = "code"        # Code generation, debugging, refactoring
    REASONING  = "reasoning"   # Analysis, logic, planning
    SEARCH     = "search"      # Retrieval-augmented Q&A
    CREATIVE   = "creative"    # Writing, ideation
    SAFETY     = "safety"      # Risk classification, policy checks
    FAST       = "fast"        # Quick single-turn completions
    VISION     = "vision"      # Multimodal (image understanding)


class LatencyClass(str, Enum):
    REALTIME   = "realtime"    # < 500 ms first token
    BACKGROUND = "background"  # seconds OK


@dataclass
class ModelProfile:
    name: str              # e.g. "llama3:8b", "gpt-4o", "gemini-2.0-flash"
    provider: str          # "ollama" | "openai" | "anthropic" | "google"
    task_strengths: List[TaskType]
    max_context_tokens: int
    cost_tier: int         # 0=free, 1=cheap, 2=moderate, 3=expensive
    latency_class: LatencyClass
    requires_key: str      # env var name that must be set, "" for local


@dataclass
class ProviderStats:
    attempts: int = 0
    successes: int = 0
    total_latency_ms: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / self.attempts if self.attempts else 1.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.successes if self.successes else 9999.0

    def record_success(self, latency_ms: float):
        self.attempts += 1
        self.successes += 1
        self.total_latency_ms += latency_ms
        self.consecutive_failures = 0

    def record_failure(self):
        self.attempts += 1
        self.last_failure = time.monotonic()
        self.consecutive_failures += 1

    def is_healthy(self) -> bool:
        if self.consecutive_failures >= 3:
            # Back-off: retry after 60 s
            return (time.monotonic() - self.last_failure) > 60
        return True


# ── Model catalog ─────────────────────────────────────────────────────────────

_CATALOG: List[ModelProfile] = [
    # ── Local (Ollama) ────────────────────────────
    ModelProfile(
        name="llama3:8b", provider="ollama",
        task_strengths=[TaskType.CODE, TaskType.REASONING, TaskType.FAST],
        max_context_tokens=8192, cost_tier=0,
        latency_class=LatencyClass.REALTIME, requires_key="",
    ),
    ModelProfile(
        name="deepseek-coder:6.7b", provider="ollama",
        task_strengths=[TaskType.CODE],
        max_context_tokens=16384, cost_tier=0,
        latency_class=LatencyClass.REALTIME, requires_key="",
    ),
    ModelProfile(
        name="mistral:7b", provider="ollama",
        task_strengths=[TaskType.FAST, TaskType.CREATIVE, TaskType.SEARCH],
        max_context_tokens=8192, cost_tier=0,
        latency_class=LatencyClass.REALTIME, requires_key="",
    ),
    ModelProfile(
        name="phi3:mini", provider="ollama",
        task_strengths=[TaskType.FAST, TaskType.SAFETY],
        max_context_tokens=4096, cost_tier=0,
        latency_class=LatencyClass.REALTIME, requires_key="",
    ),
    # ── Google Gemini ──────────────────────────────
    ModelProfile(
        name="gemini-2.0-flash", provider="google",
        task_strengths=[TaskType.REASONING, TaskType.SEARCH, TaskType.FAST, TaskType.CREATIVE],
        max_context_tokens=1_000_000, cost_tier=1,
        latency_class=LatencyClass.REALTIME, requires_key="GOOGLE_API_KEY",
    ),
    ModelProfile(
        name="gemini-2.0-pro", provider="google",
        task_strengths=[TaskType.CODE, TaskType.REASONING, TaskType.VISION],
        max_context_tokens=1_000_000, cost_tier=2,
        latency_class=LatencyClass.BACKGROUND, requires_key="GOOGLE_API_KEY",
    ),
    # ── OpenAI ─────────────────────────────────────
    ModelProfile(
        name="gpt-4o-mini", provider="openai",
        task_strengths=[TaskType.CODE, TaskType.FAST, TaskType.REASONING],
        max_context_tokens=128_000, cost_tier=1,
        latency_class=LatencyClass.REALTIME, requires_key="OPENAI_API_KEY",
    ),
    ModelProfile(
        name="gpt-4o", provider="openai",
        task_strengths=[TaskType.CODE, TaskType.REASONING, TaskType.VISION, TaskType.SAFETY],
        max_context_tokens=128_000, cost_tier=3,
        latency_class=LatencyClass.BACKGROUND, requires_key="OPENAI_API_KEY",
    ),
    # ── Anthropic ──────────────────────────────────
    ModelProfile(
        name="claude-3-5-haiku-20241022", provider="anthropic",
        task_strengths=[TaskType.FAST, TaskType.CREATIVE, TaskType.SEARCH],
        max_context_tokens=200_000, cost_tier=1,
        latency_class=LatencyClass.REALTIME, requires_key="ANTHROPIC_API_KEY",
    ),
    ModelProfile(
        name="claude-sonnet-4-5", provider="anthropic",
        task_strengths=[TaskType.CODE, TaskType.REASONING, TaskType.SAFETY, TaskType.CREATIVE],
        max_context_tokens=200_000, cost_tier=2,
        latency_class=LatencyClass.BACKGROUND, requires_key="ANTHROPIC_API_KEY",
    ),
]


class ModelRouter:
    """
    Selects the optimal model for each request and routes the generation call.
    
    Usage:
        async for token in model_router.route_generate(
            system_prompt, user_text,
            task_type=TaskType.CODE, context_tokens=2000
        ):
            print(token, end="")
    """

    def __init__(self, ollama_host: str = "http://127.0.0.1:11434"):
        self._ollama_host = ollama_host
        self._stats: Dict[str, ProviderStats] = {}
        self._available_local: Optional[List[str]] = None   # cache
        self._local_checked_at: float = 0.0
        self._google_api_key = self._load_key("GOOGLE_GEMINI_KEY", "google_gemini")
        self._openai_api_key = self._load_key("OPENAI_API_KEY", "openai")
        self._anthropic_api_key = self._load_key("ANTHROPIC_API_KEY", "anthropic")
        print("🧬 [ModelRouter] Initialized with", len(_CATALOG), "model profiles.")

    # ── Key resolution ─────────────────────────────────────────────────────────

    def _load_key(self, env_var: str, yaml_key: str) -> str:
        val = os.getenv(env_var, "")
        if not val:
            try:
                import yaml, pathlib
                p = pathlib.Path(__file__).parent.parent.parent / "config" / "secrets.yaml"
                if p.exists():
                    data = yaml.safe_load(p.read_text()) or {}
                    val = data.get("keys", {}).get(yaml_key, "")
            except Exception:
                pass
        return val or ""

    # ── Local model discovery ──────────────────────────────────────────────────

    async def _get_local_models(self) -> List[str]:
        now = time.monotonic()
        if self._available_local is not None and now - self._local_checked_at < 30:
            return self._available_local
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                r = await c.get(f"{self._ollama_host}/api/tags")
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    self._available_local = models
                    self._local_checked_at = now
                    return models
        except Exception:
            pass
        self._available_local = []
        self._local_checked_at = now
        return []

    # ── Provider key availability ──────────────────────────────────────────────

    def _key_for(self, profile: ModelProfile) -> str:
        if not profile.requires_key:
            return "local"
        mapping = {
            "GOOGLE_API_KEY": self._google_api_key,
            "OPENAI_API_KEY": self._openai_api_key,
            "ANTHROPIC_API_KEY": self._anthropic_api_key,
        }
        return mapping.get(profile.requires_key, "")

    # ── Model selection ────────────────────────────────────────────────────────

    async def select_model(
        self,
        task_type: TaskType = TaskType.FAST,
        context_tokens: int = 1000,
        latency_class: LatencyClass = LatencyClass.REALTIME,
        prefer_local: bool = True,
        max_cost_tier: int = 3,
    ) -> ModelProfile:
        local_models = await self._get_local_models()

        candidates: List[ModelProfile] = []
        for p in _CATALOG:
            # Must have key (or be local)
            if p.requires_key and not self._key_for(p):
                continue
            # Local: must be actually running
            if p.provider == "ollama" and p.name not in local_models:
                continue
            # Cost gate
            if p.cost_tier > max_cost_tier:
                continue
            # Context window
            if context_tokens > p.max_context_tokens:
                continue
            # Latency gate for realtime tasks
            if latency_class == LatencyClass.REALTIME and p.latency_class == LatencyClass.BACKGROUND:
                continue
            # Circuit-breaker health
            stats = self._stats.get(p.name, ProviderStats())
            if not stats.is_healthy():
                continue
            candidates.append(p)

        if not candidates:
            # Expand — drop latency + realtime constraint
            for p in _CATALOG:
                if p.provider == "ollama":
                    if p.name in local_models:
                        candidates.append(p)
                        break
            if not candidates:
                # Last resort: pick first in catalog (will fail gracefully)
                return _CATALOG[0]

        # Score candidates
        def score(p: ModelProfile) -> float:
            s = 0.0
            # Task strength match
            if task_type in p.task_strengths:
                s += 10.0
            # Prefer local if flag is set (Massive boost for Jarvis Local-First)
            if prefer_local and p.provider == "ollama":
                s += 5000.0
            # Lower cost is better
            s -= p.cost_tier * 2.0
            # Lower latency is better (for realtime)
            if p.latency_class == LatencyClass.REALTIME:
                s += 3.0
            # Historical performance
            pstats = self._stats.get(p.name, ProviderStats())
            s += pstats.success_rate * 2.0
            s -= (pstats.avg_latency_ms / 1000.0)
            return s

        candidates.sort(key=score, reverse=True)
        selected = candidates[0]
        print(f"🎯 [ModelRouter] Task={task_type.value} → {selected.name} ({selected.provider})")
        return selected

    # ── Generation ────────────────────────────────────────────────────────────

    async def route_generate(
        self,
        system_prompt: str,
        user_text: str,
        task_type: TaskType = TaskType.FAST,
        context_tokens: int = 1000,
        latency_class: LatencyClass = LatencyClass.REALTIME,
        prefer_local: bool = True,
        max_cost_tier: int = 3,
        attempt: int = 0,
    ) -> AsyncGenerator[str, None]:
        """Yields token stream. Automatically retries with fallback on failure."""
        profile = await self.select_model(
            task_type, context_tokens, latency_class, prefer_local, max_cost_tier
        )

        t0 = time.monotonic()
        try:
            gen = self._dispatch(profile, system_prompt, user_text)
            async for token in gen:
                yield token
            latency_ms = (time.monotonic() - t0) * 1000
            self._get_stats(profile.name).record_success(latency_ms)

        except Exception as exc:
            self._get_stats(profile.name).record_failure()
            print(f"⚠️ [ModelRouter] {profile.name} failed: {exc}")
            if attempt < 2:
                # Retry with cloud fallback (raise cost tier)
                async for token in self.route_generate(
                    system_prompt, user_text, task_type, context_tokens,
                    latency_class, prefer_local=False, max_cost_tier=3, attempt=attempt + 1
                ):
                    yield token
            else:
                yield f"[ModelRouter] All providers failed after {attempt + 1} attempts: {exc}"

    def _get_stats(self, name: str) -> ProviderStats:
        if name not in self._stats:
            self._stats[name] = ProviderStats()
        return self._stats[name]

    # ── Provider dispatchers ───────────────────────────────────────────────────

    async def _dispatch(
        self, profile: ModelProfile, system_prompt: str, user_text: str
    ) -> AsyncGenerator[str, None]:
        dispatch_map = {
            "ollama":    self._gen_ollama,
            "google":    self._gen_google,
            "openai":    self._gen_openai,
            "anthropic": self._gen_anthropic,
        }
        fn = dispatch_map.get(profile.provider)
        if not fn:
            raise ValueError(f"Unknown provider: {profile.provider}")
        async for token in fn(profile, system_prompt, user_text):
            yield token

    async def _gen_ollama(self, profile: ModelProfile, sys: str, user: str):
        import json
        payload = {
            "model": profile.name,
            "messages": [{"role": "system", "content": sys}, {"role": "user", "content": user}],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=3.0, read=120.0, write=10.0, pool=5.0)) as c:
            async with c.stream("POST", f"{self._ollama_host}/api/chat", json=payload) as r:
                async for line in r.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue

    async def _gen_google(self, profile: ModelProfile, sys: str, user: str):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self._google_api_key)
        
        # Async-to-sync wrapping since SDK generator is synchronous
        def _get_stream():
            return client.models.generate_content_stream(
                model=profile.name,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=sys,
                )
            )
            
        stream = await asyncio.to_thread(_get_stream)
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    async def _gen_openai(self, profile: ModelProfile, sys: str, user: str):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._openai_api_key)
        stream = await client.chat.completions.create(
            model=profile.name,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta

    async def _gen_anthropic(self, profile: ModelProfile, sys: str, user: str):
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._anthropic_api_key)
        async with client.messages.stream(
            model=profile.name,
            max_tokens=4096,
            system=sys,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ── Diagnostics ───────────────────────────────────────────────────────────

    async def get_status(self) -> dict:
        local_models = await self._get_local_models()
        available = []
        for p in _CATALOG:
            has_key = bool(self._key_for(p)) or not p.requires_key
            is_local_up = p.provider != "ollama" or p.name in local_models
            stats = self._stats.get(p.name, ProviderStats())
            available.append({
                "name": p.name,
                "provider": p.provider,
                "available": has_key and is_local_up,
                "task_strengths": [t.value for t in p.task_strengths],
                "cost_tier": p.cost_tier,
                "success_rate": round(stats.success_rate, 3),
                "avg_latency_ms": round(stats.avg_latency_ms, 1),
                "attempts": stats.attempts,
            })
        return {"models": available, "local_running": local_models}


# ── Singleton ─────────────────────────────────────────────────────────────────
model_router = ModelRouter()
