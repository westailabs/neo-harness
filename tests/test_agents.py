"""Agent pack discovery and system-prompt composition."""

from __future__ import annotations

from pathlib import Path

import pytest

from neo_harness.agents.loader import list_agents, load_agent
from neo_harness.harness.loop import HarnessLoop
from neo_harness.providers.mock import MockProvider


def test_list_agents_includes_sysadmin() -> None:
    packs = list_agents()
    ids = {p.id for p in packs}
    assert "sysadmin" in ids


def test_load_sysadmin_uses_short_persona() -> None:
    agent = load_agent("sysadmin")
    assert agent is not None
    assert agent.name == "SysAdmin Agent"
    assert "wsl-shurtugal" in agent.target_repos
    plan = agent.system_for("plan")
    act = agent.system_for("act")
    reflect = agent.system_for("reflect")
    assert "SysAdmin" in plan or "workstation" in plan.lower() or "IaC" in plan
    assert "Ansible" in act or "ansible" in act.lower()
    assert "next_action" in reflect or "replan" in reflect
    # Short persona, not full AGENT.md novel
    assert "AGENT (" in plan
    assert len(plan) < 4000
    assert agent.persona_full  # full still available for humans
    assert len(agent.persona) < len(agent.persona_full)


def test_load_agent_none() -> None:
    assert load_agent(None) is None
    assert load_agent("") is None


def test_load_agent_missing() -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        load_agent("definitely-not-a-real-agent-pack")


def test_loop_uses_agent_system(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock provider records system prompts; agent must appear in plan system."""
    agent = load_agent("sysadmin")
    assert agent is not None

    systems: list[str] = []
    real_plan = MockProvider.plan

    async def capture_plan(self, *, system: str, prompt: str, session_id: str):
        systems.append(system)
        return await real_plan(self, system=system, prompt=prompt, session_id=session_id)

    monkeypatch.setattr(MockProvider, "plan", capture_plan)

    from unittest.mock import MagicMock

    from neo_harness.harness.budget import Budget
    from neo_harness.harness.memory import InMemoryWorkingMemory, MemoryBundle
    from neo_harness.schemas.session import HarnessState, Session

    class FakeEpisodic:
        def append(self, episode):
            return episode

        def list_for_session(self, session_id, *, limit=50):
            return []

        def store_reflection(self, reflection):
            return reflection

    class FakeSemantic:
        def add_decision(self, decision):
            return decision

        def list_decisions(self, session_id=None, *, limit=50):
            return []

        def add_artifact(self, artifact):
            return artifact

        def list_artifacts(self, session_id, *, limit=50):
            return []

        def related(self, session_id, *, limit=20):
            return []

    client = MagicMock()
    memory = MemoryBundle(
        working=InMemoryWorkingMemory(goal="test"),
        episodic=FakeEpisodic(),  # type: ignore[arg-type]
        semantic=FakeSemantic(),  # type: ignore[arg-type]
    )
    session = Session(task="Add a package", state=HarnessState.INIT)
    loop = HarnessLoop(
        client=client,
        provider=MockProvider(),
        memory=memory,
        budget=Budget(max_steps=5),
        max_iterations=1,
        agent=agent,
    )

    monkeypatch.setattr(loop, "_persist_session", lambda s: None)
    monkeypatch.setattr(
        "neo_harness.harness.loop.queries.upsert_session",
        lambda *a, **k: None,
    )

    import asyncio

    asyncio.run(loop.run(session, steps=1))
    assert systems, "expected at least one plan() call"
    assert "SysAdmin" in systems[0] or "AGENT (" in systems[0]
    assert len(systems[0]) < 5000


def test_agent_search_respects_neo_agents_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = tmp_path / "custom-ops"
    pack.mkdir()
    (pack / "AGENT.md").write_text("# Custom Ops\n\nTest pack.\n", encoding="utf-8")
    (pack / "prompts").mkdir()
    (pack / "prompts" / "plan.md").write_text("Custom plan system.", encoding="utf-8")
    monkeypatch.setenv("NEO_AGENTS_DIR", str(tmp_path))
    agent = load_agent("custom-ops")
    assert agent is not None
    assert "Custom plan system" in agent.system_for("plan")


def test_provider_cwd_agents_preferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Workspace embed: NEO_PROVIDER_CWD/agents wins over NEO_AGENTS_DIR."""
    cwd_agents = tmp_path / "workspace" / "agents" / "ws-agent"
    cwd_agents.mkdir(parents=True)
    (cwd_agents / "AGENT.md").write_text("# WS\n", encoding="utf-8")
    (cwd_agents / "prompts").mkdir()
    (cwd_agents / "prompts" / "plan.md").write_text("FROM_CWD", encoding="utf-8")

    other = tmp_path / "other"
    other.mkdir()
    pack = other / "ws-agent"
    pack.mkdir()
    (pack / "AGENT.md").write_text("# Other\n", encoding="utf-8")
    (pack / "prompts").mkdir()
    (pack / "prompts" / "plan.md").write_text("FROM_OTHER", encoding="utf-8")

    monkeypatch.setenv("NEO_PROVIDER_CWD", str(tmp_path / "workspace"))
    monkeypatch.setenv("NEO_AGENTS_DIR", str(other))
    agent = load_agent("ws-agent")
    assert agent is not None
    assert "FROM_CWD" in agent.system_for("plan")
