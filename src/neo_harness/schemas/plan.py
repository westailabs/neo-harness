"""Planning schemas produced in the PLAN state."""

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


class StepStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


class PlanStep(BaseModel):
    """One atomic step in a plan."""

    id: str = Field(default_factory=_new_id)
    index: int = Field(..., ge=0)
    description: str = Field(..., min_length=1)
    status: StepStatus = StepStatus.PENDING
    rationale: str = ""
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """Structured plan generated in PLAN state."""

    id: str = Field(default_factory=_new_id)
    session_id: str
    goal: str = Field(..., min_length=1)
    steps: list[PlanStep] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    revised_at: datetime | None = None
    version: int = Field(default=1, ge=1)

    def next_pending_step(self) -> PlanStep | None:
        for step in sorted(self.steps, key=lambda s: s.index):
            if step.status == StepStatus.PENDING:
                return step
        return None

    def mark_step(self, step_id: str, status: StepStatus) -> PlanStep | None:
        for step in self.steps:
            if step.id == step_id:
                step.status = status
                return step
        return None

    @property
    def is_complete(self) -> bool:
        if not self.steps:
            return False
        return all(s.status in (StepStatus.DONE, StepStatus.SKIPPED) for s in self.steps)
