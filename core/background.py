"""
core/background.py — S.P.A.R.K. Contextual Agency Watcher
Monitors the system clipboard in a background thread.
When a trigger pattern is detected (URL, code snippet, file path, etc.),
SPARK silently queries the LLM and optionally speaks first.
Creates the illusion of continuous presence.
"""

import re
import time
import logging
import threading
import requests

logger = logging.getLogger(__name__)

# ── Trigger patterns ────────────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r'(https?://[^\s]+|(?:www\.)?'
    r'(?:github|gitlab|stackoverflow|npmjs|pypi|docs)\.[a-z]{2,}[^\s]*)',
    re.IGNORECASE
)
CODE_SNIPPET_PATTERN = re.compile(
    r'(def |class |import |#include|function |const |let |var |SELECT |FROM )',
    re.IGNORECASE
)
FILE_PATH_PATTERN = re.compile(
    r'([A-Za-z]:\\[^\n]+\.[a-zA-Z]{2,5}|/(?:home|usr|var|etc|mnt)/[^\n]+)',
)

# ── Config ───────────────────────────────────────────────────────────────────
POLL_INTERVAL = 1.5          # seconds between clipboard checks
COOLDOWN_SECONDS = 30        # don't re-trigger on same content for N seconds
MIN_CONTENT_LENGTH = 10      # ignore tiny clips

_running = False
_last_clip = ""
_last_trigger_time = 0.0
_voice_ref = None
_llm_query_fn = None          # Injected from main.py: fn(prompt) -> str


def _detect_type(text: str) -> str | None:
    """Returns a trigger category string or None if not interesting."""
    if URL_PATTERN.search(text):
        return "url"
    if FILE_PATH_PATTERN.search(text):
        return "filepath"
    if CODE_SNIPPET_PATTERN.search(text) and len(text) > 40:
        return "code"
    return None


def _get_clipboard() -> str:
    """Cross-platform clipboard read with graceful fallback."""
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception:
        return ""


def _broadcast_hud(event_type: str, payload: dict):
    """Fire and forget HUD broadcast."""
    def _send():
        try:
            requests.post(
                "http://127.0.0.1:8000/internal/broadcast",
                json={"type": event_type, "payload": payload},
                timeout=0.5
            )
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


def _handle_trigger(clip_text: str, trigger_type: str):
    """
    Core logic when a clipboard trigger fires.
    1. Build a contextual prompt for the LLM.
    2. Let the LLM decide whether to offer help.
    3. If yes, SPARK speaks and sends HUD notification.
    """
    logger.info(f"[BACKGROUND] Trigger detected: type={trigger_type}, preview={clip_text[:80]}")

    # Build intent-check prompt
    if trigger_type == "url":
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', clip_text)
        domain = domain_match.group(1) if domain_match else clip_text[:60]
        prompt = (
            f"The user just copied this URL to their clipboard: {clip_text[:200]}\n"
            f"Domain: {domain}\n"
            f"In one SHORT sentence (max 15 words), offer ONE specific, useful action "
            f"(e.g. 'Shall I clone it?', 'Want me to summarize the README?', "
            f"'Should I fetch the page content?'). "
            f"If it's not actionable (e.g. social media, shopping), respond with exactly: SKIP\n"
            f"Respond only with the offer sentence or SKIP."
        )
    elif trigger_type == "filepath":
        prompt = (
            f"The user copied a file path: {clip_text[:200]}\n"
            f"Offer ONE specific action in max 15 words "
            f"(e.g. 'Shall I open and summarize that file?'). "
            f"Respond only with the offer or SKIP."
        )
    elif trigger_type == "code":
        lang_hint = ""
        if "def " in clip_text or "import " in clip_text:
            lang_hint = "Python"
        elif "function " in clip_text or "const " in clip_text:
            lang_hint = "JavaScript"
        elif "#include" in clip_text:
            lang_hint = "C/C++"
        elif "SELECT " in clip_text.upper():
            lang_hint = "SQL"
        prompt = (
            f"The user copied a {lang_hint} code snippet ({len(clip_text)} chars).\n"
            f"Snippet preview: {clip_text[:150]}\n"
            f"Offer ONE specific action in max 15 words "
            f"(e.g. 'Shall I review and explain this code?', 'Want me to debug this?'). "
            f"Respond only with the offer or SKIP."
        )
    else:
        return

    # Query LLM
    offer = None
    if _llm_query_fn:
        try:
            raw = _llm_query_fn(prompt).strip()
            if raw and raw.upper() != "SKIP" and len(raw) > 5:
                offer = raw
        except Exception as e:
            logger.warning(f"[BACKGROUND] LLM query failed: {e}")
            # Fallback hardcoded offer
            if trigger_type == "url":
                offer = "I see you copied a URL. Shall I summarize it for you, sir?"
            elif trigger_type == "code":
                offer = "I see you copied a code snippet. Shall I review it?"
    else:
        # No LLM injected, use hardcoded offers
        offers_map = {
            "url": f"I see you copied a URL. Shall I fetch and summarize it, sir?",
            "filepath": f"I see you copied a file path. Shall I read and analyze it, sir?",
            "code": f"I see you copied a code snippet. Shall I review or explain it, sir?"
        }
        offer = offers_map.get(trigger_type)

    if not offer:
        return

    # Broadcast to HUD
    _broadcast_hud("clipboard_assist", {
        "trigger_type": trigger_type,
        "content_preview": clip_text[:100],
        "offer": offer
    })

    # Speak proactively
    if _voice_ref:
        def _speak():
            try:
                _voice_ref.speak(offer)
            except Exception as e:
                logger.warning(f"[BACKGROUND] Speak failed: {e}")
        threading.Thread(target=_speak, daemon=True).start()

    logger.info(f"[BACKGROUND] Offered: {offer}")


