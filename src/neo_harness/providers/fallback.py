"""Provider failure fallback policy (mock vs fail-closed)."""

from __future__ import annotations

import os
from typing import Any

from neo_harness.providers.base import ReasoningProvider
from neo_harness.providers.mock import MockProvider

# Ellipsis means "use env default"
_ENV_DEFAULT: Any = ...


def fallback_mode() -> str:
    """Return ``mock`` (default) or ``none`` from env."""
    raw = (os.environ.get("NEO_PROVIDER_FALLBACK") or "mock").strip().lower()
    if raw in ("none", "off", "0", "false", "fail", "error"):
        return "none"
    return "mock"


def resolve_fallback(explicit: Any = _ENV_DEFAULT) -> ReasoningProvider | None:
    """Resolve fallback provider.

    Args:
        explicit: Provider instance, ``None`` (fail-closed), or omit for env default.

    Returns:
        MockProvider, custom provider, or None (fail-closed).
    """
    if explicit is not _ENV_DEFAULT:
        return explicit
    if fallback_mode() == "none":
        return None
    return MockProvider()


def raise_or_fallback(
    fallback: ReasoningProvider | None,
    *,
    provider_name: str,
    reason: str,
) -> ReasoningProvider:
    """Return fallback or raise if fail-closed."""
    if fallback is None:
        raise RuntimeError(
            f"{provider_name} failed ({reason}) and NEO_PROVIDER_FALLBACK=none "
            "(fail-closed). Fix provider/auth or set NEO_PROVIDER_FALLBACK=mock."
        )
    return fallback
