from __future__ import annotations

import argparse
import asyncio
import json
import sys
from urllib.parse import urlparse

import requests
import websockets


def _normalize_base_url(value: str) -> str:
    base = value.strip().rstrip("/")
    if not base:
        raise ValueError("base URL is required")
    if not base.startswith(("http://", "https://")):
        base = f"https://{base}"
    return base


def _ws_url(base_url: str, path: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}{path}"


async def _check_websocket(ws_url: str, timeout: float) -> tuple[bool, str]:
    try:
        async with websockets.connect(ws_url, open_timeout=timeout, close_timeout=timeout) as socket:
            try:
                message = await asyncio.wait_for(socket.recv(), timeout=timeout)
            except asyncio.TimeoutError:
                return False, f"connected but no message received within {timeout}s"
            return True, str(message)
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a public SPARK tunnel")
    parser.add_argument("base_url", help="Public base URL, for example https://spark.example.com")
    parser.add_argument("--token", required=True, help="SPARK_ACCESS_TOKEN value")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    args = parser.parse_args()

    base_url = _normalize_base_url(args.base_url)
    headers = {"Authorization": f"Bearer {args.token}"}
    timeout = args.timeout
    failures: list[str] = []

    checks = [
        ("GET /health", f"{base_url}/health", False),
        ("GET /ping", f"{base_url}/ping", False),
        ("GET /status", f"{base_url}/status", True),
        ("POST /chat", f"{base_url}/chat", True),
        ("GET /hud", f"{base_url}/hud", True),
    ]

    for name, url, auth_required in checks:
        try:
            if name == "POST /chat":
                response = requests.post(url, json={"message": "hello"}, headers=headers if auth_required else None, timeout=timeout)
            else:
                response = requests.get(url, headers=headers if auth_required else None, timeout=timeout)
            if response.status_code >= 400:
                failures.append(f"{name} failed: {response.status_code} {response.text[:200]}")
            else:
                print(f"OK {name}: {response.status_code}")
                if name == "GET /status":
                    print(f"status body: {response.text[:200]}")
                if name == "POST /chat":
                    try:
                        payload = response.json()
                        print(f"chat reply: {payload.get('response', '')}")
                    except Exception:
                        print(f"chat body: {response.text[:200]}")
        except Exception as exc:
            failures.append(f"{name} error: {exc}")

    async def websocket_phase() -> None:
        ws_url = _ws_url(base_url, "/ws/system")
        ok, detail = await _check_websocket(ws_url, timeout)
        if ok:
            print(f"OK WS /ws/system: {detail[:200]}")
        else:
            failures.append(f"WS /ws/system failed: {detail}")

    try:
        asyncio.run(websocket_phase())
    except Exception as exc:
        failures.append(f"WS /ws/system error: {exc}")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nAll public tunnel checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
