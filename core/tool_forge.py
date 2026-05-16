from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
import subprocess
import sys
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from core.generated_tools import publish_generated_tool

log = logging.getLogger("spark.tool_forge")

FORGE_DIR = Path("spark_dev_memory/tool_forge")
FORGE_DIR.mkdir(parents=True, exist_ok=True)
TOOL_REVIEW_PATH = Path("spark_dev_memory/autonomy/pending_tools.json")
TOOL_REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)

ALLOWED_IMPORTS = {
    "json",
    "math",
    "statistics",
    "datetime",
    "time",
    "re",
    "typing",
    "pathlib",
    "collections",
    "itertools",
    "functools",
    "string",
    "random",
    "tools",
}

FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "input"}
FORBIDDEN_ATTRS = {
    ("os", "system"),
    ("os", "popen"),
    ("subprocess", "Popen"),
    ("subprocess", "run"),
    ("subprocess", "call"),
    ("shutil", "rmtree"),
    ("socket", "socket"),
    ("ctypes", "CDLL"),
    ("ctypes", "windll"),
}


@dataclass(slots=True)
class ForgeResult:
    name: str
    path: str
    validated: bool
    review_id: str | None
    status: str
    reason: str


def _node_to_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_node_to_name(node.value)}.{node.attr}"
    return ""


def validate_tool_code(code: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"Syntax error: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root not in ALLOWED_IMPORTS:
                    return False, f"Import not allowed: {alias.name}"
        elif isinstance(node, ast.Call):
            name = _node_to_name(node.func)
            root = name.split(".", 1)[0]
            if root in FORBIDDEN_NAMES:
                return False, f"Forbidden call: {name}"
            if (root, name.split(".")[-1]) in FORBIDDEN_ATTRS:
                return False, f"Forbidden call: {name}"
    return True, "Approved"


def _load_tool_reviews() -> list[dict[str, str]]:
    if not TOOL_REVIEW_PATH.exists():
        return []
    try:
        data = json.loads(TOOL_REVIEW_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        log.warning("Tool review queue could not be read: %s", exc)
        return []


def _save_tool_reviews(reviews: list[dict[str, str]]) -> None:
    TOOL_REVIEW_PATH.write_text(json.dumps(reviews, indent=2, ensure_ascii=False), encoding="utf-8")


def list_tool_reviews() -> list[dict[str, str]]:
    return [review for review in _load_tool_reviews() if review.get("status") == "pending"]


def approve_tool_review(review_id: str) -> dict[str, str]:
    reviews = _load_tool_reviews()
    for index, review in enumerate(reviews):
        if str(review.get("id")) != review_id:
            continue
        if review.get("status") != "pending":
            raise ValueError("Tool review is not pending")

        code = str(review.get("code") or "")
        name = str(review.get("name") or review.get("path") or "generated_tool").strip()
        publish_generated_tool(name, code)
        reviews[index] = {**review, "status": "approved", "reviewed_at": datetime.utcnow().isoformat()}
        _save_tool_reviews(reviews)
        log.info(f"Tool approved: {name} (review: {review_id[:8]}...)")
        return reviews[index]

    raise KeyError(review_id)


def reject_tool_review(review_id: str) -> dict[str, str]:
    reviews = _load_tool_reviews()
    for index, review in enumerate(reviews):
        if str(review.get("id")) != review_id:
            continue
        reviews[index] = {**review, "status": "rejected", "reviewed_at": datetime.utcnow().isoformat()}
        _save_tool_reviews(reviews)
        log.info(f"Tool rejected: {review_id[:8]}...")
        return reviews[index]
    raise KeyError(review_id)


def _auto_approve_high_confidence_tools() -> None:
    """
    Auto-approve pending tools if:
    1. Code validation passes (validate_tool_code returns True)
    2. Behavioral signal count >= 3 (indicating recurring use pattern)
    This enables SPARK to deploy new tools without manual approval.
    """
    try:
        from core.memory_loop import read_turns
        
        reviews = _load_tool_reviews()
        if not reviews:
            return
        
        # Count behavioral signals from recent turns
        turns = read_turns()
        signal_keywords = {"tool", "forge", "create", "generate", "function", "script"}
        signal_count = sum(
            1 for turn in turns[-30:]
            if turn.get("role") == "user" and any(keyword in turn.get("content", "").lower() for keyword in signal_keywords)
        )
        
        for review in reviews:
            if review.get("status") != "pending":
                continue
            
            review_id = review.get("id")
            code = str(review.get("code") or "")
            name = str(review.get("name") or "generated_tool")
            
            # Check if code validates
            validated, reason = validate_tool_code(code)
            if not validated:
                continue
            
            # Auto-approve if we have >= 3 behavioral signals
            if signal_count >= 3:
                try:
                    approve_tool_review(review_id)
                    log.info(f"[AUTO-APPROVED] Tool '{name}' deployed (signals: {signal_count})")
                    
                    # Flag in HUD
                    try:
                        from core.main import broadcast_hud_event
                        broadcast_hud_event(
                            "agent_log",
                            {
                                "type": "info",
                                "agent": "TOOL_FORGE",
                                "action": "Auto-Deployment",
                                "data": f"Tool '{name}' auto-approved and deployed (confidence: high)",
                            }
                        )
                    except:
                        pass
                except Exception as e:
                    log.debug(f"Could not auto-approve tool {review_id[:8]}...: {e}")
    except Exception as e:
        log.debug(f"Auto-approval check failed: {e}")



def forge_tool(name: str, code: str, description: str = "") -> ForgeResult:
    approved, reason = validate_tool_code(code)
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", name).strip("_") or "forged_tool"
    path = FORGE_DIR / f"{safe_name}.py"
    review_id = hashlib.sha1(f"{safe_name}:{code}".encode("utf-8")).hexdigest()[:16]
    if approved:
        path.write_text(code, encoding="utf-8")
        reviews = _load_tool_reviews()
        proposal = {
            "id": review_id,
            "status": "pending",
            "name": safe_name,
            "path": str(path),
            "description": description,
            "code": code,
            "created_at": datetime.utcnow().isoformat(),
            "fingerprint": hashlib.sha1(code.encode("utf-8")).hexdigest(),
        }
        if not any(review.get("fingerprint") == proposal["fingerprint"] and review.get("status") == "pending" for review in reviews):
            reviews.append(proposal)
            _save_tool_reviews(reviews)
        
        # Check for auto-approval opportunities
        _auto_approve_high_confidence_tools()
        
        return ForgeResult(name=safe_name, path=str(path), validated=True, review_id=review_id, status="pending_review", reason="Pending approval")
    return ForgeResult(name=safe_name, path=str(path), validated=False, review_id=None, status="rejected", reason=reason)


def run_forged_tool(path: str, argument: str = "", timeout: int = 15) -> str:
    script_path = Path(path)
    if not script_path.exists():
        return f"Forge error: {script_path} does not exist"

    result = subprocess.run(
        [sys.executable, str(script_path), argument],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if result.returncode != 0:
        return f"Forge execution failed: {stderr or stdout or 'unknown error'}"
    return stdout or stderr or "Forge tool completed successfully"