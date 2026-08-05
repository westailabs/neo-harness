"""Named run profiles (token/ops presets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunProfile:
    """CLI/runtime knobs applied on start/resume."""

    name: str
    reflect_every_n: int | None = None
    loop_iterations: int | None = None
    max_steps: int | None = None
    description: str = ""


# cheap: fewer reflections, shorter loop — good for small demo-class jobs
# deep: more steps/reflect — design or multi-file work
# default: use settings as-is (no overrides)
PROFILES: dict[str, RunProfile] = {
    "default": RunProfile(name="default", description="Use env/settings defaults"),
    "cheap": RunProfile(
        name="cheap",
        reflect_every_n=99,
        loop_iterations=8,
        max_steps=24,
        description="Short jobs: sparse interval reflect, fewer loop iterations",
    ),
    "deep": RunProfile(
        name="deep",
        reflect_every_n=3,
        loop_iterations=24,
        max_steps=80,
        description="Longer work: more reflections and loop room",
    ),
}


def get_profile(name: str | None) -> RunProfile:
    if not name or not str(name).strip():
        return PROFILES["default"]
    key = str(name).strip().lower()
    if key not in PROFILES:
        known = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown profile {name!r}. Choose: {known}")
    return PROFILES[key]


def apply_profile_to_budget_kwargs(profile: RunProfile, settings: Any) -> dict[str, int]:
    """Build Budget constructor kwargs from settings with profile overlays."""
    return {
        "max_steps": profile.max_steps
        if profile.max_steps is not None
        else settings.max_steps,
        "max_tokens": settings.max_tokens,
        "reflect_every_n_actions": profile.reflect_every_n
        if profile.reflect_every_n is not None
        else settings.reflect_every_n,
    }


def profile_loop_iterations(
    profile: RunProfile, settings: Any, steps_opt: int | None
) -> int:
    if steps_opt is not None:
        return steps_opt
    if profile.loop_iterations is not None:
        return profile.loop_iterations
    return settings.loop_iterations
