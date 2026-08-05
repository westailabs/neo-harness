# CLI reference

Entry point: **`neo`** (console script from the package).

Always prefer:

```bash
uv run neo <command>
# or after: source .venv/bin/activate
neo <command>
```

## Global

```bash
neo --help
neo --version
neo version
neo policy                 # show tier + path gates
neo policy --check-path P  # allow/deny test
neo providers              # provider readiness
neo init-workspace [path]  # thin embed into a git repo
neo audit <session_id> -o review.json
neo audit <session_id> -o review.md --format md
```

New project walkthrough: [starting-a-workspace.md](./starting-a-workspace.md).

## `neo init-db`

Create Neo4j constraints and indexes (idempotent).

```bash
uv run neo init-db
```

Requires a working Bolt connection (see [configuration](./configuration.md)).

## `neo start`

Start a new session for a task description.

```bash
uv run neo start "Task description here"
uv run neo start --task-file /tmp/job.md --agent sysadmin
uv run neo start - < /tmp/job.md --provider mock
uv run neo start "…" --provider mock|grok_build|copilot|xai
uv run neo start "…" --agent sysadmin    # workstation IaC persona
uv run neo start "…" --steps 12          # max loop iterations this run
uv run neo start "…" --no-run            # create Session only; do not enter loop
```

| Option | Description |
|--------|-------------|
| `TASK` | Task string, or `-` for stdin (optional if `--task-file`) |
| `-f / --task-file` | Read task brief from a file |
| `-p / --provider` | Override `NEO_PROVIDER` |
| `-a / --agent` | Agent pack id (override `NEO_AGENT`); e.g. `sysadmin` |
| `-n / --steps` | Cap harness loop iterations for this invocation |
| `--profile` | `default` \| `cheap` \| `deep` — loop/reflect presets |
| `--no-run` | Persist session in INIT/active without calling the model |

On start: schema ensure, upsert `Session`, save active id, optionally `HarnessLoop.run`.

## `neo agents`

List loadable agent packs (`agents/<id>/`).

```bash
uv run neo agents
```

## `neo resume`

Resume an existing session by UUID.

```bash
uv run neo resume <session_id>
uv run neo resume <session_id> --provider copilot --steps 10
uv run neo resume <session_id> --agent sysadmin
```

- Loads session + recent episodes from Neo4j.
- If status was `completed`/`failed`, reopens as active and may force state to `PLAN`.
- If `BLOCKED`, unblocks into `PLAN`.
- Re-runs the loop with prior step_count informing budget usage.

Use a real UUID (from `neo status --all`), not the placeholder `<session_id>`.

## `neo status`

```bash
uv run neo status                 # active local pointer, else latest active-ish session
uv run neo status -s <session_id>
uv run neo status --session <session_id>
uv run neo status --all           # recent sessions table
```

Shows status, harness state, counters, and last ~10 episodes for a single session.

**Note:** After a run reaches `DONE`, the local active pointer is cleared, so bare
`neo status` may say “No active session.” Use `--all` or `-s <id>`.

## `neo end`

End active or specified session.

```bash
uv run neo end
uv run neo end --session <session_id>
uv run neo end --fail             # mark FAILED instead of COMPLETED
```

Attempts a final reflection with trigger `session_end` when the session is not already
terminal. Clears local active pointer when it matches.

## Exit and UX notes

- Real providers can take **minutes** with little stdout until the loop finishes.
- Watch progress: second terminal `neo status -s …` or Neo4j Browser.
- Do not paste multiple shell lines with angle-bracket placeholders in one go (zsh may error).

## Programmatic equivalent

```python
import asyncio
from neo_harness.harness.budget import Budget
from neo_harness.harness.loop import HarnessLoop
from neo_harness.harness.memory import MemoryBundle
from neo_harness.neo4j.client import Neo4jClient
from neo_harness.neo4j.schema import setup_schema
from neo_harness.providers import get_provider
from neo_harness.schemas.session import Session

async def main() -> None:
    with Neo4jClient() as client:
        setup_schema(client)
        session = Session(task="Explore harness loop")
        memory = MemoryBundle.from_client(client, goal=session.task)
        loop = HarnessLoop(
            client=client,
            provider=get_provider("mock"),
            memory=memory,
            budget=Budget(reflect_every_n_actions=2),
            max_iterations=12,
        )
        result = await loop.run(session)
        print(result.final_state, result.history)

asyncio.run(main())
```
