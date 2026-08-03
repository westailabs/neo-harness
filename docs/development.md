# Development

## Setup

```bash
cd ~/projects/neo-harness
uv sync --all-extras
uv run pytest -q
```

Editable install is handled by `uv sync` / the project’s hatchling build.

## Layout

```
neo-harness/
├── pyproject.toml
├── README.md                 # overview + pointers
├── .env.example
├── docs/                     # this documentation
├── src/neo_harness/
│   ├── cli.py
│   ├── config.py
│   ├── harness/
│   ├── providers/
│   ├── schemas/
│   └── neo4j/
└── tests/
```

## Tests

```bash
uv run pytest -q
```

| Module | Coverage |
|--------|----------|
| `test_state_machine.py` | Legal/illegal transitions, terminals |
| `test_schemas.py` | Pydantic session/plan/episode/reflection |
| `test_budget.py` | Step/token/reflect interval |
| `test_json_util.py` | CLI JSON / Grok envelope parsing |
| `test_mock_loop.py` | Full PLAN→…→DONE with mock + faked Neo4j |

Unit tests do **not** require Neo4j. Integration against a live DB is manual via CLI.

## Code style

- Python 3.12+, type hints preferred  
- Pydantic v2 for all externalizable models  
- Ruff configured in `pyproject.toml` (`uv run ruff check src tests`)

## Extending

### New provider

1. Implement `ReasoningProvider` in `providers/`.
2. Register in `get_provider()`.
3. Document in `docs/providers.md` + `docs/configuration.md`.
4. Prefer mock fallback on failure.

### New graph types

1. Add Pydantic schema under `schemas/`.
2. Constraints/indexes in `neo4j/schema.py`.
3. CRUD in `neo4j/queries.py`.
4. Wire through memory interfaces / loop as needed.

### Loop behavior

- Transitions must stay inside `ALLOWED_TRANSITIONS`.
- Never let the model pick an arbitrary next state string without mapping through harness code.

## Version

Bump `version` in `pyproject.toml` and `__version__` in `src/neo_harness/__init__.py` together.

## Related ecosystem (lab)

- Shared Neo4j / RAG services may run on **other** ports than neo-harness’s session DB.  
- Keep harness session graph (`localhost:7687` lab default) distinct from org LTM unless you deliberately federate.
