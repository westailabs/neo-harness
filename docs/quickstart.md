# Quick Start

## Requirements

- Python **3.12+**
- [uv](https://github.com/astral-sh/uv) (preferred) or pip + venv
- Neo4j **5.x** reachable over Bolt
- Optional: `grok` (Grok Build CLI), `copilot` (GitHub Copilot CLI), or `XAI_API_KEY`

## Project environment

This project uses a **local** `.venv` managed by uv.

If your shell already has another env active, uv may print:

```text
warning: VIRTUAL_ENV=... does not match the project environment path `.venv`
```

**That is normal.** Prefer **`uv run …`** so every command uses the project env.

| Approach | When |
|----------|------|
| `uv run neo …` | Always safe |
| `source .venv/bin/activate` then `neo …` | Interactive shell; deactivate other venvs first |
| Bare `neo` while a foreign venv is active | Often **wrong** — missing package / entrypoint |

```bash
cd neo-harness
uv sync --all-extras
uv run which neo
# → …/neo-harness/.venv/bin/neo
```

Do **not** use `uv sync --active` unless you intentionally want installs in the foreign active venv.

## Neo4j

`NEO4J_PASSWORD` must match the **running** database. The package default
`password` is only a placeholder for local Docker.

**Fresh Docker** (default ports 7474 / 7687):

```bash
docker run -d --name neo4j-harness \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5
```

Browser: http://localhost:7474

If you already run Neo4j on different host ports, set `NEO4J_URI` in `.env`
(for example `bolt://localhost:17687`) to match that instance. A timeout on
default `7687` usually means the server is on another host port — see
[troubleshooting FAQ](./troubleshooting.md#faq--tip-init-db-times-out-on-localhost7687).

## First run

```bash
cd neo-harness
uv sync --all-extras

cp .env.example .env
# Edit NEO4J_PASSWORD (and optionally NEO_PROVIDER) to match your DB

uv run neo init-db

# Fast structural smoke (no model spend)
uv run neo start "Smoke test neo-harness" --provider mock

uv run neo status --all
```

### With a real model

```bash
# Grok Build CLI (authenticated `grok` on PATH)
uv run neo start "Draft a short design note for typed memory" --provider grok_build

# GitHub Copilot CLI
uv run neo start "Draft a short design note for typed memory" --provider copilot
```

While a real provider runs, the terminal may sit on `running loop…` for several minutes.
Progress is still written to Neo4j — use another terminal:

```bash
uv run neo status --all
uv run neo status -s <session_id>
```

## Verify install

```bash
uv run python -c "import neo_harness; print(neo_harness.__version__)"
uv run pytest -q
uv run neo version
```

## Next reading

- [Starting a workspace](./starting-a-workspace.md) — embed neo-harness in a new project  
- [Usage & demo](./usage-and-demo.md) — how to use and present the harness  
- [Providers](./providers.md) — mock / grok / copilot / xai  
- [Workspace embed](./workspace-embed.md) — use from another git repo  
- [Troubleshooting](./troubleshooting.md) — auth, venv, hung-looking runs  
