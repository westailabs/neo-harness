# Troubleshooting

## uv / venv

### Warning: `VIRTUAL_ENV` does not match `.venv`

```text
warning: VIRTUAL_ENV=/home/…/.python3_venv does not match the project environment path `.venv`
```

**Cause:** Shell has another venv active; uv correctly uses project `.venv`.  
**Fix:** Ignore the warning and use `uv run …`, or:

```bash
deactivate 2>/dev/null || true
source .venv/bin/activate
```

### `neo: command not found`

Use `uv run neo` or activate **project** `.venv`, not `.python3_venv`.

### Packages installed in the wrong place

Avoid `uv sync --active` unless you mean to target the currently activated foreign env.

---

## Neo4j

### FAQ / Tip: `init-db` times out on `localhost:7687`

```text
Couldn't connect to localhost:7687 … Timed out …
Cannot connect to Neo4j. URI=bolt://localhost:7687
```

**This is usually not a neo-harness bug.** `neo init-db` does **not** start Neo4j.
It only connects to whatever `NEO4J_URI` / password say and applies schema.

| Check | Command / action |
|-------|------------------|
| Is anything listening? | `ss -ltn \| grep 7687` or `docker ps` |
| Remapped lab port? | Host **17687** → container 7687 is common |
| Match `.env` to the live stack | `NEO4J_URI=bolt://localhost:17687` (example) |
| Password | Must match **that** container’s `NEO4J_AUTH`, not the package default |

**Lab example:** container `…-neo4j` with  
`0.0.0.0:17687->7687/tcp` and `17474->7474` → use Bolt **`17687`**, Browser **`17474`**.

```bash
# See host port mapping
docker ps --format '{{.Names}} {{.Ports}}' | grep -i neo4j

# Point workspace .env at the host Bolt port
# NEO4J_URI=bolt://localhost:17687
# NEO4J_PASSWORD=<same as that instance>

./scripts/neo init-db
```

**Fresh dedicated instance** (if you want default 7687):

```bash
docker run -d --name neo4j-harness \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5
# .env: NEO4J_URI=bolt://localhost:7687  NEO4J_PASSWORD=password
```

**Multiple workspaces** may share one Neo4j (same URI) or each use a different
port/database — set each project’s `.env` accordingly. `init-db` only touches
the database you configured for **this** process.

### FAQ / Tip: several projects each with neo-harness

| Per workspace | Often shared |
|---------------|--------------|
| `.venv-neo`, `./scripts/neo`, `.env`, `agents/`, `jobs/` | Neo4j server (if same `NEO4J_URI`) |
| `NEO_PROVIDER_CWD` | Provider CLIs (`grok`, `copilot`) |

- Always run from the project root: `cd ~/projects/foo && ./scripts/neo …`  
- Same Bolt URI → **one graph** for all sessions (`status --all` mixes projects)  
- Isolate with different ports/databases if you need hard separation  
- Active session pointer under `~/.neo-harness/` is machine-local, not per-repo  

See [neo4j.md](./neo4j.md) (multiple instances) and [starting-a-workspace.md](./starting-a-workspace.md).

### `Neo.ClientError.Security.Unauthorized`

Wrong password/user for the instance on that URI.

1. Check what is listening: `docker ps` (host ports **7687 vs 17687**).  
2. Set `NEO4J_PASSWORD` in `.env` to match that container’s `NEO4J_AUTH`.  
3. Do not assume the example password `password` unless you set it that way.

### `Cannot connect` / connection refused

Same as the FAQ above: process not up, wrong **host** Bolt port, or firewall.

- Is Neo4j up? `docker ps \| grep -i neo4j`  
- Correct `NEO4J_URI` (**published** port, not always 7687)?  
- Firewall / bind address?

### Schema errors on first run

```bash
uv run neo init-db
# or from a workspace embed:
./scripts/neo init-db
```

Idempotent; safe to re-run. Requires a **reachable** Neo4j first.

---

## CLI / loop

### Terminal stuck on `Provider: … · running loop…`

Usually **not hung**. Real providers take a long time per call; history prints at the end.

**Check progress:**

```bash
uv run neo status -s <session_id>
uv run neo status --all
ps aux | rg 'neo start|copilot|grok'
```

### `No active session` after a successful start

Session reached `DONE`/`FAILED` and local active pointer was cleared. Use:

```bash
uv run neo status --all
uv run neo status -s <full-uuid>
```

### `zsh: parse error near '\n'`

Pasted multiple commands or a literal `<session_id>` placeholder. Run one command per line with a real UUID.

### Illegal transition / unexpected FAILED

Check `last_error` on the session and loop history. Budget exhaustion forces failure when legal. Inspect episodes in Neo4j.

### Provider always behaves like mock

- Binary missing (`which grok`, `which copilot`)?  
- Provider crashed and fell back (check logs/stderr)?  
- Wrong `--provider` / `NEO_PROVIDER`?

### Copilot / Grok auth failures

Log in with the respective CLI (`grok login`, `copilot` auth flow) outside the harness first.

---

## Tools / files

### No files written after a “design note” task

With `NEO_ACT_ALLOW_TOOLS=0`, ACT is pure reasoning. Episodes hold the content summary; disk writes need tools on and an explicit write step.

### Unexpected file edits

`NEO_ACT_ALLOW_TOOLS=1` allows the provider to modify the tree under `NEO_PROVIDER_CWD`. Use a worktree or clean git status before demos.

---

## Tests

```bash
uv run pytest -q
```

If imports fail, re-run `uv sync --all-extras` from the project root.
