"""Explicit state machine — legal transitions only, code-enforced."""

from __future__ import annotations

from dataclasses import dataclass, field

from neo_harness.schemas.session import HarnessState


class IllegalTransitionError(Exception):
    """Raised when a transition is not in the allowed graph."""

    def __init__(self, current: HarnessState, target: HarnessState) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Illegal transition: {current.value} → {target.value}")


# Terminal states have no outgoing transitions (except FAILED can be inspected only).
TERMINAL_STATES: frozenset[HarnessState] = frozenset(
    {
        HarnessState.DONE,
        HarnessState.FAILED,
    }
)

# Legal directed edges: from_state -> frozenset of allowed to_states.
# The harness owns this graph; the model cannot invent new transitions.
ALLOWED_TRANSITIONS: dict[HarnessState, frozenset[HarnessState]] = {
    HarnessState.INIT: frozenset(
        {
            HarnessState.PLAN,
            HarnessState.FAILED,
            HarnessState.BLOCKED,
        }
    ),
    HarnessState.PLAN: frozenset(
        {
            HarnessState.ACT,
            HarnessState.REFLECT,
            HarnessState.DONE,
            HarnessState.FAILED,
            HarnessState.BLOCKED,
        }
    ),
    HarnessState.ACT: frozenset(
        {
            HarnessState.OBSERVE,
            HarnessState.REFLECT,
            HarnessState.FAILED,
            HarnessState.BLOCKED,
        }
    ),
    HarnessState.OBSERVE: frozenset(
        {
            HarnessState.ACT,
            HarnessState.REFLECT,
            HarnessState.PLAN,
            HarnessState.DONE,
            HarnessState.FAILED,
            HarnessState.BLOCKED,
        }
    ),
    HarnessState.REFLECT: frozenset(
        {
            HarnessState.PLAN,
            HarnessState.ACT,
            HarnessState.DONE,
            HarnessState.FAILED,
            HarnessState.BLOCKED,
        }
    ),
    HarnessState.BLOCKED: frozenset(
        {
            HarnessState.PLAN,
            HarnessState.ACT,
            HarnessState.REFLECT,
            HarnessState.DONE,
            HarnessState.FAILED,
        }
    ),
    # Terminal: no exits.
    HarnessState.DONE: frozenset(),
    HarnessState.FAILED: frozenset(),
}


@dataclass
class TransitionRecord:
    """Audit entry for a successful transition."""

    from_state: HarnessState
    to_state: HarnessState
    reason: str = ""


@dataclass
class StateMachine:
    """
    Code-enforced harness state machine.

    The model never chooses arbitrary next states; only the harness calls
    `transition()` after validating the edge exists in ALLOWED_TRANSITIONS.
    """

    state: HarnessState = HarnessState.INIT
    history: list[TransitionRecord] = field(default_factory=list)

    def can_transition(self, target: HarnessState) -> bool:
        allowed = ALLOWED_TRANSITIONS.get(self.state, frozenset())
        return target in allowed

    def transition(self, target: HarnessState, *, reason: str = "") -> HarnessState:
        if not self.can_transition(target):
            raise IllegalTransitionError(self.state, target)
        record = TransitionRecord(from_state=self.state, to_state=target, reason=reason)
        self.history.append(record)
        self.state = target
        return self.state

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def allowed_next(self) -> frozenset[HarnessState]:
        return ALLOWED_TRANSITIONS.get(self.state, frozenset())

    def reset(self, state: HarnessState = HarnessState.INIT) -> None:
        """Restore machine to a known state (e.g. session resume)."""
        self.state = state
        # history is intentionally preserved unless caller clears it
