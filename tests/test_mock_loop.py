"""In-memory loop smoke test with mock provider (no Neo4j required for pure SM path).

Uses a lightweight fake client so PLAN→ACT→REFLECT can be exercised without Bolt.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from neo_harness.harness.budget import Budget
from neo_harness.harness.loop import HarnessLoop
from neo_harness.harness.memory import InMemoryWorkingMemory, MemoryBundle
from neo_harness.providers.mock import MockProvider
from neo_harness.schemas.episode import Episode
from neo_harness.schemas.reflection import Reflection
from neo_harness.schemas.session import HarnessState, Session


class FakeEpisodic:
    def __init__(self) -> None:
        self.episodes: list[Episode] = []
        self.reflections: list[Reflection] = []

    def append(self, episode: Episode) -> Episode:
        self.episodes.append(episode)
        return episode

    def list_for_session(self, session_id: str, *, limit: int = 50) -> list[Episode]:
        return [e for e in self.episodes if e.session_id == session_id][:limit]

    def store_reflection(self, reflection: Reflection) -> Reflection:
        self.reflections.append(reflection)
        # mirror as episode like real impl
        from neo_harness.schemas.episode import EpisodeKind

        self.append(
            Episode(
                session_id=reflection.session_id,
                kind=EpisodeKind.REFLECTION,
                state="REFLECT",
                summary=reflection.what_happened,
                content=reflection.model_dump(mode="json"),
            )
        )
        return reflection


class FakeSemantic:
    def add_decision(self, decision: Any) -> Any:
        return decision

    def list_decisions(self, session_id: str | None = None, *, limit: int = 50) -> list:
        return []

    def add_artifact(self, artifact: Any) -> Any:
        return artifact

    def list_artifacts(self, session_id: str, *, limit: int = 50) -> list:
        return []

    def related(self, session_id: str, *, limit: int = 20) -> list:
        return []


@pytest.fixture
def fake_client() -> MagicMock:
    client = MagicMock()
    client.write = MagicMock(return_value=[])
    client.read = MagicMock(return_value=[])
    client.run = MagicMock(return_value=[])
    return client


def test_mock_loop_reaches_done(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    # Bypass Neo4j query helpers used by _persist_session / create_episode paths
    # by patching queries.upsert_session and using our fake memory bundle.
    from neo_harness.neo4j import queries as q

    monkeypatch.setattr(q, "upsert_session", lambda client, session: session)
    monkeypatch.setattr(q, "create_episode", lambda client, ep: ep)
    monkeypatch.setattr(q, "create_reflection", lambda client, r: r)
    monkeypatch.setattr(q, "create_decision", lambda client, d: d)

    session = Session(task="Verify mock PLAN→ACT→REFLECT loop")
    memory = MemoryBundle(
        working=InMemoryWorkingMemory(goal=session.task),
        episodic=FakeEpisodic(),  # type: ignore[arg-type]
        semantic=FakeSemantic(),  # type: ignore[arg-type]
    )
    loop = HarnessLoop(
        client=fake_client,
        provider=MockProvider(),
        memory=memory,
        budget=Budget(max_steps=30, reflect_every_n_actions=3),
        max_iterations=25,
    )
    result = asyncio.run(loop.run(session))
    assert result.error is None
    assert result.final_state in (HarnessState.DONE, HarnessState.ACT, HarnessState.OBSERVE, HarnessState.REFLECT, HarnessState.PLAN)
    # With mock, 3 steps + reflections should finish as DONE within 25 iters
    assert result.final_state == HarnessState.DONE, result.history
    assert result.session.action_count >= 3
    assert any("PLAN" in h for h in result.history)
    assert any("REFLECT" in h for h in result.history)
