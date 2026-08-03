"""Forced structured reflection — harness requires a valid Reflection model."""

from __future__ import annotations

from neo_harness.providers.base import ReasoningProvider
from neo_harness.schemas.episode import Episode
from neo_harness.schemas.plan import Plan
from neo_harness.schemas.reflection import NextAction, Reflection, ReflectionTrigger
from neo_harness.schemas.session import Session


REFLECTION_SYSTEM_PROMPT = """You are a structured reflection engine inside an agent harness.
Given recent session context, produce a honest, concise reflection.
You must choose next_action from: continue, replan, done, fail, block.
Prefer continue when progress is being made; replan when the plan is wrong;
done only when the goal is achieved; fail for unrecoverable errors; block for human input.
"""


def build_reflection_prompt(
    session: Session,
    plan: Plan | None,
    recent_episodes: list[Episode],
    trigger: ReflectionTrigger,
    error: str | None = None,
) -> str:
    lines = [
        f"Session task: {session.task}",
        f"Current goal: {session.goal or session.task}",
        f"State: {session.state.value}",
        f"Steps so far: {session.step_count}, actions: {session.action_count}",
        f"Reflection trigger: {trigger.value}",
    ]
    if error:
        lines.append(f"Error: {error}")
    if plan:
        lines.append(f"Plan goal: {plan.goal} (v{plan.version})")
        for step in plan.steps:
            lines.append(f"  [{step.status.value}] {step.index}. {step.description}")
    if recent_episodes:
        lines.append("Recent episodes:")
        for ep in recent_episodes[-10:]:
            lines.append(f"  - ({ep.kind.value}) {ep.summary}")
    lines.append(
        "Respond with structured fields: what_happened, what_worked, what_failed, "
        "lessons, decisions, open_questions, next_action, confidence."
    )
    return "\n".join(lines)


async def run_reflection(
    provider: ReasoningProvider,
    session: Session,
    plan: Plan | None,
    recent_episodes: list[Episode],
    trigger: ReflectionTrigger,
    error: str | None = None,
) -> Reflection:
    """
    Force a structured Reflection via the provider.

    On provider failure, returns a conservative fallback reflection
    so the harness never stalls without a decision.
    """
    prompt = build_reflection_prompt(session, plan, recent_episodes, trigger, error)
    try:
        result = await provider.reflect(
            system=REFLECTION_SYSTEM_PROMPT,
            prompt=prompt,
            session_id=session.id,
        )
        # Ensure session/trigger are set even if provider omits them.
        return result.model_copy(
            update={
                "session_id": session.id,
                "trigger": trigger,
            }
        )
    except Exception as exc:  # noqa: BLE001 — harness must stay resilient
        return _fallback_reflection(session, trigger, error or str(exc))


def _fallback_reflection(
    session: Session,
    trigger: ReflectionTrigger,
    error: str,
) -> Reflection:
    next_action = NextAction.FAIL if trigger == ReflectionTrigger.ERROR else NextAction.REPLAN
    if trigger == ReflectionTrigger.SESSION_END:
        next_action = NextAction.DONE
    return Reflection(
        session_id=session.id,
        trigger=trigger,
        what_happened=f"Reflection fallback after: {error}",
        what_worked=[],
        what_failed=[error],
        lessons=["Provider reflection failed; harness used fallback decision."],
        decisions=[],
        open_questions=["Should a human review this session?"],
        next_action=next_action,
        confidence=0.2,
        metadata={"fallback": True},
    )


def next_state_for_reflection(reflection: Reflection) -> str:
    """Map reflection next_action to a HarnessState value string."""
    mapping = {
        NextAction.CONTINUE: "ACT",
        NextAction.REPLAN: "PLAN",
        NextAction.DONE: "DONE",
        NextAction.FAIL: "FAILED",
        NextAction.BLOCK: "BLOCKED",
    }
    return mapping[reflection.next_action]
