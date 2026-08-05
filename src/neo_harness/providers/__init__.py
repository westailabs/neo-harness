"""Reasoning providers — model is swappable; harness owns control flow."""

from __future__ import annotations

import os

from neo_harness.providers.base import ReasoningProvider
from neo_harness.providers.copilot import CopilotProvider
from neo_harness.providers.fallback import fallback_mode, resolve_fallback
from neo_harness.providers.grok_build import GrokBuildProvider
from neo_harness.providers.mock import MockProvider
from neo_harness.providers.status import ProviderStatus, probe_all
from neo_harness.providers.xai_api import XAIAPIProvider


def get_provider(name: str | None = None) -> ReasoningProvider:
    """Factory: mock | grok_build | copilot | xai (default: mock).

    Real providers honor ``NEO_PROVIDER_FALLBACK=mock|none`` (fail-closed).
    """
    # Ensure settings env is visible even if only set in Settings cache later
    key = (name or os.environ.get("NEO_PROVIDER") or "mock").lower().replace("-", "_")
    fb = resolve_fallback()
    if key in ("mock", "placeholder"):
        return MockProvider()
    if key in ("grok", "grok_build", "build"):
        return GrokBuildProvider(fallback=fb)
    if key in ("copilot", "gh_copilot", "github_copilot"):
        return CopilotProvider(fallback=fb)
    if key in ("xai", "xai_api", "api"):
        return XAIAPIProvider(fallback=fb)
    raise ValueError(
        f"Unknown provider: {name!r}. Use mock|grok_build|copilot|xai"
    )


__all__ = [
    "CopilotProvider",
    "GrokBuildProvider",
    "MockProvider",
    "ProviderStatus",
    "ReasoningProvider",
    "XAIAPIProvider",
    "fallback_mode",
    "get_provider",
    "probe_all",
    "resolve_fallback",
]
