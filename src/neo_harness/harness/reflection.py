"""Forced structured reflection — harness requires a valid Reflection model."""

from __future__ import annotations

from neo_harness.agents.loader import DEFAULT_REFLECT_SYSTEM, AgentProfile
from neo_harness.providers.base import ReasoningProvider
from neo_harness.schemas.episode import Episode
from neo_harness.schemas.plan import Plan
from neo_harness.schemas.reflection import NextAction, Reflection, ReflectionTrigger
from neo_harness.schemas.session import Session

# Back-compat alias
REFLECTION_SYSTEM_PROMPT = DEFAULT_REFLECT_SYSTEM


def _task_line(session: Session) -> str:
    meta = session.metadata or {}
    summary = meta.get("task_summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    task = session.task.strip()
    first = task.splitlines()[0] if task else ""
    if len(first) > 200:
        return first[:200] + "…"
    return first or task[:200]


def build_reflection_prompt(
    session: Session,
    plan: Plan | None,
    recent_episodes: list[Episode],
    trigger: ReflectionTrigger,
    error: str | None = None,
    *,
    max_prompt_chars: int = 2500,
) -> str:
    lines = [
        f"Session task: {_task_line(session)}",
        f"Current goal: {session.goal or _task_line(session)}",
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
        for ep in recent_episodes:
            lines.append(f"  - ({ep.kind.value}) {ep.summary[:200]}")
    lines.append(
        "Respond with structured fields: what_happened, what_worked, what_failed, "
        "lessons, decisions, open_questions, next_action, confidence."
    )
    text = "\n".join(lines)
    if max_prompt_chars > 0 and len(text) > max_prompt_chars:
        return text[: max_prompt_chars - 16].rstrip() + "\n…[truncated]"
    return text


async def run_reflection(
    provider: ReasoningProvider,
    session: Session,
    plan: Plan | None,
    recent_episodes: list[Episode],
    trigger: ReflectionTrigger,
    error: str | None = None,
    agent: AgentProfile | None = None,
    max_prompt_chars: int = 2500,
) -> Reflection:
    """
    Force a structured Reflection via the provider.

    On provider failure, returns a conservative fallback reflection
    so the harness never stalls without a decision.
    """
    prompt = build_reflection_prompt(
        session,
        plan,
        recent_episodes,
        trigger,
        error,
        max_prompt_chars=max_prompt_chars,
    )
    system = agent.system_for("reflect") if agent is not None else DEFAULT_REFLECT_SYSTEM
    try:
        result = await provider.reflect(
            system=system,
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
