"""core/hybrid.py

Helper utilities to load the hybrid strategy and tiered prompt templates.
This module is intentionally lightweight and dependency-free so it can be
imported by runtime routing code to obtain system prompts and the fallback chain.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, List

BASE = Path(__file__).resolve().parent
CONFIG_PATH = Path(BASE.parent, "config", "hybrid_strategy.json")
PROMPTS_DIR = Path(BASE, "hybrid_prompts")


def load_strategy() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _read_prompt_file(name: str) -> str:
    p = PROMPTS_DIR / name
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def get_tier_prompt(tier: int) -> str:
    """Return the system prompt template for a given tier index (0..3)."""
    if tier == 0:
        return _read_prompt_file("tier_0.txt")
    if tier in (1, 2):
        return _read_prompt_file("tier_1_2.txt")
    return _read_prompt_file("tier_3.txt")


def get_fallback_chain() -> List[Dict[str, Any]]:
    """Return an ordered list of tiers for fallback resolution, using env overrides."""
    strategy = load_strategy()
    tiers = strategy.get("tiers", [])
    chain: List[Dict[str, Any]] = []
    for t in tiers:
        env_key = t.get("model_env")
        model = os.getenv(env_key, t.get("default_model")) if env_key else t.get("default_model")
        chain.append({
            "tier": t.get("tier"),
            "name": t.get("name"),
            "model": model,
            "role": t.get("role"),
            "behavior": t.get("behavior"),
        })
    return chain


def render_handoff_state(session_id: str, tracking: Dict[str, Any], last_partial: str, recommended_fallback: int) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "tracking_matrix": tracking,
        "last_response_partial": last_partial,
        "recommended_fallback": recommended_fallback,
    }
