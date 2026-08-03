# Configuration

Settings load from environment variables and optional project **`.env`**
(`pydantic-settings`, see `config.py`). Copy from `.env.example`.

`.env` is gitignored — never commit real passwords or API keys.

## Core

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Bolt URL |
| `NEO4J_USER` | `neo4j` | User |
| `NEO4J_PASSWORD` | `password` | Password (**must match server**) |
| `NEO4J_DATABASE` | `neo4j` | Database name |
| `NEO_PROVIDER` | `mock` | `mock` \| `grok_build` \| `copilot` \| `xai` |
| `NEO_MAX_STEPS` | `50` | Step budget per budget object |
| `NEO_MAX_TOKENS` | `200000` | Token budget |
| `NEO_REFLECT_EVERY_N` | `3` | Force REFLECT after N actions |
| `NEO_LOOP_ITERATIONS` | `20` | Default max iterations per CLI run |
| `NEO_ACT_ALLOW_TOOLS` | `1` (code) / often `0` in lab `.env` | Tools during ACT |
| `NEO_PROVIDER_CWD` | process cwd | Working dir for CLI providers |

## Grok Build

| Variable | Default | Description |
|----------|---------|-------------|
| `GROK_BUILD_CMD` | `grok` | CLI command |
| `GROK_MODEL` | — | Optional model id |
| `NEO_GROK_MODEL` | — | Alias for model |
| `NEO_GROK_TIMEOUT` | `180` | Subprocess timeout (seconds) |
| `NEO_GROK_ACT_TURNS` | `8` | Max turns when ACT allows tools |

## Copilot

| Variable | Default | Description |
|----------|---------|-------------|
| `COPILOT_CMD` | `copilot` | CLI command |
| `COPILOT_MODEL` | — | Optional model |
| `NEO_COPILOT_MODEL` | — | Alias |
| `COPILOT_EFFORT` | `low` | Reasoning effort |
| `NEO_COPILOT_EFFORT` | — | Alias |
| `NEO_COPILOT_TIMEOUT` | `300` | Subprocess timeout (seconds) |

## xAI API

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_API_KEY` | — | Bearer token |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | API base |
| `XAI_MODEL` | `grok-2-latest` | Model name |

## Local state (not env)

| Path | Purpose |
|------|---------|
| `~/.neo-harness/active_session.json` | Last active session id for CLI convenience |

Neo4j remains authoritative if this file is missing or stale.

## Example `.env` (lab-oriented)

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<from-~/neo4j/docker-compose.yml>
NEO4J_DATABASE=neo4j

NEO_PROVIDER=grok_build
NEO_ACT_ALLOW_TOOLS=0
NEO_REFLECT_EVERY_N=3
NEO_LOOP_ITERATIONS=20
```

## CLI overrides

Provider and step cap can be set per invocation without editing `.env`:

```bash
uv run neo start "…" --provider copilot --steps 8
```