def _watcher_loop():
    """Main polling loop — runs in a daemon thread."""
    global _last_clip, _last_trigger_time

    logger.info("[BACKGROUND] Clipboard watcher started.")
    while _running:
        try:
            clip = _get_clipboard().strip()

            # Ignore empty, short, or unchanged content
            if (
                not clip
                or len(clip) < MIN_CONTENT_LENGTH
                or clip == _last_clip
            ):
                time.sleep(POLL_INTERVAL)
                continue

            # Cooldown check (same clip seen recently)
            now = time.time()
            if clip == _last_clip and (now - _last_trigger_time) < COOLDOWN_SECONDS:
                time.sleep(POLL_INTERVAL)
                continue

            _last_clip = clip

            trigger_type = _detect_type(clip)
            if trigger_type:
                _last_trigger_time = now
                # Run handler in its own thread so watcher never blocks
                threading.Thread(
                    target=_handle_trigger,
                    args=(clip, trigger_type),
                    daemon=True
                ).start()

        except Exception as e:
            logger.warning(f"[BACKGROUND] Watcher loop error: {e}")

        time.sleep(POLL_INTERVAL)

    logger.info("[BACKGROUND] Clipboard watcher stopped.")


def start_watcher(voice=None, llm_query_fn=None):
    """
    Start the background clipboard watcher daemon.
    Call once from main.py during boot.

    voice:         SparkVoice instance for proactive speech.
    llm_query_fn:  fn(prompt: str) -> str  — lightweight LLM call for intent check.
    """
    global _running, _voice_ref, _llm_query_fn

    if _running:
        logger.warning("[BACKGROUND] Watcher already running.")
        return

    # Check pyperclip availability
    try:
        import pyperclip
        pyperclip.paste()  # test access
    except Exception as e:
        logger.warning(f"[BACKGROUND] pyperclip not available ({e}). Watcher disabled.")
        return

    _voice_ref = voice
    _llm_query_fn = llm_query_fn
    _running = True

    t = threading.Thread(target=_watcher_loop, daemon=True, name="spark-clipboard-watcher")
    t.start()
    logger.info("[BACKGROUND] ✅ Contextual agency watcher started.")


def stop_watcher():
    """Stop the clipboard watcher thread."""
    global _running
    _running = False
    logger.info("[BACKGROUND] Watcher stop signal sent.")
