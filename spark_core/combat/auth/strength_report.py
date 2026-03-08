"""
Password Strength / Hash-File Analyst
=======================================
Analyses a hash dump file for density estimations and policy violations.
NEVER handles or stores plaintext passwords — only inspects hash formats.
"""
import re
import logging
from pathlib import Path
from typing import TypedDict, List

log = logging.getLogger(__name__)

# Common NTLM "empty" hashes that indicate blank passwords
_BLANK_NTLM = {"31d6cfe0d16ae931b73c59d7e0c089c0"}  # lower-case hash of empty string

_HASH_SIGNATURES: list = [
    (r"^[0-9a-f]{32}$",                       "MD5 / NTLM (32 hex)"),
    (r"^[0-9a-f]{40}$",                        "SHA-1 (40 hex)"),
    (r"^[0-9a-f]{64}$",                        "SHA-256 (64 hex)"),
    (r"^\$2[aby]\$",                           "bcrypt"),
    (r"^\$S\$",                                "Drupal SHA-512"),
    (r"^\$P\$",                                "phpass (WordPress)"),
    (r"^[A-Za-z0-9+/]{43}=$",                 "SHA-256 base64"),
    (r"^[0-9a-f]{32}:[0-9a-f]+$",             "NTLM (user:hash)"),
    (r"^[^:]+:[^:]+:[0-9a-f]{32}:[0-9a-f]{32}:", "NTLM full SAM dump"),
]


class StrengthReport(TypedDict):
    file_path:          str
    total_hashes:       int
    detected_format:    str
    blank_passwords:    int         # hashes matching known blank-password values
    policy_violations:  int         # any hash known to be trivially crackable
    unique_hashes:      int
    duplicate_count:    int
    risk_level:         str   # LOW | MEDIUM | HIGH | CRITICAL
    recommendations:    List[str]


def analyze_hash_file(file_path: str) -> StrengthReport:
    """
    Read a hash file and produce a StrengthReport.
    Works entirely on hash values — no plaintext is ever read or stored.
    """
    path = Path(file_path)
    if not path.exists():
        return StrengthReport(
            file_path=file_path, total_hashes=0, detected_format="FILE_NOT_FOUND",
            blank_passwords=0, policy_violations=0, unique_hashes=0,
            duplicate_count=0, risk_level="UNKNOWN", recommendations=[],
        )

    hashes: List[str] = []
    detected_format = "UNKNOWN"

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        hashes = lines

        # Detect format from first non-empty line
        for pattern, label in _HASH_SIGNATURES:
            if lines and re.match(pattern, lines[0], re.I):
                detected_format = label
                break

    except Exception as exc:
        log.error("analyze_hash_file error: %s", exc)

    total       = len(hashes)
    unique      = len(set(h.lower() for h in hashes))
    duplicates  = total - unique
    blanks      = sum(1 for h in hashes if h.lower() in _BLANK_NTLM)

    # Policy violations: blank passwords are always violations
    violations  = blanks

    # Risk heuristic
    if blanks > 0 or (total > 0 and duplicates / total > 0.3):
        risk = "CRITICAL"
    elif duplicates > 0 or total > 1000:
        risk = "HIGH"
    elif total > 100:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    recs: List[str] = []
    if blanks > 0:
        recs.append(f"Force password reset for {blanks} account(s) with blank passwords.")
    if duplicates > 0:
        recs.append(f"{duplicates} duplicate hashes found — shared passwords in use.")
    if detected_format in ("MD5 / NTLM (32 hex)", "SHA-1 (40 hex)"):
        recs.append("Hash algorithm is weak. Migrate to bcrypt / Argon2 immediately.")
    if not recs:
        recs.append("No immediate red flags — continue monitoring.")

    return StrengthReport(
        file_path         = str(path),
        total_hashes      = total,
        detected_format   = detected_format,
        blank_passwords   = blanks,
        policy_violations = violations,
        unique_hashes     = unique,
        duplicate_count   = duplicates,
        risk_level        = risk,
        recommendations   = recs,
    )
