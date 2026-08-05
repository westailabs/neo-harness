"""Policy, redaction, and path gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from neo_harness.security.policy import PolicyTier, load_policy, path_allowed
from neo_harness.security.secrets import redact_secrets, redact_structure


def test_policy_tier_parse() -> None:
    assert PolicyTier.parse("report") == PolicyTier.REPORT
    assert PolicyTier.parse("APPLY") == PolicyTier.APPLY
    assert PolicyTier.parse(1) == PolicyTier.PROPOSE
    with pytest.raises(ValueError):
        PolicyTier.parse("nope")


def test_report_tier_disables_tools() -> None:
    p = load_policy(tier="report")
    assert p.tools_allowed(True) is False
    assert load_policy(tier="apply").tools_allowed(True) is True


def test_path_deny_env(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    secret = root / ".env"
    secret.write_text("x=1\n", encoding="utf-8")
    ok_file = root / "src" / "a.py"
    ok_file.parent.mkdir()
    ok_file.write_text("print(1)\n", encoding="utf-8")
    policy = load_policy(tier="apply", workspace_root=root)
    assert path_allowed(secret, policy).allowed is False
    assert path_allowed(ok_file, policy).allowed is True


def test_path_outside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    outside = tmp_path / "other" / "x.py"
    outside.parent.mkdir()
    outside.write_text("x\n", encoding="utf-8")
    policy = load_policy(tier="apply", workspace_root=root)
    assert path_allowed(outside, policy).allowed is False


def test_redact_api_keys() -> None:
    text = "token sk-abcdefghijklmnopqrstuvwxyz012345 and ghp_abcdefghijklmnopqrstuv"
    out = redact_secrets(text)
    assert "sk-abc" not in out
    assert "ghp_" not in out
    assert "REDACTED" in out


def test_redact_password_assignment() -> None:
    assert "secretpass" not in redact_secrets("NEO4J_PASSWORD=secretpass")
    assert "REDACTED" in redact_secrets("NEO4J_PASSWORD=secretpass")


def test_redact_structure() -> None:
    data = {"nested": {"key": "Bearer abcdefghijklmnop"}}
    out = redact_structure(data)
    assert "abcdefghijklmnop" not in str(out)
