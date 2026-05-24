from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import textwrap
from datetime import datetime
from typing import Sequence

from spark.core import SparkCore, load_config


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
WHITE = "\033[37m"
RED = "\033[31m"


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, color: str) -> str:
    if not _use_color():
        return text
    return f"{color}{text}{RESET}"


def _title(text: str) -> str:
    return _c(text, BOLD + CYAN)


def _accent(text: str) -> str:
    return _c(text, CYAN)


def _muted(text: str) -> str:
    return _c(text, DIM + WHITE)


def _ok(text: str) -> str:
    return _c(text, GREEN)


def _warn(text: str) -> str:
    return _c(text, YELLOW)


def _error(text: str) -> str:
    return _c(text, RED)


def _terminal_width() -> int:
    return max(shutil.get_terminal_size(fallback=(88, 24)).columns, 72)


def _wrap(text: str, indent: int = 0, width: int | None = None) -> str:
    width = width or _terminal_width()
    return textwrap.fill(text, width=max(width - indent, 40), subsequent_indent=" " * indent)


def _rule(char: str = "─") -> str:
    return char * _terminal_width()


def _panel_lines(title: str, body: Sequence[str], accent: str = CYAN) -> list[str]:
    width = _terminal_width()
    inner_width = max(width - 4, 48)
    top = f"┌{('─' * (width - 2))}┐"
    bottom = f"└{('─' * (width - 2))}┘"
    title_text = f" {title} "
    if len(title_text) < width - 2:
        title_row = f"│{_c(title_text.ljust(width - 2), accent)}│"
    else:
        title_row = f"│{_c(title_text[:width - 2], accent)}│"

    lines = [top, title_row, f"│{' ' * (width - 2)}│"]
    for raw_line in body:
        wrapped = textwrap.wrap(raw_line, width=inner_width) or [""]
        for segment in wrapped:
            lines.append(f"│ {segment.ljust(inner_width)} │")
    lines.append(bottom)
    return lines


def _print_banner() -> None:
    logo = [
        " ███████╗██████╗  █████╗ ██████╗ ██╗  ██╗",
        " ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝",
        " ███████╗██████╔╝███████║██████╔╝█████╔╝ ",
        " ╚════██║██╔═══╝ ██╔══██║██╔══██╗██╔═██╗ ",
        " ███████║██║     ██║  ██║██║  ██║██║  ██╗",
        " ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝",
    ]
    print(_c(_rule("═"), MAGENTA))
    for line in logo:
        print(_c(line, BOLD + CYAN))
    print(_c("Sentient Proactive Autonomous Response Kernel", BOLD + WHITE))
    print(_muted("Local-first CLI. Type naturally. Use ask, once, voice, or status from the same shell."))
    print(_c(_rule("═"), MAGENTA))
    print(_c("Quick start", BOLD + MAGENTA))
    quick = [
        "ask <prompt>      send one message directly",
        "once              run one autonomous cycle",
        "voice             start live speech mode",
        "status            inspect current runtime config",
        "exit / quit       leave the interactive shell",
    ]
    for line in quick:
        print(_muted(f"  • {line}"))
    print(_c(_rule(), MAGENTA))


