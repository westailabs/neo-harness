# Contributing to neo-harness

Thanks for interest in improving the harness. This project is early (**0.x alpha**).

## Development setup

```bash
git clone https://github.com/westailabs/neo-harness.git
cd neo-harness
uv sync --all-extras          # or: python3 -m venv .venv && pip install -e ".[dev]"
cp .env.example .env          # Neo4j password for local runs
uv run pytest -q
```

Optional Neo4j (for live CLI smoke, not required for unit tests):

```bash
docker run -d --name neo4j-harness \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5
# set NEO4J_PASSWORD=password in .env
uv run neo init-db
uv run neo start "Smoke test" --provider mock
```

## Guidelines

- **Python 3.12+**, type hints on public functions  
- Keep the harness **thin**: control flow, budgets, memory, providers — not monorepo policy  
- Prefer small PRs with tests for behavior changes  
- Do not commit `.env`, secrets, virtualenvs, or personal machine paths  
- Run `uv run pytest -q` (and `uv run ruff check src tests` if you touch style)

## Pull requests

1. Branch from `develop` (or `master` if that is the default integration branch)  
2. Describe *why* and *what*  
3. Link related issues  
4. Ensure CI is green  

## Design notes

- The model only **reasons** inside PLAN / ACT / REFLECT  
- Illegal state transitions must fail in code, not via prompt discipline  
- Workspace-specific agent packs live in the *consumer* repo; built-ins stay generic  

See [docs/architecture.md](docs/architecture.md) and [docs/development.md](docs/development.md).
