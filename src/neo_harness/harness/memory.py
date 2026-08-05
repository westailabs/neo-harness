"""Typed memory interfaces backed by Neo4j — Working, Episodic, Semantic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from neo_harness.neo4j import queries
from neo_harness.neo4j.client import Neo4jClient
from neo_harness.schemas.episode import Artifact, Decision, Episode, EpisodeKind
from neo_harness.schemas.reflection import Reflection
from neo_harness.schemas.session import Session
from neo_harness.security.secrets import redact_secrets, redact_structure


@runtime_checkable
class WorkingMemory(Protocol):
    """Short-horizon context: current goal + recent observations."""

    def get_goal(self) -> str | None: ...
    def set_goal(self, goal: str) -> None: ...
    def push_observation(self, text: str, *, meta: dict[str, Any] | None = None) -> None: ...
    def recent_observations(self, limit: int = 10) -> list[dict[str, Any]]: ...
    def clear_observations(self) -> None: ...
    def context_blob(self) -> dict[str, Any]: ...


@runtime_checkable
class EpisodicMemory(Protocol):
    """Timeline of past steps and sessions."""

    def append(self, episode: Episode) -> Episode: ...
    def list_for_session(self, session_id: str, *, limit: int = 50) -> list[Episode]: ...
    def store_reflection(self, reflection: Reflection) -> Reflection: ...


@runtime_checkable
class SemanticMemory(Protocol):
    """Stable facts, decisions, SOPs that survive sessions."""

    def add_decision(self, decision: Decision) -> Decision: ...
    def list_decisions(
        self, session_id: str | None = None, *, limit: int = 50
    ) -> list[Decision]: ...
    def add_artifact(self, artifact: Artifact) -> Artifact: ...
    def list_artifacts(self, session_id: str, *, limit: int = 50) -> list[Artifact]: ...
    def related(self, session_id: str, *, limit: int = 20) -> list[dict[str, Any]]: ...


@dataclass
class InMemoryWorkingMemory:
    """Process-local working memory (also mirrored to session node on flush)."""

    goal: str | None = None
    observations: list[dict[str, Any]] = field(default_factory=list)
    max_observations: int = 50

    def get_goal(self) -> str | None:
        return self.goal

    def set_goal(self, goal: str) -> None:
        self.goal = goal

    def push_observation(self, text: str, *, meta: dict[str, Any] | None = None) -> None:
        self.observations.append(
            {"text": redact_secrets(text), "meta": redact_structure(meta or {})}
        )
        if len(self.observations) > self.max_observations:
            self.observations = self.observations[-self.max_observations :]

    def recent_observations(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.observations[-limit:]

    def clear_observations(self) -> None:
        self.observations.clear()

    def context_blob(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "observations": self.recent_observations(10),
        }


class Neo4jEpisodicMemory:
    """Episodes and reflections persisted as Neo4j nodes."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    def append(self, episode: Episode) -> Episode:
        # Secret hygiene: never persist raw secrets into episodic memory
        episode.summary = redact_secrets(episode.summary)
        if isinstance(episode.content, dict):
            episode.content = redact_structure(episode.content)
        elif isinstance(episode.content, str):
            episode.content = redact_secrets(episode.content)
        queries.create_episode(self._client, episode)
        return episode

    def list_for_session(self, session_id: str, *, limit: int = 50) -> list[Episode]:
        return queries.list_episodes(self._client, session_id, limit=limit)

    def store_reflection(self, reflection: Reflection) -> Reflection:
        reflection.what_happened = redact_secrets(reflection.what_happened)
        if reflection.lessons:
            reflection.lessons = [redact_secrets(x) for x in reflection.lessons]
        queries.create_reflection(self._client, reflection)
        # Also mirror as an Episode for timeline queries.
        episode = Episode(
            session_id=reflection.session_id,
            kind=EpisodeKind.REFLECTION,
            state="REFLECT",
            summary=reflection.what_happened[:500],
            content=reflection.model_dump(mode="json"),
            success=reflection.next_action.value not in ("fail",),
            tags=["reflection", reflection.trigger.value],
        )
        self.append(episode)
        return reflection


class Neo4jSemanticMemory:
    """Decisions and artifacts — longer-lived knowledge."""

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    def add_decision(self, decision: Decision) -> Decision:
        decision.statement = redact_secrets(decision.statement)
        if decision.rationale:
            decision.rationale = redact_secrets(decision.rationale)
        queries.create_decision(self._client, decision)
        return decision

    def list_decisions(
        self, session_id: str | None = None, *, limit: int = 50
    ) -> list[Decision]:
        return queries.list_decisions(self._client, session_id=session_id, limit=limit)

    def add_artifact(self, artifact: Artifact) -> Artifact:
        queries.create_artifact(self._client, artifact)
        return artifact

    def list_artifacts(self, session_id: str, *, limit: int = 50) -> list[Artifact]:
        return queries.list_artifacts(self._client, session_id, limit=limit)

    def related(self, session_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return queries.related_knowledge(self._client, session_id, limit=limit)


@dataclass
class MemoryBundle:
    """Convenience bundle of the three memory layers."""

    working: InMemoryWorkingMemory
    episodic: Neo4jEpisodicMemory
    semantic: Neo4jSemanticMemory

    @classmethod
    def from_client(cls, client: Neo4jClient, *, goal: str | None = None) -> MemoryBundle:
        working = InMemoryWorkingMemory(goal=goal)
        return cls(
            working=working,
            episodic=Neo4jEpisodicMemory(client),
            semantic=Neo4jSemanticMemory(client),
        )

    def hydrate_working_from_session(self, session: Session) -> None:
        self.working.set_goal(session.goal or session.task)
