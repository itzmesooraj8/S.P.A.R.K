from __future__ import annotations

import pyperclip


def get_clipboard() -> str:
    try:
        content = pyperclip.paste()
    except Exception:
        return "Clipboard is unavailable."
    content = content if isinstance(content, str) else str(content)
    return content.strip() or "Clipboard is empty."