"""Secret redaction for prompts and episodic memory (defense in depth)."""

from __future__ import annotations

import re
from typing import Any

# Patterns that commonly appear in agent traces; keep conservative replacements.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OpenAI / similar
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bsk-proj-[A-Za-z0-9_\-]{16,}\b"), "[REDACTED_API_KEY]"),
    # GitHub
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    # xAI / generic bearer-ish
    (re.compile(r"\bxai-[A-Za-z0-9_\-]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer [REDACTED_TOKEN]"),
    # Env-style assignments for high-risk keys
    (
        re.compile(
            r"(?i)\b(NEO4J_PASSWORD|PASSWORD|SECRET|API_KEY|TOKEN|PRIVATE_KEY)"
            r"\s*[=:]\s*['\"]?([^\s'\"]+)"
        ),
        r"\1=[REDACTED]",
    ),
    # PEM blocks
    (
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


def redact_secrets(text: str | None) -> str:
    """Return ``text`` with high-risk secrets replaced."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    out = text
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    return out


def redact_structure(value: Any) -> Any:
    """Recursively redact strings in dict/list structures."""
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {k: redact_structure(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_structure(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_structure(v) for v in value)
    return value
