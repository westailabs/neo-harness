"""Export session audit packages for InfoSec / operator review."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neo_harness import __version__
from neo_harness.neo4j import queries
from neo_harness.neo4j.client import Neo4jClient
from neo_harness.security.secrets import redact_structure


def build_audit_package(
    client: Neo4jClient,
    session_id: str,
    *,
    redact: bool = True,
    episode_limit: int = 500,
) -> dict[str, Any]:
    """Assemble a reviewable audit package for one session.

    Args:
        client: Neo4j client.
        session_id: Session id.
        redact: Apply secret redaction to string fields.
        episode_limit: Max episodes to include.

    Returns:
        Serializable dict (JSON-friendly).

    Raises:
        FileNotFoundError: If session does not exist.
    """
    session = queries.get_session(client, session_id)
    if session is None:
        raise FileNotFoundError(f"Session not found: {session_id}")

    episodes = queries.list_episodes(client, session_id, limit=episode_limit)
    reflections = queries.list_reflections(client, session_id, limit=episode_limit)
    decisions = queries.list_decisions(client, session_id=session_id, limit=200)
    artifacts = queries.list_artifacts(client, session_id, limit=200)

    package: dict[str, Any] = {
        "schema_version": 1,
        "exported_at": datetime.now(UTC).isoformat(),
        "neo_harness_version": __version__,
        "redacted": redact,
        "session": session.model_dump(mode="json"),
        "episodes": [e.model_dump(mode="json") for e in episodes],
        "reflections": [r.model_dump(mode="json") for r in reflections],
        "decisions": [d.model_dump(mode="json") for d in decisions],
        "artifacts": [a.model_dump(mode="json") for a in artifacts],
        "counts": {
            "episodes": len(episodes),
            "reflections": len(reflections),
            "decisions": len(decisions),
            "artifacts": len(artifacts),
        },
    }
    if redact:
        package = redact_structure(package)
        package["redacted"] = True
    return package


def export_audit(
    client: Neo4jClient,
    session_id: str,
    out_path: Path,
    *,
    redact: bool = True,
    fmt: str = "json",
) -> Path:
    """Write audit package to disk.

    Args:
        client: Neo4j client.
        session_id: Session id.
        out_path: Output file path.
        redact: Redact secrets.
        fmt: ``json`` or ``md``.

    Returns:
        Path written.
    """
    package = build_audit_package(client, session_id, redact=redact)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "md":
        out_path.write_text(_to_markdown(package), encoding="utf-8")
    else:
        out_path.write_text(
            json.dumps(package, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
    return out_path


def _to_markdown(package: dict[str, Any]) -> str:
    session = package.get("session") or {}
    lines = [
        f"# neo-harness audit — {session.get('id', '?')}",
        "",
        f"- Exported: {package.get('exported_at')}",
        f"- Version: {package.get('neo_harness_version')}",
        f"- Redacted: {package.get('redacted')}",
        f"- Task: {session.get('task', '')}",
        f"- Status: {session.get('status')} / state: {session.get('state')}",
        "",
        "## Counts",
        "",
    ]
    for k, v in (package.get("counts") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Episodes", ""])
    for ep in package.get("episodes") or []:
        lines.append(
            f"### {ep.get('kind')} @ {ep.get('created_at', '')} — {ep.get('summary', '')[:120]}"
        )
        lines.append("")
        content = ep.get("content")
        if content:
            lines.append("```json")
            lines.append(json.dumps(content, indent=2, default=str)[:4000])
            lines.append("```")
            lines.append("")
    lines.extend(["## Reflections", ""])
    for ref in package.get("reflections") or []:
        lines.append(
            f"- **{ref.get('next_action')}** ({ref.get('trigger')}): "
            f"{(ref.get('what_happened') or '')[:200]}"
        )
    lines.append("")
    return "\n".join(lines)
