"""Neo4j constraints and indexes for neo-harness graph."""

from __future__ import annotations

import logging

from neo_harness.neo4j.client import Neo4jClient

logger = logging.getLogger(__name__)

# Node labels: Session, Episode, Reflection, Decision, Artifact
# Relationships: HAS_EPISODE, HAS_REFLECTION, PRODUCED, RELATED_TO, MADE_DECISION

CONSTRAINTS: list[str] = [
    # Uniqueness on business ids
    "CREATE CONSTRAINT session_id IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT reflection_id IF NOT EXISTS FOR (r:Reflection) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (a:Artifact) REQUIRE a.id IS UNIQUE",
]

INDEXES: list[str] = [
    "CREATE INDEX session_status IF NOT EXISTS FOR (s:Session) ON (s.status)",
    "CREATE INDEX session_state IF NOT EXISTS FOR (s:Session) ON (s.state)",
    "CREATE INDEX session_updated IF NOT EXISTS FOR (s:Session) ON (s.updated_at)",
    "CREATE INDEX episode_session IF NOT EXISTS FOR (e:Episode) ON (e.session_id)",
    "CREATE INDEX episode_kind IF NOT EXISTS FOR (e:Episode) ON (e.kind)",
    "CREATE INDEX episode_created IF NOT EXISTS FOR (e:Episode) ON (e.created_at)",
    "CREATE INDEX reflection_session IF NOT EXISTS FOR (r:Reflection) ON (r.session_id)",
    "CREATE INDEX decision_session IF NOT EXISTS FOR (d:Decision) ON (d.session_id)",
    "CREATE INDEX artifact_session IF NOT EXISTS FOR (a:Artifact) ON (a.session_id)",
    # Full-text for semantic-ish search of decisions / episode summaries
    (
        "CREATE FULLTEXT INDEX episode_summary_ft IF NOT EXISTS "
        "FOR (e:Episode) ON EACH [e.summary]"
    ),
    (
        "CREATE FULLTEXT INDEX decision_statement_ft IF NOT EXISTS "
        "FOR (d:Decision) ON EACH [d.statement]"
    ),
]


def setup_schema(client: Neo4jClient) -> None:
    """Apply constraints and indexes (idempotent)."""
    client.connect()
    for stmt in CONSTRAINTS:
        try:
            client.run(stmt)
            logger.debug("Applied: %s", stmt[:60])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Constraint statement failed: %s — %s", stmt[:80], exc)
    for stmt in INDEXES:
        try:
            client.run(stmt)
            logger.debug("Applied: %s", stmt[:60])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Index statement failed: %s — %s", stmt[:80], exc)
    logger.info("Neo4j schema setup complete (%d constraints, %d indexes)", len(CONSTRAINTS), len(INDEXES))


def drop_all_harness_data(client: Neo4jClient) -> None:
    """
    Delete harness nodes only (dangerous — for dev/tests).

    Does not drop constraints/indexes.
    """
    client.write(
        """
        MATCH (n)
        WHERE n:Session OR n:Episode OR n:Reflection OR n:Decision OR n:Artifact
        DETACH DELETE n
        """
    )
