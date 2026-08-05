"""Run profile presets."""

from __future__ import annotations

import pytest

from neo_harness.profiles import (
    apply_profile_to_budget_kwargs,
    get_profile,
    profile_loop_iterations,
)


class _S:
    max_steps = 50
    max_tokens = 1000
    reflect_every_n = 3
    loop_iterations = 20


def test_cheap_profile_overrides() -> None:
    p = get_profile("cheap")
    kw = apply_profile_to_budget_kwargs(p, _S())
    assert kw["reflect_every_n_actions"] == 99
    assert kw["max_steps"] == 24
    assert profile_loop_iterations(p, _S(), None) == 8
    assert profile_loop_iterations(p, _S(), 3) == 3


def test_default_profile_keeps_settings() -> None:
    p = get_profile(None)
    kw = apply_profile_to_budget_kwargs(p, _S())
    assert kw["max_steps"] == 50
    assert kw["reflect_every_n_actions"] == 3


def test_unknown_profile() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        get_profile("turbo-mega")
