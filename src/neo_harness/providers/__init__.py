"""Reasoning providers — model is swappable; harness owns control flow."""

from __future__ import annotations

from neo_harness.providers.base import ReasoningProvider
from neo_harness.providers.copilot import CopilotProvider
from neo_harness.providers.grok_build import GrokBuildProvider
from neo_harness.providers.mock import MockProvider
from neo_harness.providers.xai_api import XAIAPIProvider


def get_provider(name: str | None = None) -> ReasoningProvider:
    """Factory: mock | grok_build | copilot | xai (default: mock)."""
    key = (name or "mock").lower().replace("-", "_")
    if key in ("mock", "placeholder"):
        return MockProvider()
    if key in ("grok", "grok_build", "build"):
        return GrokBuildProvider()
    if key in ("copilot", "gh_copilot", "github_copilot"):
        return CopilotProvider()
    if key in ("xai", "xai_api", "api"):
        return XAIAPIProvider()
    raise ValueError(
        f"Unknown provider: {name!r}. Use mock|grok_build|copilot|xai"
    )


__all__ = [
    "CopilotProvider",
    "GrokBuildProvider",
    "MockProvider",
    "ReasoningProvider",
    "XAIAPIProvider",
    "get_provider",
]
