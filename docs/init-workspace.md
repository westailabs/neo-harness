# `neo init-workspace` — thin harness embed

Populate an existing (or empty) git repository so it can **consume** neo-harness.
This is **not** a full project scaffolder (Forge-class). It only adds harness
embed files.

## What it creates

| Path | Purpose |
|------|---------|
| `env.neo.example` | Neo4j + provider + policy defaults |
| `requirements-neo.txt` | Package pin / install hint |
| `jobs/smoke-mock.md` | First bounded task |
| `agents/<pack>/` | Starter pack (manifest + short prompts) |
| `scripts/neo` | Optional workspace runner (venv-local) |
| `.gitignore` lines | `.venv-neo/`, `.env` |
| `README.md` section | Operator quick path |

## Usage

```bash
# inside a git repo
uv run neo init-workspace
uv run neo init-workspace /path/to/repo --pack platform
uv run neo init-workspace . --force          # overwrite embed files
uv run neo init-workspace . --no-pack        # files only, no agents/
uv run neo init-workspace . --no-runner      # skip scripts/neo
uv run neo init-workspace . --force-no-git   # allow non-git dirs
```

## After init

```bash
cp env.neo.example .env   # set NEO4J_PASSWORD
./scripts/neo providers   # or: uv run neo providers
./scripts/neo init-db
./scripts/neo start --task-file jobs/smoke-mock.md --agent workspace -p mock
```

Lab editable install:

```bash
export NEO_HARNESS_SRC=~/path/to/neo-harness
python3 -m venv .venv-neo
.venv-neo/bin/pip install -e "$NEO_HARNESS_SRC"
```

## Full walkthrough

Step-by-step from empty/existing git repo through first mock job:

→ **[starting-a-workspace.md](./starting-a-workspace.md)** (example: `~/projects/test`)

## Related

- [starting-a-workspace.md](./starting-a-workspace.md)  
- [workspace-embed.md](./workspace-embed.md)  
- [policy.md](./policy.md)  
- [providers.md](./providers.md)  
