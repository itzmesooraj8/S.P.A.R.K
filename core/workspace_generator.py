# core/workspace_generator.py
import json
import os
import re
import subprocess
import sys
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.workspace_generator")

SANDBOX_DIR = Path("sandbox").resolve()

def verify_safe_path(path: str | Path) -> Path:
    """Resolve path relative to sandbox directory and verify it is strictly within the sandbox folder."""
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    p = Path(path)
    if p.is_absolute():
        target = p.resolve()
    else:
        target = (SANDBOX_DIR / p).resolve()
            
    if target != SANDBOX_DIR and SANDBOX_DIR not in target.parents:
        raise PermissionError(f"Security Violation: Path '{path}' (resolved to '{target}') is outside the sandbox '{SANDBOX_DIR}'")
    return target

async def generate_workspace(project_name: str, prompt: str) -> dict[str, Any]:
    """
    Decouple code execution from chat text loops. Translates code creation requests
    into structured JSON manifests defining frameworks, block locations, and view parameters,
    creates files inside sandbox/ cleanly, and triggers non-blocking preview shell calls.
    """
    # Clean project name
    project_name = re.sub(r'[^a-zA-Z0-9_]', '', project_name.replace(" ", "_")).strip()
    if not project_name:
        project_name = "default_project"

    system_prompt = (
        "You are the SPARK Workspace Generator. Translate the user's coding request into a structured JSON manifest.\n"
        "You must return ONLY a valid raw JSON object. Do NOT wrap in Markdown code blocks, do NOT include conversational text.\n"
        "Format schema:\n"
        "{\n"
        '  "project_name": "string (no spaces)",\n'
        '  "frameworks": ["string (e.g. bootstrap, fontawesome, vanilla)"],\n'
        '  "block_locations": {\n'
        '    "header": "string description",\n'
        '    "content": "string description",\n'
        '    "footer": "string description"\n'
        '  },\n'
        '  "view_parameters": {\n'
        '    "theme": "string (dark or light)",\n'
        '    "viewport": "string"\n'
        '  },\n'
        '  "files": [\n'
        '    {\n'
        '      "path": "string (filename, e.g. index.html or style.css or app.js)",\n'
        '      "content": "string (full source code content)"\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Generate a complete, fully functioning and styled index.html page (and optionally CSS/JS) for the request."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Build a project named '{project_name}' for this prompt: '{prompt}'"}
    ]

    from core.spark_brain import _chat_completion, _local_chat_completion, client
    import asyncio

    llm_output = ""
    try:
        if client is not None:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: _chat_completion(messages, allow_tools=False))
            llm_output = (response.choices[0].message.content or "").strip()
        else:
            llm_output = await _local_chat_completion(messages)
    except Exception as exc:
        logger.warning(f"Groq failed in manifest generator, falling back to local: {exc}")
        try:
            llm_output = await _local_chat_completion(messages)
        except Exception as local_exc:
            logger.error(f"Local LLM fallback failed in manifest generator: {local_exc}")

    # Remove any Markdown code block backticks
    clean_json_str = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", llm_output, flags=re.DOTALL).strip()

    manifest: dict[str, Any] = {}
    try:
        manifest = json.loads(clean_json_str)
    except Exception as parse_exc:
        logger.warning(f"Failed to parse manifest JSON: {parse_exc}. Building default emergency manifest.")
        manifest = {
            "project_name": project_name,
            "frameworks": ["vanilla"],
            "block_locations": {"header": "Default Header", "content": "Default Content", "footer": "Default Footer"},
            "view_parameters": {"theme": "dark", "viewport": "width=device-width, initial-scale=1.0"},
            "files": [
                {
                    "path": "index.html",
                    "content": f"<!DOCTYPE html><html><head><title>{project_name}</title></head><body><h1>{project_name}</h1><p>Prompt: {prompt}</p></body></html>"
                }
            ]
        }

    # Verify project name matches target folder to prevent path traversal
    safe_proj_dir = verify_safe_path(project_name)
    safe_proj_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    files_list = manifest.get("files", [])
    if not isinstance(files_list, list):
        files_list = []

    for file_info in files_list:
        file_path = file_info.get("path", "")
        file_content = file_info.get("content", "")
        # Prevent traversal in filenames
        safe_file_path = verify_safe_path(safe_proj_dir / Path(file_path).name)
        safe_file_path.write_text(file_content, encoding="utf-8")
        created_files.append(str(safe_file_path.relative_to(SANDBOX_DIR)))

    # Trigger a non-blocking local shell call targeting only the index.html viewport pipe
    html_target = os.path.abspath(safe_proj_dir / "index.html")
    logger.info(f"Triggering non-blocking preview shell call for {html_target}")

    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer.exe", html_target])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", html_target])
        else:
            subprocess.Popen(["xdg-open", html_target])
        shell_triggered = True
    except Exception as shell_exc:
        logger.error(f"Failed to spawn non-blocking shell call: {shell_exc}")
        shell_triggered = False

    return {
        "status": "success",
        "project_name": project_name,
        "manifest": manifest,
        "created_files": created_files,
        "shell_triggered": shell_triggered,
        "html_preview_path": html_target
    }
