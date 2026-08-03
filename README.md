# neo-harness

Production-style **agent harness** for Grok Build, GitHub Copilot, and (optionally) the xAI API.

The model is a **replaceable reasoning engine**. The harness owns:

- Explicit control-flow (state machine)
- Typed memory (Neo4j)
- Budgets (steps / tokens / reflection cadence)
- Forced structured reflection
- Session continuity across days

## Documentation

**Full docs live in [`docs/`](./docs/README.md):**

| Doc | Topic |
|-----|--------|
| [Quick Start](./docs/quickstart.md) | Install, venv, Neo4j, first run |
| [Architecture](./docs/architecture.md) | State machine, memory, loop |
| [CLI](./docs/cli.md) | `start` · `resume` · `status` · `end` |
| [Providers](./docs/providers.md) | mock · grok_build · copilot · xai |
| [Neo4j](./docs/neo4j.md) | Schema, Browser queries |
| [Configuration](./docs/configuration.md) | Environment variables |
| [Usage & demo](./docs/usage-and-demo.md) | How to use it · **demo script** |
| [Development](./docs/development.md) | Layout, tests, extensions |
| [Troubleshooting](./docs/troubleshooting.md) | Common failures |

## Architecture (snapshot)

```
INIT → PLAN → ACT → OBSERVE ⇄ ACT
                 ↘     ↓
                   REFLECT → PLAN | ACT | DONE | FAILED | BLOCKED
```

| Layer | Responsibility |
|--------|----------------|
| **State machine** | Legal transitions only |
| **Memory** | Working · Episodic · Semantic (Neo4j SoT) |
| **Providers** | plan / act / reflect only |
| **CLI** | `neo start` · `resume` · `status` · `end` |

## Quick Start (shortest path)

```bash
cd ~/projects/neo-harness
uv sync --all-extras
cp .env.example .env   # set NEO4J_PASSWORD to match your DB
uv run neo init-db
uv run neo start "Smoke test" --provider mock
uv run neo status --all
```

**Always prefer `uv run`** if another venv (e.g. `.python3_venv`) is active — uv’s
“VIRTUAL_ENV does not match `.venv`” warning is safe to ignore.

Lab Neo4j password must match `~/neo4j/docker-compose.yml`, not the package default.

Real model:

```bash
NEO_ACT_ALLOW_TOOLS=0 uv run neo start "Draft a short design note for typed memory" --provider copilot
# or: --provider grok_build
```

Long runs look quiet; watch with `uv run neo status -s <id>` in another terminal.

## Demo

See **[docs/usage-and-demo.md](./docs/usage-and-demo.md)** for:

- When to use the harness vs free-form chat  
- Day-to-day recipes  
- An **~8 minute demo** (mock → real provider → Neo4j Browser → resume)

## Project layout

```
src/neo_harness/
  cli.py
  harness/          # state machine, budget, memory, reflection, loop
  providers/        # mock, grok_build, copilot, xai
  schemas/
  neo4j/
docs/
tests/
```

## Tests

```bash
uv run pytest -q
```

## License

MIT
