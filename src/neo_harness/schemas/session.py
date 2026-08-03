"""Session lifecycle schemas."""

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


class SessionStatus(StrEnum):
    """High-level session lifecycle status (orthogonal to harness state)."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class HarnessState(StrEnum):
    """Explicit harness control states. Transitions are code-enforced."""

    INIT = "INIT"
    PLAN = "PLAN"
    ACT = "ACT"
    OBSERVE = "OBSERVE"
    REFLECT = "REFLECT"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class Session(BaseModel):
    """A durable work session spanning one or more days."""

    id: str = Field(default_factory=_new_id)
    task: str = Field(..., min_length=1, description="User-facing task description")
    status: SessionStatus = SessionStatus.ACTIVE
    state: HarnessState = HarnessState.INIT
    goal: str | None = Field(default=None, description="Current refined goal")
    step_count: int = Field(default=0, ge=0)
    action_count: int = Field(default=0, ge=0)
    reflection_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    last_error: str | None = None

    def touch(self) -> None:
        """Bump updated_at to now."""
        self.updated_at = _utc_now()

    def mark_ended(self, status: SessionStatus = SessionStatus.COMPLETED) -> None:
        self.status = status
        self.ended_at = _utc_now()
        self.touch()
