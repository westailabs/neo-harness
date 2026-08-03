"""Cypher helpers for session / episode / reflection CRUD."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from neo_harness.neo4j.client import Neo4jClient
from neo_harness.schemas.episode import Artifact, Decision, Episode, EpisodeKind
from neo_harness.schemas.reflection import NextAction, Reflection, ReflectionTrigger
from neo_harness.schemas.session import HarnessState, Session, SessionStatus


def _dt(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return default if default is not None else {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default if default is not None else {}
    return value


def _session_from_node(props: dict[str, Any]) -> Session:
    return Session(
        id=props["id"],
        task=props["task"],
        status=SessionStatus(props.get("status", "active")),
        state=HarnessState(props.get("state", "INIT")),
        goal=props.get("goal"),
        step_count=int(props.get("step_count") or 0),
        action_count=int(props.get("action_count") or 0),
        reflection_count=int(props.get("reflection_count") or 0),
        created_at=props.get("created_at") or datetime.utcnow(),
        updated_at=props.get("updated_at") or datetime.utcnow(),
        ended_at=props.get("ended_at"),
        metadata=_loads(props.get("metadata"), {}),
        last_error=props.get("last_error"),
    )


def upsert_session(client: Neo4jClient, session: Session) -> Session:
    client.write(
        """
        MERGE (s:Session {id: $id})
        SET s.task = $task,
            s.status = $status,
            s.state = $state,
            s.goal = $goal,
            s.step_count = $step_count,
            s.action_count = $action_count,
            s.reflection_count = $reflection_count,
            s.created_at = $created_at,
            s.updated_at = $updated_at,
            s.ended_at = $ended_at,
            s.metadata = $metadata,
            s.last_error = $last_error
        RETURN s
        """,
        id=session.id,
        task=session.task,
        status=session.status.value,
        state=session.state.value,
        goal=session.goal,
        step_count=session.step_count,
        action_count=session.action_count,
        reflection_count=session.reflection_count,
        created_at=_dt(session.created_at),
        updated_at=_dt(session.updated_at),
        ended_at=_dt(session.ended_at),
        metadata=json.dumps(session.metadata),
        last_error=session.last_error,
    )
    return session


def get_session(client: Neo4jClient, session_id: str) -> Session | None:
    rows = client.read(
        "MATCH (s:Session {id: $id}) RETURN s",
        id=session_id,
    )
    if not rows:
        return None
    node = rows[0]["s"]
    props = dict(node) if hasattr(node, "items") else node
    return _session_from_node(props)


def get_active_session(client: Neo4jClient) -> Session | None:
    """Most recently updated active/paused/blocked session."""
    rows = client.read(
        """
        MATCH (s:Session)
        WHERE s.status IN ['active', 'paused', 'blocked']
        RETURN s
        ORDER BY s.updated_at DESC
        LIMIT 1
        """
    )
    if not rows:
        return None
    node = rows[0]["s"]
    props = dict(node) if hasattr(node, "items") else node
    return _session_from_node(props)


def list_sessions(client: Neo4jClient, *, limit: int = 20) -> list[Session]:
    rows = client.read(
        """
        MATCH (s:Session)
        RETURN s
        ORDER BY s.updated_at DESC
        LIMIT $limit
        """,
        limit=limit,
    )
    out: list[Session] = []
    for row in rows:
        node = row["s"]
        props = dict(node) if hasattr(node, "items") else node
        out.append(_session_from_node(props))
    return out


def create_episode(client: Neo4jClient, episode: Episode) -> Episode:
    client.write(
        """
        MATCH (s:Session {id: $session_id})
        CREATE (e:Episode {
            id: $id,
            session_id: $session_id,
            kind: $kind,
            state: $state,
            summary: $summary,
            content: $content,
            step_index: $step_index,
            success: $success,
            created_at: $created_at,
            tags: $tags
        })
        CREATE (s)-[:HAS_EPISODE]->(e)
        RETURN e
        """,
        id=episode.id,
        session_id=episode.session_id,
        kind=episode.kind.value,
        state=episode.state,
        summary=episode.summary,
        content=json.dumps(episode.content),
        step_index=episode.step_index,
        success=episode.success,
        created_at=_dt(episode.created_at),
        tags=episode.tags,
    )
    return episode


def list_episodes(
    client: Neo4jClient, session_id: str, *, limit: int = 50
) -> list[Episode]:
    rows = client.read(
        """
        MATCH (s:Session {id: $session_id})-[:HAS_EPISODE]->(e:Episode)
        RETURN e
        ORDER BY e.created_at ASC, e.step_index ASC
        LIMIT $limit
        """,
        session_id=session_id,
        limit=limit,
    )
    episodes: list[Episode] = []
    for row in rows:
        node = row["e"]
        p = dict(node) if hasattr(node, "items") else node
        episodes.append(
            Episode(
                id=p["id"],
                session_id=p["session_id"],
                kind=EpisodeKind(p["kind"]),
                state=p.get("state", "INIT"),
                summary=p["summary"],
                content=_loads(p.get("content"), {}),
                step_index=int(p.get("step_index") or 0),
                success=bool(p.get("success", True)),
                created_at=p.get("created_at") or datetime.utcnow(),
                tags=list(p.get("tags") or []),
            )
        )
    return episodes


def create_reflection(client: Neo4jClient, reflection: Reflection) -> Reflection:
    client.write(
        """
        MATCH (s:Session {id: $session_id})
        CREATE (r:Reflection {
            id: $id,
            session_id: $session_id,
            trigger: $trigger,
            what_happened: $what_happened,
            what_worked: $what_worked,
            what_failed: $what_failed,
            lessons: $lessons,
            decisions: $decisions,
            open_questions: $open_questions,
            next_action: $next_action,
            confidence: $confidence,
            created_at: $created_at,
            metadata: $metadata
        })
        CREATE (s)-[:HAS_REFLECTION]->(r)
        RETURN r
        """,
        id=reflection.id,
        session_id=reflection.session_id,
        trigger=reflection.trigger.value,
        what_happened=reflection.what_happened,
        what_worked=reflection.what_worked,
        what_failed=reflection.what_failed,
        lessons=reflection.lessons,
        decisions=reflection.decisions,
        open_questions=reflection.open_questions,
        next_action=reflection.next_action.value,
        confidence=reflection.confidence,
        created_at=_dt(reflection.created_at),
        metadata=json.dumps(reflection.metadata),
    )
    return reflection


def list_reflections(
    client: Neo4jClient, session_id: str, *, limit: int = 50
) -> list[Reflection]:
    rows = client.read(
        """
        MATCH (s:Session {id: $session_id})-[:HAS_REFLECTION]->(r:Reflection)
        RETURN r
        ORDER BY r.created_at ASC
        LIMIT $limit
        """,
        session_id=session_id,
        limit=limit,
    )
    out: list[Reflection] = []
    for row in rows:
        node = row["r"]
        p = dict(node) if hasattr(node, "items") else node
        out.append(
            Reflection(
                id=p["id"],
                session_id=p["session_id"],
                trigger=ReflectionTrigger(p.get("trigger", "interval")),
                what_happened=p["what_happened"],
                what_worked=list(p.get("what_worked") or []),
                what_failed=list(p.get("what_failed") or []),
                lessons=list(p.get("lessons") or []),
                decisions=list(p.get("decisions") or []),
                open_questions=list(p.get("open_questions") or []),
                next_action=NextAction(p.get("next_action", "continue")),
                confidence=float(p.get("confidence") or 0.5),
                created_at=p.get("created_at") or datetime.utcnow(),
                metadata=_loads(p.get("metadata"), {}),
            )
        )
    return out


def create_decision(client: Neo4jClient, decision: Decision) -> Decision:
    client.write(
        """
        MATCH (s:Session {id: $session_id})
        CREATE (d:Decision {
            id: $id,
            session_id: $session_id,
            statement: $statement,
            rationale: $rationale,
            reversible: $reversible,
            created_at: $created_at,
            metadata: $metadata
        })
        CREATE (s)-[:MADE_DECISION]->(d)
        RETURN d
        """,
        id=decision.id,
        session_id=decision.session_id,
        statement=decision.statement,
        rationale=decision.rationale,
        reversible=decision.reversible,
        created_at=_dt(decision.created_at),
        metadata=json.dumps(decision.metadata),
    )
    return decision


def list_decisions(
    client: Neo4jClient,
    session_id: str | None = None,
    *,
    limit: int = 50,
) -> list[Decision]:
    if session_id:
        rows = client.read(
            """
            MATCH (s:Session {id: $session_id})-[:MADE_DECISION]->(d:Decision)
            RETURN d
            ORDER BY d.created_at DESC
            LIMIT $limit
            """,
            session_id=session_id,
            limit=limit,
        )
    else:
        rows = client.read(
            """
            MATCH (d:Decision)
            RETURN d
            ORDER BY d.created_at DESC
            LIMIT $limit
            """,
            limit=limit,
        )
    out: list[Decision] = []
    for row in rows:
        node = row["d"]
        p = dict(node) if hasattr(node, "items") else node
        out.append(
            Decision(
                id=p["id"],
                session_id=p["session_id"],
                statement=p["statement"],
                rationale=p.get("rationale") or "",
                reversible=bool(p.get("reversible", True)),
                created_at=p.get("created_at") or datetime.utcnow(),
                metadata=_loads(p.get("metadata"), {}),
            )
        )
    return out


def create_artifact(client: Neo4jClient, artifact: Artifact) -> Artifact:
    client.write(
        """
        MATCH (s:Session {id: $session_id})
        CREATE (a:Artifact {
            id: $id,
            session_id: $session_id,
            name: $name,
            kind: $kind,
            uri: $uri,
            content_preview: $content_preview,
            created_at: $created_at,
            metadata: $metadata
        })
        CREATE (s)-[:PRODUCED]->(a)
        RETURN a
        """,
        id=artifact.id,
        session_id=artifact.session_id,
        name=artifact.name,
        kind=artifact.kind,
        uri=artifact.uri,
        content_preview=artifact.content_preview,
        created_at=_dt(artifact.created_at),
        metadata=json.dumps(artifact.metadata),
    )
    return artifact


def list_artifacts(
    client: Neo4jClient, session_id: str, *, limit: int = 50
) -> list[Artifact]:
    rows = client.read(
        """
        MATCH (s:Session {id: $session_id})-[:PRODUCED]->(a:Artifact)
        RETURN a
        ORDER BY a.created_at DESC
        LIMIT $limit
        """,
        session_id=session_id,
        limit=limit,
    )
    out: list[Artifact] = []
    for row in rows:
        node = row["a"]
        p = dict(node) if hasattr(node, "items") else node
        out.append(
            Artifact(
                id=p["id"],
                session_id=p["session_id"],
                name=p["name"],
                kind=p.get("kind") or "file",
                uri=p.get("uri"),
                content_preview=p.get("content_preview"),
                created_at=p.get("created_at") or datetime.utcnow(),
                metadata=_loads(p.get("metadata"), {}),
            )
        )
    return out


def related_knowledge(
    client: Neo4jClient, session_id: str, *, limit: int = 20
) -> list[dict[str, Any]]:
    """Lightweight retrieval of decisions + recent episode summaries."""
    rows = client.read(
        """
        MATCH (s:Session {id: $session_id})
        OPTIONAL MATCH (s)-[:MADE_DECISION]->(d:Decision)
        OPTIONAL MATCH (s)-[:HAS_EPISODE]->(e:Episode)
        WITH collect(DISTINCT d)[..$half] AS decisions,
             collect(DISTINCT e)[..$half] AS episodes
        RETURN decisions, episodes
        """,
        session_id=session_id,
        half=max(1, limit // 2),
    )
    if not rows:
        return []
    result: list[dict[str, Any]] = []
    row = rows[0]
    for d in row.get("decisions") or []:
        if d is None:
            continue
        p = dict(d) if hasattr(d, "items") else d
        result.append({"type": "decision", "statement": p.get("statement"), "id": p.get("id")})
    for e in row.get("episodes") or []:
        if e is None:
            continue
        p = dict(e) if hasattr(e, "items") else e
        result.append(
            {
                "type": "episode",
                "summary": p.get("summary"),
                "kind": p.get("kind"),
                "id": p.get("id"),
            }
        )
    return result[:limit]


def relate_sessions(
    client: Neo4jClient, from_id: str, to_id: str, *, note: str = ""
) -> None:
    client.write(
        """
        MATCH (a:Session {id: $from_id}), (b:Session {id: $to_id})
        MERGE (a)-[r:RELATED_TO]->(b)
        SET r.note = $note
        """,
        from_id=from_id,
        to_id=to_id,
        note=note,
    )
