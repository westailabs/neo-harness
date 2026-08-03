"""Provider abstraction — model is a replaceable reasoning engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from neo_harness.schemas.plan import Plan, PlanStep
from neo_harness.schemas.reflection import Reflection


class ReasoningProvider(ABC):
    """
    Interface for planning, acting, and reflecting.

    Implementations must not own control flow — they only answer prompts
    for the current harness state.
    """

    name: str = "base"

    @abstractmethod
    async def plan(self, *, system: str, prompt: str, session_id: str) -> Plan:
        """Generate a structured Plan for the session task."""

    @abstractmethod
    async def act(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
        step: PlanStep,
    ) -> dict[str, Any]:
        """
        Perform (or simulate) one action.

        Returns a dict with at least:
          - summary: str
          - success: bool
        Optional: tokens_used, output, metadata
        """

    @abstractmethod
    async def reflect(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
    ) -> Reflection:
        """Produce a structured Reflection."""

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str | None = None,
    ) -> str:
        """Optional free-form completion hook for extensions."""
        raise NotImplementedError(f"{self.name} does not implement complete()")
