"""Budget accounting tests."""

import pytest

from neo_harness.harness.budget import Budget, BudgetExceededError


def test_steps_and_reflect_interval() -> None:
    b = Budget(max_steps=5, reflect_every_n_actions=2)
    b.record_step()
    b.record_action()
    assert not b.should_reflect()
    b.record_action()
    assert b.should_reflect()
    b.reset_reflection_counter()
    assert not b.should_reflect()


def test_step_budget_exceeded() -> None:
    b = Budget(max_steps=2)
    b.record_step()
    b.record_step()
    with pytest.raises(BudgetExceededError) as exc:
        b.record_step()
    assert exc.value.kind == "steps"


def test_token_budget() -> None:
    b = Budget(max_tokens=100)
    b.record_tokens(50)
    b.record_tokens(50)
    with pytest.raises(BudgetExceededError):
        b.record_tokens(1)


def test_snapshot() -> None:
    b = Budget()
    snap = b.snapshot()
    assert "steps_used" in snap
    assert snap["should_reflect"] is False
