"""Thin workspace population for neo-harness embed (not a full Forge)."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

from neo_harness import __version__

# Starter pack files (generic — no personal machine names)
_PACK_MANIFEST = """\
id: {pack_id}
name: {pack_title}
description: Starter harness pack for this workspace (edit prompts as needed)
target_repos: {repo_name}
"""

_PACK_PERSONA = """\
{pack_title} — bounded PLAN→ACT→REFLECT work in this repository.

Rules: smallest coherent change; no secrets in git; operator owns commit/push;
prefer repo control plane over one-off host mutations.
"""

_PACK_PLAN = """\
You are the **{pack_title}** planning engine inside neo-harness.

Produce a short, ordered multi-step plan (2–6 steps) for the task in this workspace.
Prefer validation steps. No essay.
"""

_PACK_ACT = """\
You are the **{pack_title}** action engine inside neo-harness.

Execute one plan step when tools are enabled; otherwise describe exact files/commands.
Never commit secrets. Return summary, paths, success boolean, residual risk.
"""

_PACK_REFLECT = """\
You are the **{pack_title}** reflection engine inside neo-harness.

Judge progress honestly. next_action: continue | replan | done | fail | block.
"""

_PACK_AGENT_MD = """\
# AGENT PROFILE: {pack_title}

Harness pack id: `{pack_id}`

Use with:

```bash
neo start --task-file jobs/smoke-mock.md --agent {pack_id} -p mock
```

Edit `prompts/` for domain-specific behavior. Policy is controlled by env
(`NEO_POLICY_TIER`), not this file alone.
"""

_ENV_EXAMPLE = """\
# Copy to .env (gitignored). Never commit real secrets.
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

NEO_PROVIDER=mock
NEO_POLICY_TIER=propose
NEO_ACT_ALLOW_TOOLS=0
NEO_PROVIDER_FALLBACK=mock
# Fail-closed for InfoSec runs: NEO_PROVIDER_FALLBACK=none

# Default pack id (must exist under $NEO_PROVIDER_CWD/agents/<id>/).
# Built-in package packs only include sysadmin — workspace packs come from init-workspace.
NEO_AGENT={pack_id}

# Absolute path to THIS checkout (not another machine's path).
# Prefer ./scripts/neo — it sets NEO_PROVIDER_CWD to the repo root automatically.
NEO_PROVIDER_CWD={cwd}

# Optional path gates (comma-separated globs under workspace)
# NEO_PATH_ALLOW=src/**,docs/**,tests/**,jobs/**
# NEO_PATH_DENY=.env,**/*.pem,secrets/**
"""

_REQUIREMENTS = """\
# neo-harness embed (pin when publishing to an index)
# neo-harness=={version}
#
# Lab editable install:
#   pip install -e /path/to/neo-harness
#
# Or: pip install "neo-harness @ git+https://github.com/westailabs/neo-harness.git@v{version}"

neo-harness>={version}
"""

_JOB_SMOKE = """\
# Task: neo-harness workspace smoke (mock)

## Goal

Validate neo-harness embed in this workspace. No product code changes required.

## Success

- Session reaches DONE under mock provider
- No secrets written; no push
"""

_SCRIPTS_NEO = """\
#!/usr/bin/env bash
# Workspace runner — project venv only (not a global neo install).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${{ROOT}}/.venv-neo"
BIN="${{VENV}}/bin/neo"
ENV_FILE="${{ROOT}}/.env"

if [[ ! -x "${{BIN}}" ]]; then
  echo "==> Creating ${{VENV}} and installing neo-harness" >&2
  python3 -m venv "${{VENV}}"
  "${{VENV}}/bin/pip" install -U pip -q
  if [[ -f "${{ROOT}}/requirements-neo.txt" ]]; then
    "${{VENV}}/bin/pip" install -r "${{ROOT}}/requirements-neo.txt" -q
  else
    "${{VENV}}/bin/pip" install "neo-harness>={version}" -q
  fi
fi

