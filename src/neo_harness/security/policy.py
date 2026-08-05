"""Policy tiers and path allow/deny for ACT tooling (InfoSec control plane)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path


class PolicyTier(IntEnum):
    """Operational authority for harness ACT tools.

    report  — observe only; no durable edits (tools off or read-only intent)
    propose — may draft patches/diffs; operator applies
    apply   — may write within path policy (still operator-owned push)
    """

    REPORT = 0
    PROPOSE = 1
    APPLY = 2

    @classmethod
    def parse(cls, value: str | int | None) -> PolicyTier:
        if value is None or value == "":
            return cls.PROPOSE
        if isinstance(value, int):
            return cls(value)
        key = str(value).strip().lower()
        aliases = {
            "0": cls.REPORT,
            "report": cls.REPORT,
            "read": cls.REPORT,
            "1": cls.PROPOSE,
            "propose": cls.PROPOSE,
            "draft": cls.PROPOSE,
            "2": cls.APPLY,
            "apply": cls.APPLY,
            "write": cls.APPLY,
        }
        if key not in aliases:
            raise ValueError(
                f"Unknown policy tier {value!r}; use report|propose|apply (0|1|2)"
            )
        return aliases[key]


@dataclass(frozen=True)
class PolicyConfig:
    """Resolved policy for one run."""

    tier: PolicyTier = PolicyTier.PROPOSE
    allow_globs: tuple[str, ...] = field(default_factory=tuple)
    deny_globs: tuple[str, ...] = field(default_factory=tuple)
    workspace_root: Path | None = None

    def tools_allowed(self, act_allow_tools: bool) -> bool:
        """Whether ACT may enable provider tools under this tier."""
        if self.tier == PolicyTier.REPORT:
            return False
        return bool(act_allow_tools)


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    path: str | None = None


def _split_csv(raw: str | None) -> tuple[str, ...]:
    if not raw or not str(raw).strip():
        return ()
    return tuple(p.strip() for p in str(raw).split(",") if p.strip())


def load_policy(
    *,
    tier: str | int | None = None,
    allow: str | None = None,
    deny: str | None = None,
    workspace_root: str | Path | None = None,
) -> PolicyConfig:
    """Load policy from args with env fallbacks.

    Env:
      NEO_POLICY_TIER=report|propose|apply
      NEO_PATH_ALLOW=comma globs relative to workspace (empty = allow all under root)
      NEO_PATH_DENY=comma globs always blocked
      NEO_PROVIDER_CWD=workspace root
    """
    env_tier = tier if tier is not None else os.environ.get("NEO_POLICY_TIER")
    env_allow = allow if allow is not None else os.environ.get("NEO_PATH_ALLOW")
    env_deny = deny if deny is not None else os.environ.get("NEO_PATH_DENY")
    root_s = workspace_root or os.environ.get("NEO_PROVIDER_CWD")
    root = Path(root_s).expanduser().resolve() if root_s else None
    # Sensible default denylist for secrets/vcs
    default_deny = (
        ".env",
        ".env.*",
        "**/.env",
        "**/.env.*",
        "**/*.pem",
        "**/*id_rsa*",
        "**/.git/config",
        "**/credentials*",
        "**/secrets/**",
    )
    deny_globs = _split_csv(env_deny) or default_deny
    return PolicyConfig(
        tier=PolicyTier.parse(env_tier),
        allow_globs=_split_csv(env_allow),
        deny_globs=deny_globs,
        workspace_root=root,
    )


def _match_glob(path: Path, pattern: str, *, root: Path | None) -> bool:
    from fnmatch import fnmatch

    s = str(path)
    name = path.name
    if fnmatch(name, pattern) or fnmatch(s, pattern):
        return True
    if root is not None:
        try:
            rel = path.resolve().relative_to(root.resolve())
            rel_s = str(rel).replace("\\", "/")
            if fnmatch(rel_s, pattern) or fnmatch(rel_s, pattern.lstrip("./")):
                return True
            # **/pattern
            if pattern.startswith("**/") and fnmatch(rel_s, pattern[3:]):
                return True
            if fnmatch(rel_s, pattern.replace("**/", "")):
                return True
        except ValueError:
            pass
    return fnmatch(s.replace("\\", "/"), pattern)


def path_allowed(path: str | Path, policy: PolicyConfig) -> PolicyDecision:
    """Return whether ``path`` may be written/touched under policy."""
    p = Path(path).expanduser()
    try:
        resolved = p.resolve()
    except OSError:
        resolved = p

    for pattern in policy.deny_globs:
        if _match_glob(resolved, pattern, root=policy.workspace_root):
            return PolicyDecision(
                False, f"denied by NEO_PATH_DENY pattern {pattern!r}", str(resolved)
            )

    if policy.workspace_root is not None:
        try:
            resolved.relative_to(policy.workspace_root.resolve())
        except ValueError:
            return PolicyDecision(
                False,
                f"path outside workspace root {policy.workspace_root}",
                str(resolved),
            )

    if policy.allow_globs:
        for pattern in policy.allow_globs:
            if _match_glob(resolved, pattern, root=policy.workspace_root):
                return PolicyDecision(True, f"allowed by {pattern!r}", str(resolved))
        return PolicyDecision(
            False, "not matched by NEO_PATH_ALLOW", str(resolved)
        )

    return PolicyDecision(True, "allowed (no allowlist; under workspace)", str(resolved))


def policy_preamble(policy: PolicyConfig) -> str:
    """Short system-prompt fragment for PLAN/ACT under this policy."""
    tier = policy.tier
    lines = [
        "---",
        f"POLICY TIER: {tier.name.lower()} ({int(tier)})",
    ]
    if tier == PolicyTier.REPORT:
        lines.append(
            "Tools/edits: FORBIDDEN. Observe and report only; describe what you would change."
        )
    elif tier == PolicyTier.PROPOSE:
        lines.append(
            "Tools: propose diffs and commands; prefer not to apply host-changing "
            "actions unless the operator already enabled tools and path policy allows."
        )
    else:
        lines.append(
            "Tools: apply within path policy; never commit secrets; operator owns push."
        )
    if policy.workspace_root:
        lines.append(f"Workspace root: {policy.workspace_root}")
    if policy.allow_globs:
        lines.append("Path allow: " + ", ".join(policy.allow_globs))
    deny_preview = ", ".join(policy.deny_globs[:8])
    if len(policy.deny_globs) > 8:
        deny_preview += "…"
    lines.append("Path deny: " + deny_preview)
    lines.append("---")
    return "\n".join(lines)
