"""Low-priority worker script executed by WorkerSupervisor for isolated workspace previews."""

import json
import os
import sys
import subprocess
from pathlib import Path

SANDBOX_DIR = Path("sandbox").resolve()

def verify_safe_path(path: str | Path) -> Path:
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    p = Path(path)
    if p.is_absolute():
        target = p.resolve()
    else:
        target = (SANDBOX_DIR / p).resolve()
            
    if target != SANDBOX_DIR and SANDBOX_DIR not in target.parents:
        raise PermissionError(f"Security Violation: Path is outside sandbox.")
    return target

def main() -> None:
    if len(sys.argv) < 4:
        sys.exit(1)

    project_name = sys.argv[1]
    html_target = sys.argv[2]
    manifest_str = sys.argv[3]

    try:
        manifest = json.loads(manifest_str)
    except Exception:
        sys.exit(2)

    # Write files under sandbox
    safe_proj_dir = verify_safe_path(project_name)
    safe_proj_dir.mkdir(parents=True, exist_ok=True)

    files_list = manifest.get("files", [])
    for file_info in files_list:
        file_path = file_info.get("path", "")
        file_content = file_info.get("content", "")
        # Prevent traversal in filenames
        safe_file_path = verify_safe_path(safe_proj_dir / Path(file_path).name)
        safe_file_path.write_text(file_content, encoding="utf-8")

    # Trigger a preview process
    try:
        # Since this script runs under BELOW_NORMAL_PRIORITY_CLASS,
        # any processes it spawns will inherit the same low priority!
        if sys.platform == "win32":
            subprocess.Popen(["explorer.exe", html_target])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", html_target])
        else:
            subprocess.Popen(["xdg-open", html_target])
    except Exception:
        sys.exit(3)

if __name__ == "__main__":
    main()