if [[ -f "${{ENV_FILE}}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${{ENV_FILE}}"
  set +a
fi
export NEO_PROVIDER_CWD="${{NEO_PROVIDER_CWD:-${{ROOT}}}}"
cd "${{ROOT}}"
exec "${{BIN}}" "$@"
"""

_GITIGNORE_SNIPPET = """\
# neo-harness local
.venv-neo/
.env
neo-audit*.json
neo-audit*.md
"""

_README_SNIPPET = """\
## neo-harness

This workspace embeds [neo-harness](https://github.com/westailabs/neo-harness)
for bounded PLAN→ACT→REFLECT jobs (token-efficient vs full monorepo chat).

```bash
# Prefer ./scripts/neo (loads .env + NEO_PROVIDER_CWD). Do not use bare .venv-neo/bin/neo.
./scripts/neo init-db          # once (needs Neo4j)
./scripts/neo providers
./scripts/neo policy
./scripts/neo agents           # must list {pack_id}
./scripts/neo start --task-file jobs/smoke-mock.md --agent {pack_id} -p mock
```

Policy default: **propose**. Set `NEO_POLICY_TIER=report` for read-only.
See package docs: workspace-embed, policy, threat-model.
"""


@dataclass
class InitResult:
    root: Path
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def _write(
    path: Path,
    content: str,
    *,
    force: bool,
    result: InitResult,
    executable: bool = False,
) -> None:
    rel = str(path)
    try:
        rel = str(path.relative_to(result.root))
    except ValueError:
        pass
    if path.exists() and not force:
        result.skipped.append(rel)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result.created.append(rel)


def init_workspace(
    root: Path | str,
    *,
    pack_id: str = "workspace",
    force: bool = False,
    with_runner: bool = True,
    with_pack: bool = True,
    require_git: bool = True,
) -> InitResult:
    """Populate a directory as a neo-harness consumer workspace.

    Does **not** scaffold full product apps (that is Forge/template territory).
    Only embed files: env example, jobs, optional pack, optional scripts/neo.
    """
    root = Path(root).expanduser().resolve()
    result = InitResult(root=root)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    if require_git and not (root / ".git").exists():
        raise RuntimeError(
            f"{root} is not a git repository. "
            "Run `git init` or pass require_git=False / --force-no-git."
        )

    repo_name = root.name
    pack_title = pack_id.replace("-", " ").replace("_", " ").title() + " Agent"
    cwd = str(root)
    ctx = {
        "pack_id": pack_id,
        "pack_title": pack_title,
        "repo_name": repo_name,
        "cwd": cwd,
        "version": __version__,
    }

    _write(root / "env.neo.example", _ENV_EXAMPLE.format(**ctx), force=force, result=result)
    _write(
        root / "requirements-neo.txt",
        _REQUIREMENTS.format(**ctx),
        force=force,
        result=result,
    )
    _write(
        root / "jobs" / "smoke-mock.md",
        _JOB_SMOKE,
        force=force,
        result=result,
    )

    if with_pack:
        pack_root = root / "agents" / pack_id
        _write(
            pack_root / "manifest.yml",
            _PACK_MANIFEST.format(**ctx),
            force=force,
            result=result,
        )
        _write(
            pack_root / "AGENT.md",
            _PACK_AGENT_MD.format(**ctx),
            force=force,
            result=result,
        )
        _write(
            pack_root / "prompts" / "persona.short.md",
            _PACK_PERSONA.format(**ctx),
            force=force,
            result=result,
        )
        _write(
            pack_root / "prompts" / "plan.md",
            _PACK_PLAN.format(**ctx),
            force=force,
            result=result,
        )
        _write(
            pack_root / "prompts" / "act.md",
            _PACK_ACT.format(**ctx),
            force=force,
            result=result,
        )
        _write(
            pack_root / "prompts" / "reflect.md",
            _PACK_REFLECT.format(**ctx),
            force=force,
            result=result,
        )

    if with_runner:
        _write(
            root / "scripts" / "neo",
            _SCRIPTS_NEO.format(version=__version__),
            force=force,
            result=result,
            executable=True,
        )

    # Soft-append gitignore / README (never clobber whole file)
    gi = root / ".gitignore"
    if gi.exists():
        text = gi.read_text(encoding="utf-8")
        if ".venv-neo" not in text:
            gi.write_text(text.rstrip() + "\n" + _GITIGNORE_SNIPPET, encoding="utf-8")
            result.created.append(".gitignore (appended neo-harness lines)")
        else:
            result.skipped.append(".gitignore (already has neo-harness entries)")
    else:
        _write(gi, _GITIGNORE_SNIPPET, force=force, result=result)

    readme = root / "README.md"
    marker = "## neo-harness"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        if marker not in text:
            readme.write_text(
                text.rstrip() + "\n\n" + _README_SNIPPET.format(**ctx),
                encoding="utf-8",
            )
            result.created.append("README.md (appended neo-harness section)")
        else:
            result.skipped.append("README.md (section exists)")
    else:
        _write(
            readme,
            f"# {repo_name}\n\n" + _README_SNIPPET.format(**ctx),
            force=force,
            result=result,
        )

    result.messages.append(
        "Next: copy env.neo.example → .env; set NEO4J_PASSWORD; "
        "./scripts/neo providers; ./scripts/neo init-db; "
        f"./scripts/neo start --task-file jobs/smoke-mock.md --agent {pack_id} -p mock"
    )
    # Hint for local editable install
    neo_src = os.environ.get("NEO_HARNESS_SRC")
    if neo_src:
        result.messages.append(
            f"Lab editable: .venv-neo/bin/pip install -e {neo_src}"
        )
    return result
