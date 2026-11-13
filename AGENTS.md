# AGENTS.md — neo-harness

Instructions for AI coding agents working on this repo ([agents.md](https://agents.md)
convention). `CLAUDE.md` imports this file and `.gemini/settings.json` points Gemini CLI
here, so keep agent guidance in this one file.

## Project overview

- **neo-harness** is an alpha, production-style agent harness: an explicit
  PLAN → ACT → OBSERVE → REFLECT state machine, typed memory in Neo4j, budgets
  (steps, tokens, reflection cadence), and session continuity. The model is a
  replaceable reasoning engine; the harness owns control flow.
- Providers: `mock`, `grok_build`, `copilot`, `xai` (see [docs/providers.md](docs/providers.md)).
- Scaffolding new projects is [nebulus-forge](https://github.com/westailabs/nebulus-forge)'s
  job, not this repo's.
- Public repo: [westailabs/neo-harness](https://github.com/westailabs/neo-harness). MIT licensed.

## Setup and commands

Python 3.12+, managed with [uv](https://docs.astral.sh/uv/) (`uv.lock` is committed).

```bash
uv sync --all-extras                  # install into .venv (dev extras included)
uv run pytest -q                      # unit tests (no Neo4j needed)
uv run ruff check src tests           # lint (same as CI)
uv run neo version                    # CLI smoke
uv run neo start "Smoke test" --provider mock   # needs a local Neo4j + .env
```

Live CLI runs need Neo4j (`cp .env.example .env`, then `uv run neo init-db`). See
[CONTRIBUTING.md](CONTRIBUTING.md) for the Docker one-liner. Never read or print `.env` values.

CI (`.github/workflows/ci.yml`) runs `uv sync --all-extras`, `ruff check`, `pytest`, and an
import smoke on pushes and PRs to `develop` and `master`.

## Layout

| Path | Purpose |
|------|---------|
| `src/neo_harness/cli.py` | Typer CLI: `init-db`, `agents`, `start`, `resume`, `status`, `end`, `policy`, `audit`, `providers`, `init-workspace`, `version` |
| `src/neo_harness/harness/` | State machine, loop, budgets |
| `src/neo_harness/providers/` | Reasoning providers (`ReasoningProvider`, `get_provider()`) |
| `src/neo_harness/schemas/` | Pydantic v2 models for sessions, plans, episodes, reflections |
| `src/neo_harness/neo4j/` | Schema, constraints, queries |
| `src/neo_harness/agents/` | Agent pack loader |
| `src/neo_harness/security/`, `workspace/` | Run policy / audit, `init-workspace` embedding |
| `agents/` | Built-in generic packs (e.g. `sysadmin`: `AGENT.md` + `prompts/`) |
| `docs/` | User and developer docs ([docs/README.md](docs/README.md)) |
| `tests/` | Pytest suite |

Note: `agents/<id>/AGENT.md` files are harness **persona packs** loaded at runtime, not
instructions for coding agents. Keep them generic; workspace-specific packs live in the
consumer repo.

## Code style and design rules

- Python 3.12+, type hints on public functions, Pydantic v2 for externalizable models.
- Ruff config is in `pyproject.toml` (line length 100; `E`, `F`, `I`, `UP`, `B`).
- Keep the harness **thin**: control flow, budgets, memory, providers, not monorepo policy.
- The model only reasons inside PLAN / ACT / REFLECT. Transitions must stay inside
  `ALLOWED_TRANSITIONS`; illegal transitions fail in code, not via prompt discipline.
- New provider: implement `ReasoningProvider`, register in `get_provider()`, document in
  `docs/providers.md` and `docs/configuration.md`, prefer mock fallback on failure.
- Tests for every behavior change. Details: [docs/development.md](docs/development.md).
- Version bumps: change `version` in `pyproject.toml` and `__version__` in
  `src/neo_harness/__init__.py` together, and add a `CHANGELOG.md` entry.

## Git workflow

- `master` is the release branch (default on GitHub); `develop` is integration.
- Branch off `develop` (`feat/`, `fix/`, `docs/`, `chore/`), keep changes small, merge back
  with `git merge --squash` (one conventional commit) and delete the branch.
- Releases: merge `develop` into `master` with `--no-ff`, tag `vX.Y.Z`.
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`).
- Ask before pushing. Never force-push or skip hooks.

## Security

- Never commit `.env`, keys, tokens, virtualenvs, session dumps, or personal machine paths.
  See [SECURITY.md](SECURITY.md) and [docs/security-and-publishing.md](docs/security-and-publishing.md).
- Keep the harness session graph (lab default `localhost:7687`) separate from any shared
  org Neo4j / RAG service unless deliberately federated.
- Do not assert a service is healthy without probing it.
