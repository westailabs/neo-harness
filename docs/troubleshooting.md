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

### `Neo.ClientError.Security.Unauthorized`

Wrong password/user for the instance on that URI.

1. Check what is listening: `docker ps` (ports 7687 vs 17687).  
2. Set `NEO4J_PASSWORD` in `.env` to match that container’s `NEO4J_AUTH`.  
3. Lab compose often lives at `~/neo4j/docker-compose.yml`.

### `Cannot connect` / connection refused

- Is Neo4j up? `docker ps | rg neo4j`  
- Correct `NEO4J_URI` (bolt port)?  
- Firewall / bind address?

### Schema errors on first run

```bash
uv run neo init-db
```

Idempotent; safe to re-run.

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
