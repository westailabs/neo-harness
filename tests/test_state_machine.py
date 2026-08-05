"""State machine: legal transitions and enforcement."""

import pytest

from neo_harness.harness.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    IllegalTransitionError,
    StateMachine,
)
from neo_harness.schemas.session import HarnessState


def test_starts_in_init() -> None:
    sm = StateMachine()
    assert sm.state == HarnessState.INIT


def test_happy_path_plan_act_observe_reflect_done() -> None:
    sm = StateMachine()
    sm.transition(HarnessState.PLAN, reason="start")
    sm.transition(HarnessState.ACT, reason="planned")
    sm.transition(HarnessState.OBSERVE, reason="acted")
    sm.transition(HarnessState.REFLECT, reason="interval")
    sm.transition(HarnessState.DONE, reason="complete")
    assert sm.is_terminal()
    assert sm.state == HarnessState.DONE
    assert len(sm.history) == 5


def test_illegal_transition_raises() -> None:
    sm = StateMachine()
    with pytest.raises(IllegalTransitionError) as exc:
        sm.transition(HarnessState.ACT)  # INIT → ACT illegal
    assert exc.value.current == HarnessState.INIT
    assert exc.value.target == HarnessState.ACT


def test_act_cannot_jump_to_plan() -> None:
    sm = StateMachine()
    sm.transition(HarnessState.PLAN)
    sm.transition(HarnessState.ACT)
    assert not sm.can_transition(HarnessState.PLAN)
    with pytest.raises(IllegalTransitionError):
        sm.transition(HarnessState.PLAN)


def test_terminal_has_no_exits() -> None:
    for state in TERMINAL_STATES:
        assert ALLOWED_TRANSITIONS[state] == frozenset()
        sm = StateMachine(state=state)
        assert sm.is_terminal()
        for target in HarnessState:
            assert not sm.can_transition(target)


def test_blocked_can_resume() -> None:
    sm = StateMachine()
    sm.transition(HarnessState.PLAN)
    sm.transition(HarnessState.BLOCKED, reason="need human")
    sm.transition(HarnessState.PLAN, reason="unblocked")
    assert sm.state == HarnessState.PLAN


def test_allowed_next() -> None:
    sm = StateMachine()
    assert HarnessState.PLAN in sm.allowed_next()
    assert HarnessState.DONE not in sm.allowed_next()


def test_every_nonterminal_has_edges() -> None:
    for state, targets in ALLOWED_TRANSITIONS.items():
        if state in TERMINAL_STATES:
            assert not targets
        else:
            assert targets, f"{state} should have outbound edges"
