"""Episodic memory schemas — past steps and session events."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


class EpisodeKind(StrEnum):
    """What kind of event this episode records."""

    PLAN = "plan"
    ACTION = "action"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    DECISION = "decision"
    ERROR = "error"
    SYSTEM = "system"


class Episode(BaseModel):
    """A single typed event in a session's timeline."""

    id: str = Field(default_factory=_new_id)
    session_id: str
    kind: EpisodeKind
    state: str = Field(..., description="Harness state when this episode was recorded")
    summary: str = Field(..., min_length=1)
    content: dict[str, Any] = Field(default_factory=dict)
    step_index: int = Field(default=0, ge=0)
    success: bool = True
    created_at: datetime = Field(default_factory=_utc_now)
    tags: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    """A durable decision made during a session (promoted to semantic memory)."""

    id: str = Field(default_factory=_new_id)
    session_id: str
    statement: str = Field(..., min_length=1)
    rationale: str = ""
    reversible: bool = True
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """A produced artifact (file path, URL, blob ref, etc.)."""

    id: str = Field(default_factory=_new_id)
    session_id: str
    name: str = Field(..., min_length=1)
    kind: str = Field(default="file", description="file | url | text | other")
    uri: str | None = None
    content_preview: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
