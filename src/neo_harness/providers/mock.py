"""Deterministic mock provider for local loop demos and tests."""

from __future__ import annotations

from typing import Any

from neo_harness.providers.base import ReasoningProvider
from neo_harness.schemas.plan import Plan, PlanStep
from neo_harness.schemas.reflection import NextAction, Reflection, ReflectionTrigger


class MockProvider(ReasoningProvider):
    """
    Placeholder reasoning engine.

    Produces a simple 3-step plan, marks each act as success, and reflects
    with CONTINUE until all steps are done, then DONE.
    """

    name = "mock"

    def __init__(self) -> None:
        self._act_calls = 0
        self._plan_calls = 0

    async def plan(self, *, system: str, prompt: str, session_id: str) -> Plan:
        self._plan_calls += 1
        # Extract a rough goal from the prompt.
        goal = "Complete the user task"
        for line in prompt.splitlines():
            if line.startswith("Task:"):
                goal = line.removeprefix("Task:").strip() or goal
                break
        steps = [
            PlanStep(index=0, description=f"Clarify scope for: {goal[:80]}"),
            PlanStep(index=1, description="Execute core work for the task"),
            PlanStep(index=2, description="Verify outcome and capture artifacts"),
        ]
        return Plan(
            session_id=session_id,
            goal=goal,
            steps=steps,
            assumptions=["Mock provider — no real tools available"],
            risks=["Results are simulated"],
        )

    async def act(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
        step: PlanStep,
    ) -> dict[str, Any]:
        self._act_calls += 1
        return {
            "summary": f"[mock] Completed step {step.index}: {step.description}",
            "success": True,
            "tokens_used": 50,
            "output": {"step_id": step.id, "mock": True},
        }

    async def reflect(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
    ) -> Reflection:
        # Heuristic: if plan complete language appears, finish; else continue/replan.
        lower = prompt.lower()
        plan_done = "done" in lower and "pending" not in lower
        # Count "[done]" style statuses in prompt
        done_marks = lower.count("[done]")
        pending_marks = lower.count("[pending]")

        if pending_marks == 0 and done_marks > 0:
            next_action = NextAction.DONE
            what = "All plan steps completed successfully (mock)."
        elif "error" in lower:
            next_action = NextAction.REPLAN
            what = "An error was reported; recommending replan (mock)."
        else:
            next_action = NextAction.CONTINUE
            what = "Progress looks fine; continue acting (mock)."

        # Session end trigger
        if "session_end" in lower or "session end" in lower:
            next_action = NextAction.DONE
            what = "Session ending (mock)."

        return Reflection(
            session_id=session_id,
            trigger=ReflectionTrigger.INTERVAL,
            what_happened=what,
            what_worked=["Mock actions succeeded"] if next_action != NextAction.FAIL else [],
            what_failed=[],
            lessons=["Replace MockProvider with Grok Build / xAI for real reasoning."],
            decisions=[] if next_action != NextAction.DONE else ["Accept mock completion"],
            open_questions=[],
            next_action=next_action,
            confidence=0.85 if next_action == NextAction.DONE else 0.7,
            metadata={"provider": "mock", "plan_done_heuristic": plan_done},
        )
