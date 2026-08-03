# Quick Start

## Requirements

- Python **3.12+**
- [uv](https://github.com/astral-sh/uv) (preferred)
- Neo4j **5.x** reachable over Bolt
- Optional: `grok` (Grok Build CLI), `copilot` (GitHub Copilot CLI), or `XAI_API_KEY`

## Project environment (important)

This project uses a **local** `.venv` managed by uv.

If your shell already has another env active (e.g. `🐍 .python3_venv`), uv prints:

```text
warning: VIRTUAL_ENV=.../.python3_venv does not match the project environment path `.venv`
```

**That is normal.** Prefer **`uv run …`** so every command uses the project env.

| Approach | When |
|----------|------|
| `uv run neo …` | Always safe |
| `source .venv/bin/activate` then `neo …` | Interactive shell; deactivate other venvs first |
| Bare `neo` while `.python3_venv` is active | Often **wrong** — missing package / entrypoint |

```bash
cd ~/projects/neo-harness
uv sync --all-extras
uv run which neo
# → …/neo-harness/.venv/bin/neo
```

Do **not** use `uv sync --active` unless you intentionally want installs in the foreign active venv.

## Neo4j credentials

`NEO4J_PASSWORD` must match the **running** database. Package default `password` is only a placeholder.

**Shurtugal lab:** container `neo4j` on `bolt://localhost:7687`. Auth is defined in
`~/neo4j/docker-compose.yml` (`NEO4J_AUTH=neo4j/…`). Put that password in project `.env`.

**Fresh Docker** (only if nothing owns 7474/7687):

```bash
docker run -d --name neo4j-harness \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5
```

Browser: http://localhost:7474

## First run (lab)

```bash
cd ~/projects/neo-harness
uv sync --all-extras

# Once: env file (password must match your Neo4j)
cp .env.example .env
# Edit NEO4J_PASSWORD (and optionally NEO_PROVIDER)

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

- [Usage & demo](./usage-and-demo.md) — how to use and present the harness  
- [Providers](./providers.md) — mock / grok / copilot / xai  
- [Troubleshooting](./troubleshooting.md) — auth, venv, hung-looking runs  
