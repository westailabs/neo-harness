"""CLI task resolution helpers (no Neo4j)."""

from __future__ import annotations

from neo_harness.cli import task_summary


def test_task_summary_prefers_heading() -> None:
    text = "# Task: foobar alias\n\nLong body here.\n"
    assert task_summary(text, 80) == "Task: foobar alias"


def test_task_summary_truncates() -> None:
    text = "x" * 200
    s = task_summary(text, 50)
    assert len(s) <= 50
    assert s.endswith("…")