def _print_turn(role: str, content: str, accent: str = CYAN) -> None:
    width = _terminal_width()
    title = f" {role.upper()} · {datetime.now().strftime('%H:%M:%S')} "
    top = f"┌{('─' * (width - 2))}┐"
    bottom = f"└{('─' * (width - 2))}┘"
    print(_c(top, accent))
    print(_c(f"│{title.ljust(width - 2)}│", accent))
    print(_c(f"│{' ' * (width - 2)}│", accent))
    for paragraph in (content or "").splitlines() or [""]:
        wrapped = textwrap.wrap(paragraph, width=max(width - 4, 40)) or [""]
        for segment in wrapped:
            print(_c(f"│ {segment.ljust(width - 4)} │", accent))
    print(_c(bottom, accent))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spark_cli.py",
        description="SPARK command line interface",
    )
    parser.add_argument("--once", action="store_true", help="Compatibility alias for 'once'")
    parser.add_argument("--voice", action="store_true", help="Compatibility alias for 'voice'")
    parser.add_argument("--voice-once", action="store_true", help="Compatibility alias for 'voice-once'")
    parser.add_argument("--dry-run", action="store_true", help="Compatibility alias for 'status'")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output where supported")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the autonomous loop")
    subparsers.add_parser("start", help="Alias for run")
    subparsers.add_parser("once", help="Run one autonomous cycle and exit")
    subparsers.add_parser("voice", help="Run the live mic -> Whisper -> LLM -> speak loop")
    subparsers.add_parser("voice-once", help="Run one voice interaction and exit")

    ask_parser = subparsers.add_parser("ask", help="Send a text prompt directly to SPARK")
    ask_parser.add_argument("prompt", nargs=argparse.REMAINDER, help="Prompt text to send")

    subparsers.add_parser("status", help="Show the current runtime configuration")
    return parser


def _print_status() -> None:
    config = load_config()
    llm_config = config.get("llm", {}) if isinstance(config.get("llm", {}), dict) else {}
    tools_config = config.get("tools", {}) if isinstance(config.get("tools", {}), dict) else {}

    body = [
        f"Config loaded: {bool(config)}",
        f"Loop interval: {config.get('loop_interval_seconds', 5)}s",
        f"Reflection interval: {config.get('reflection_interval_seconds', 86400)}s",
        f"LLM backend: {llm_config.get('backend', 'ollama')}",
        f"Ollama host: {llm_config.get('ollama_host', 'http://localhost:11434')}",
        f"Ollama model: {llm_config.get('ollama_model', 'gemma4')}",
        f"Generated tools dir: {tools_config.get('generated_dir', 'tools/generated')}",
    ]
    for line in _panel_lines("SPARK STATUS", body, accent=GREEN):
        print(line)


def _print_once_result(result: dict | None, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result is None:
        _print_turn("spark", "SPARK is idle.", accent=YELLOW)
        return

    reply = str(result.get("reply", "") or "").strip()
    _print_turn("spark", reply or "SPARK returned no reply.", accent=CYAN)


def _print_voice_once_result(result: dict | None, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result is None:
        _print_turn("voice", "No speech detected.", accent=YELLOW)
        return

    reply = str(result.get("reply", "") or "").strip()
    transcript = str(result.get("transcript", "") or "").strip()
    if transcript:
        _print_turn("heard", transcript, accent=MAGENTA)
    _print_turn("spark", reply or "SPARK returned no reply.", accent=CYAN)


def _print_ask_result(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    reply = str(result.get("reply", "") or "").strip()
    tool_used = result.get("tool_used")
    if tool_used:
        _print_turn("tool", str(tool_used), accent=BLUE)
    _print_turn("spark", reply or "SPARK returned no reply.", accent=CYAN)


def _run_interactive_shell(core: SparkCore) -> int:
    _print_banner()

    while True:
        try:
            prompt = input(_c("SPARK ▸ ", BOLD + CYAN)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not prompt:
            continue

        if prompt.lower() in {"exit", "quit"}:
            return 0

        _print_turn("you", prompt, accent=MAGENTA)
        result = core.llm.execute(prompt)
        _print_ask_result(result, False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.dry_run or args.command == "status":
        _print_status()
        return 0

    if args.command in {"once"} or args.once:
        core = SparkCore()
        _print_once_result(core.run_once(), args.json)
        return 0

    if args.command in {"voice-once"} or args.voice_once:
        core = SparkCore()
        _print_voice_once_result(core.run_voice_once(), args.json)
        return 0

    if args.command in {"voice"} or args.voice:
        core = SparkCore()
        core.run_voice_loop()
        return 0

    if args.command in {"ask"}:
        prompt = " ".join(args.prompt).strip()
        if not prompt:
            parser.error("ask requires a prompt")
        core = SparkCore()
        _print_ask_result(core.llm.execute(prompt), args.json)
        return 0

    core = SparkCore()
    return _run_interactive_shell(core)


if __name__ == "__main__":
    raise SystemExit(main())
