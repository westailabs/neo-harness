# neo-harness

**Alpha** production-style **agent harness** for Grok Build, GitHub Copilot, and (optionally) the xAI API.

The model is a **replaceable reasoning engine**. The harness owns:

- Explicit control-flow (state machine)
- Typed memory (Neo4j)
- Budgets (steps / tokens / reflection cadence)
- Forced structured reflection
- Session continuity across days

> **Status:** `0.1.x` alpha — APIs and CLI flags may change before 1.0.  
> **License:** [MIT](./LICENSE)

## Documentation

Full docs: [`docs/`](./docs/README.md)

| Doc | Topic |
|-----|--------|
| [Quick Start](./docs/quickstart.md) | Install, Neo4j, first run |
| [Architecture](./docs/architecture.md) | State machine, memory, loop |
| [CLI](./docs/cli.md) | `start` · `resume` · `status` · `end` |
| [Providers](./docs/providers.md) | mock · grok_build · copilot · xai |
| [Starting a workspace](./docs/starting-a-workspace.md) | New project → init → first mock job |
| [Workspace embed](./docs/workspace-embed.md) | Use neo-harness inside your own repo |
| [Related projects](./docs/related-projects.md) | **nebulus-forge** (scaffold) vs this runtime |
| [Security & publishing](./docs/security-and-publishing.md) | Secrets hygiene |
| [Contributing](./CONTRIBUTING.md) | Dev setup and PRs |

Full project scaffolding: **[nebulus-forge](https://github.com/westailabs/nebulus-forge)** (`forge new`, optional `--neo auto`).

## Architecture (snapshot)

```
INIT → PLAN → ACT → OBSERVE ⇄ ACT
                 ↘     ↓
                   REFLECT → PLAN | ACT | DONE | FAILED | BLOCKED
```

| Layer | Responsibility |
|--------|----------------|
| **State machine** | Legal transitions only |
| **Memory** | Working · Episodic · Semantic (Neo4j source of truth) |
| **Providers** | plan / act / reflect only |
| **CLI** | `neo start` · `resume` · `status` · `end` |

## Quick Start

### Requirements

- Python **3.12+**
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Neo4j **5.x** over Bolt (local Docker is fine)
- Optional: `grok` CLI, `copilot` CLI, or `XAI_API_KEY`

### Neo4j (fresh Docker)

```bash
docker run -d --name neo4j-harness \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5
```

Browser: http://localhost:7474 — set the same password in `.env`.

### Install and smoke (mock provider)

```bash
git clone https://github.com/westailabs/neo-harness.git
cd neo-harness
uv sync --all-extras

cp .env.example .env
# NEO4J_URI=bolt://localhost:7687
# NEO4J_PASSWORD=password   # must match the running DB

uv run neo init-db
uv run neo start "Smoke test neo-harness" --provider mock
uv run neo status --all
uv run pytest -q
```

Prefer **`uv run neo …`** so the project `.venv` is used even if another virtualenv is active.

### Real model

```bash
# Grok Build CLI (authenticated `grok` on PATH)
uv run neo start "Draft a short design note for typed memory" --provider grok_build

# GitHub Copilot CLI
uv run neo start "Draft a short design note for typed memory" --provider copilot
```

Long runs can look quiet; progress is in Neo4j:

```bash
uv run neo status --all
uv run neo status -s <session_id>
```

### SysAdmin agent (host IaC repos)

```bash
uv run neo agents
NEO_ACT_ALLOW_TOOLS=1 \
  NEO_PROVIDER_CWD=~/path/to/your-host-iac \
  uv run neo start "Add a status check for ruff to make status" \
    --provider grok_build \
    --agent sysadmin
```

## Workspace embed

Treat **neo-harness as a library/CLI**; your monorepo or IaC tree is the workspace:

```bash
# in your git project
uv run neo init-workspace --pack workspace
# or after pip install:
neo init-workspace --pack workspace
cp env.neo.example .env
./scripts/neo providers
./scripts/neo start --task-file jobs/smoke-mock.md --agent workspace -p mock
```

Full walkthrough: **[docs/starting-a-workspace.md](./docs/starting-a-workspace.md)**  
(example path `~/projects/test`). Also [init-workspace](./docs/init-workspace.md),
[workspace-embed](./docs/workspace-embed.md). Thin embed only — not a full
Forge-style project generator.

## Project layout

```
src/neo_harness/
  cli.py
  harness/          # state machine, budget, memory, reflection, loop
  providers/        # mock, grok_build, copilot, xai
  schemas/
  neo4j/
agents/             # built-in packs (e.g. sysadmin)
docs/
tests/
```

## Tests

```bash
uv run pytest -q
```

## Security

Never commit `.env` or API keys. See [SECURITY.md](./SECURITY.md) and
[docs/security-and-publishing.md](./docs/security-and-publishing.md).

## License

[MIT](./LICENSE) © West AI Labs LLC
