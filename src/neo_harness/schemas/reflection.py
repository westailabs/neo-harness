"""Forced structured reflection schemas."""

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


class ReflectionTrigger(StrEnum):
    """Why reflection was forced."""

    INTERVAL = "interval"  # every N actions
    ERROR = "error"
    BLOCKED = "blocked"
    MANUAL = "manual"
    SESSION_END = "session_end"
    PLAN_COMPLETE = "plan_complete"


class NextAction(StrEnum):
    """What the harness should do after reflection."""

    CONTINUE = "continue"  # keep acting on current plan
    REPLAN = "replan"  # return to PLAN
    DONE = "done"  # task complete
    FAIL = "fail"  # unrecoverable
    BLOCK = "block"  # need human / external input


class Reflection(BaseModel):
    """Structured reflection produced in REFLECT state and stored as an Episode."""

    id: str = Field(default_factory=_new_id)
    session_id: str
    trigger: ReflectionTrigger
    what_happened: str = Field(..., min_length=1)
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    lessons: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    next_action: NextAction = NextAction.CONTINUE
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
