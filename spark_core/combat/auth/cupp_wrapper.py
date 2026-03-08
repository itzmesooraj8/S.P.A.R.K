"""
CUPP (Common User Password Profiler) Wrapper
=============================================
Generates targeted wordlists from user-profile data.
Requires: CUPP — https://github.com/Mebus/cupp (pip install cupp OR clone)

IMPORTANT: Only generate wordlists for accounts you own or have written
           authorisation to audit.  Never store or transmit plaintext credentials.
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_WORDLISTS_DIR = Path(__file__).parent / "wordlists"
_WORDLISTS_DIR.mkdir(exist_ok=True)


class ProfileData:
    """User-facing profile for wordlist generation (no passwords — inputs only)."""
    def __init__(
        self,
        first_name: str = "",
        last_name: str  = "",
        nickname: str   = "",
        birthdate: str  = "",       # DDMMYYYY
        partner: str    = "",
        pet_name: str   = "",
        company: str    = "",
        keywords: list  = None,
    ):
        self.first_name = first_name.strip()[:64]
        self.last_name  = last_name.strip()[:64]
        self.nickname   = nickname.strip()[:64]
        self.birthdate  = birthdate.strip()[:8]
        self.partner    = partner.strip()[:64]
        self.pet_name   = pet_name.strip()[:64]
        self.company    = company.strip()[:64]
        self.keywords   = [k.strip()[:64] for k in (keywords or [])][:20]


async def generate_wordlist(profile: ProfileData, output_name: str = "") -> dict:
    """
    Generate a targeted wordlist using CUPP interactive mode (piped stdin).
    Returns {"wordlist_path", "line_count", "status"}.
    """
    import uuid
    out_name = (output_name or f"cupp_{str(uuid.uuid4())[:8]}") + ".txt"
    out_path = str(_WORDLISTS_DIR / out_name)

    # CUPP interactive mode answers
    answers = [
        profile.first_name or " ",
        profile.last_name  or " ",
        profile.nickname   or " ",
        profile.birthdate  or " ",
        profile.partner    or " ",
        "",  # partner DOB
        profile.pet_name   or " ",
        profile.company    or " ",
        " ".join(profile.keywords) if profile.keywords else " ",
        "n",   # no special words file
        "y",   # leet mode
        "y",   # generate
    ]
    stdin_input = "\n".join(answers) + "\n"

    try:
        proc = await asyncio.create_subprocess_exec(
            "cupp", "-i",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(_WORDLISTS_DIR),
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(input=stdin_input.encode()),
            timeout=120,
        )
        output = stdout.decode("utf-8", errors="replace")

        # CUPP writes to <firstname>.txt in cwd — find and rename
        generated = _find_cupp_output(str(_WORDLISTS_DIR), profile.first_name)
        if generated and os.path.exists(generated):
            os.rename(generated, out_path)

        line_count = _count_lines(out_path)
        return {"wordlist_path": out_path, "line_count": line_count, "status": "COMPLETE"}

    except FileNotFoundError:
        log.warning("CUPP not found — generating basic wordlist")
        line_count = _build_basic_wordlist(profile, out_path)
        return {"wordlist_path": out_path, "line_count": line_count, "status": "BASIC_FALLBACK"}
    except asyncio.TimeoutError:
        return {"wordlist_path": "", "line_count": 0, "status": "TIMEOUT"}
    except Exception as exc:
        log.error("CUPP error: %s", exc)
        return {"wordlist_path": "", "line_count": 0, "status": "ERROR", "message": str(exc)}


def _find_cupp_output(directory: str, first_name: str) -> Optional[str]:
    """CUPP typically writes <FirstName>.txt"""
    candidates = [
        os.path.join(directory, f"{first_name}.txt"),
        os.path.join(directory, f"{first_name.lower()}.txt"),
        os.path.join(directory, f"{first_name.capitalize()}.txt"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _build_basic_wordlist(profile: ProfileData, out_path: str) -> int:
    """Fallback: build a minimal wordlist from profile tokens without CUPP."""
    tokens = [
        profile.first_name, profile.last_name, profile.nickname,
        profile.partner, profile.pet_name, profile.company,
        profile.birthdate,
    ] + profile.keywords
    tokens = [t for t in tokens if t]

    words = set()
    for t in tokens:
        words.add(t)
        words.add(t.lower())
        words.add(t.capitalize())
        words.add(t.upper())
        words.add(t + "123")
        words.add(t + "!")
        words.add(t + "2024")
        words.add(t + "2023")
        # Combine pairs
        for t2 in tokens:
            if t2 != t:
                words.add(t + t2)
                words.add(t.lower() + t2.lower())

    with open(out_path, "w", encoding="utf-8") as f:
        for w in sorted(words):
            f.write(w + "\n")

    return len(words)
