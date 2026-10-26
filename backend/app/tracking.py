"""Takip kodu üretimi ve özetleme."""
import hashlib
import re
import secrets

# 0/O, 1/I/l ve urlsafe'in '-' '_' karakterleri çıkarıldı.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
CODE_RE = re.compile(rf"^[{ALPHABET}]{{{CODE_LENGTH}}}$")


def generate_code() -> str:
    chars: list[str] = []
    while len(chars) < CODE_LENGTH:
        chars.extend(c for c in secrets.token_urlsafe(16).upper() if c in ALPHABET)
    return "".join(chars[:CODE_LENGTH])


def normalize_code(value: str) -> str | None:
    code = (value or "").strip().upper()
    return code if CODE_RE.match(code) else None


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()
