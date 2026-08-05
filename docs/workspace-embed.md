# Workspace embed — consume, don’t fork

**neo-harness** is a **Python package + `neo` CLI**. Workspaces (IaC repos,
monorepos, product trees) **depend on it**; they do not re-implement the state machine.

## Bootstrap pattern

Preferred (from neo-harness install):

```bash
cd /path/to/your-git-repo
neo init-workspace --pack workspace   # creates agents/workspace + scripts/neo
cp env.neo.example .env               # set NEO4J_PASSWORD (+ fix NEO_PROVIDER_CWD if wrong)
./scripts/neo providers
./scripts/neo agents                  # must list workspace
./scripts/neo start --task-file jobs/smoke-mock.md --agent workspace -p mock
```

**Entrypoint rule:** use **`./scripts/neo`**, not bare `.venv-neo/bin/neo`.

| Entrypoint | Loads `.env`? | Sets `NEO_PROVIDER_CWD`? | Typical packs seen |
|------------|---------------|--------------------------|--------------------|
| `./scripts/neo …` | yes | yes (repo root) | workspace + sysadmin |
| `.venv-neo/bin/neo …` | **no** | only if you exported it | often **sysadmin only** |

`env.neo.example` sets `NEO_AGENT=workspace`. That only works when the pack
exists under `$NEO_PROVIDER_CWD/agents/workspace`. Without CWD, start fails
with “only sysadmin available” — see [troubleshooting](./troubleshooting.md#faq-agent-pack-workspace-not-found--only-sysadmin-listed).

Manual pattern:

```text
1. git clone <workspace>
2. neo init-workspace --pack workspace   # do not skip
3. python3 -m venv .venv-neo && .venv-neo/bin/pip install neo-harness==x.y
   # lab: pip install -e /path/to/neo-harness
4. cp env.neo.example .env  (set secrets + absolute NEO_PROVIDER_CWD if needed)
5. ./scripts/neo start --task-file jobs/….md --agent workspace -p mock
```

See [init-workspace.md](./init-workspace.md) and the full guide
[starting-a-workspace.md](./starting-a-workspace.md).

### Editable (local development of the harness)

```bash
cd ~/path/to/my-workspace
python3 -m venv .venv-neo
.venv-neo/bin/pip install -e ~/path/to/neo-harness
export NEO_PROVIDER_CWD="$PWD"
.venv-neo/bin/neo agents
.venv-neo/bin/neo start --task-file jobs/demo.md -p mock -a sysadmin --no-run
```

### Published package (when available)

```bash
pip install neo-harness==0.1.x
# or from a private index your org maintains
```

## Where packs live

Search order (`agent_search_paths`):

1. `$NEO_PROVIDER_CWD/agents` — **workspace packs**
2. `$NEO_AGENTS_DIR`
3. neo-harness repo / package `agents/` (built-ins like `sysadmin`)
4. `~/.neo-harness/agents`

A directory counts as a harness pack only if it has **`manifest.yml`** (or
`.yaml`) **or** a `prompts/` tree with at least one of `plan.md` / `act.md` /
`reflect.md` / `persona.short.md`. Free-form `AGENT.md`-only profiles (e.g.
chat role cards in monorepos) are **not** listed as packs.

## Token thrift (defaults)

| Knob | Default | Role |
|------|---------|------|
| `prompts/persona.short.md` | preferred | Short model persona |
| `NEO_FULL_PERSONA=1` | off | Inject full AGENT.md (expensive) |
| `NEO_PROMPT_MAX_CHARS_*` | 4k/3k/2.5k | Phase prompt caps |
| `NEO_EPISODE_TAIL` | 5 | Reflection episode count |
| `NEO_OBSERVATION_TAIL` | 3 | ACT/PLAN observation count |
| `--task-file` | — | Keep long briefs out of shell history |
| Copilot provider | thrifty model + effort defaults | See configuration docs |

## Related

- [Plan](./plans/token-diet-and-workspace-embed.md)
- [SysAdmin workflow](./sysadmin-workflow.md)
- [Configuration](./configuration.md)
