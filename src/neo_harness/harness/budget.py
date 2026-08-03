"""Token and step budgets — harness-owned limits the model cannot override."""

from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceededError(Exception):
    """Raised when a budget is exhausted."""

    def __init__(self, kind: str, used: int, limit: int) -> None:
        self.kind = kind
        self.used = used
        self.limit = limit
        super().__init__(f"{kind} budget exceeded: {used}/{limit}")


@dataclass
class Budget:
    """
    Tracks step and token usage for a session.

    Reflection interval is also owned here so the loop can force REFLECT
    after every N successful actions.
    """

    max_steps: int = 50
    max_tokens: int = 200_000
    reflect_every_n_actions: int = 3

    steps_used: int = 0
    tokens_used: int = 0
    actions_since_reflect: int = 0

    _soft_warned: set[str] = field(default_factory=set, repr=False)

    def record_step(self) -> None:
        self.steps_used += 1
        if self.steps_used > self.max_steps:
            raise BudgetExceededError("steps", self.steps_used, self.max_steps)

    def record_tokens(self, n: int) -> None:
        if n < 0:
            raise ValueError("token count must be non-negative")
        self.tokens_used += n
        if self.tokens_used > self.max_tokens:
            raise BudgetExceededError("tokens", self.tokens_used, self.max_tokens)

    def record_action(self) -> None:
        """Call after a successful ACT. Increments reflection counter."""
        self.actions_since_reflect += 1

    def should_reflect(self) -> bool:
        return self.actions_since_reflect >= self.reflect_every_n_actions

    def reset_reflection_counter(self) -> None:
        self.actions_since_reflect = 0

    def remaining_steps(self) -> int:
        return max(0, self.max_steps - self.steps_used)

    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.tokens_used)

    def snapshot(self) -> dict[str, int | bool]:
        return {
            "steps_used": self.steps_used,
            "max_steps": self.max_steps,
            "tokens_used": self.tokens_used,
            "max_tokens": self.max_tokens,
            "actions_since_reflect": self.actions_since_reflect,
            "reflect_every_n_actions": self.reflect_every_n_actions,
            "should_reflect": self.should_reflect(),
        }
