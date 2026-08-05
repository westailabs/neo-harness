"""Provider status probes and fallback policy."""

from __future__ import annotations

import asyncio

import pytest

from neo_harness.providers.fallback import fallback_mode, raise_or_fallback, resolve_fallback
from neo_harness.providers.grok_build import GrokBuildProvider
from neo_harness.providers.mock import MockProvider
from neo_harness.providers.status import probe_all, probe_mock
from neo_harness.schemas.plan import PlanStep


def test_probe_mock_always_ready() -> None:
    st = probe_mock()
    assert st.available is True
    assert st.name == "mock"


def test_probe_all_has_four() -> None:
    names = {s.name for s in probe_all()}
    assert names == {"mock", "grok_build", "copilot", "xai"}


def test_fallback_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEO_PROVIDER_FALLBACK", "none")
    assert fallback_mode() == "none"
    assert resolve_fallback() is None
    monkeypatch.setenv("NEO_PROVIDER_FALLBACK", "mock")
    assert isinstance(resolve_fallback(), MockProvider)


def test_raise_or_fallback_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="fail-closed"):
        raise_or_fallback(None, provider_name="x", reason="boom")


def test_grok_fail_closed_without_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEO_PROVIDER_FALLBACK", "none")
    monkeypatch.setenv("GROK_BUILD_CMD", "definitely-not-a-real-grok-binary-xyz")
    p = GrokBuildProvider(fallback=None)
    assert p.available is False

    async def _run() -> None:
        await p.plan(system="s", prompt="task", session_id="sid")

    with pytest.raises(RuntimeError, match="fail-closed"):
        asyncio.run(_run())


def test_grok_soft_fallback_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROK_BUILD_CMD", "definitely-not-a-real-grok-binary-xyz")
    p = GrokBuildProvider(fallback=MockProvider())
    plan = asyncio.run(p.plan(system="s", prompt="do things", session_id="sid"))
    assert plan.steps
    act = asyncio.run(
        p.act(
            system="s",
            prompt="go",
            session_id="sid",
            step=PlanStep(index=0, description="step"),
        )
    )
    assert "summary" in act
