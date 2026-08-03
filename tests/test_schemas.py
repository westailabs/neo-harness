"""Pydantic schema smoke tests."""

from neo_harness.schemas import (
    Episode,
    EpisodeKind,
    HarnessState,
    NextAction,
    Plan,
    PlanStep,
    Reflection,
    ReflectionTrigger,
    Session,
    SessionStatus,
    StepStatus,
)


def test_session_defaults() -> None:
    s = Session(task="Ship neo-harness v0.1")
    assert s.status == SessionStatus.ACTIVE
    assert s.state == HarnessState.INIT
    assert s.step_count == 0
    assert s.id
    s.touch()
    s.mark_ended()
    assert s.status == SessionStatus.COMPLETED
    assert s.ended_at is not None


def test_plan_next_and_complete() -> None:
    plan = Plan(
        session_id="s1",
        goal="Do the thing",
        steps=[
            PlanStep(index=0, description="A"),
            PlanStep(index=1, description="B"),
        ],
    )
    first = plan.next_pending_step()
    assert first is not None and first.index == 0
    plan.mark_step(first.id, StepStatus.DONE)
    second = plan.next_pending_step()
    assert second is not None and second.index == 1
    plan.mark_step(second.id, StepStatus.DONE)
    assert plan.is_complete
    assert plan.next_pending_step() is None


def test_episode_and_reflection() -> None:
    ep = Episode(
        session_id="s1",
        kind=EpisodeKind.ACTION,
        state="ACT",
        summary="Did a thing",
    )
    assert ep.success is True

    ref = Reflection(
        session_id="s1",
        trigger=ReflectionTrigger.INTERVAL,
        what_happened="Progress",
        next_action=NextAction.CONTINUE,
        confidence=0.8,
    )
    assert ref.next_action == NextAction.CONTINUE


def test_harness_state_values() -> None:
    expected = {"INIT", "PLAN", "ACT", "OBSERVE", "REFLECT", "DONE", "FAILED", "BLOCKED"}
    assert {s.value for s in HarnessState} == expected
