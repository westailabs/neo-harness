# Workspace embed — consume, don’t fork

**neo-harness** is a **Python package + `neo` CLI**. Workspaces (IaC repos,
monorepos, corp trees) **depend on it**; they do not re-implement the state machine.

## Bootstrap pattern

```text
1. git clone <workspace>
2. ./bootstrap or: python3 -m venv .venv && pip install neo-harness==x.y
3. cp .env.example .env   # Neo4j + provider; never commit secrets
4. neo start --task-file jobs/….md --agent <pack>
```

Lab (editable, until JFrog/private index exists):

```bash
cd ~/projects/my-workspace
python3 -m venv .venv
.venv/bin/pip install -e ~/projects/neo-harness
export NEO_PROVIDER_CWD="$PWD"
export NEO_AGENTS_DIR="$PWD/agents"   # optional if packs live here
.venv/bin/neo agents
.venv/bin/neo start --task-file jobs/demo.md -p mock -a sysadmin --no-run
```

Corp: `pip install neo-harness==x.y` from JFrog/Artifactory (same CLI).

## Where packs live

Search order (`agent_search_paths`):

1. `$NEO_PROVIDER_CWD/agents` — **workspace packs**
2. `$NEO_AGENTS_DIR`
3. neo-harness repo `agents/` (built-ins like `sysadmin`)
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
| Copilot provider | `gpt-5-mini` + effort `none` | Cheap default for that provider |

## Related

- [Plan](./plans/token-diet-and-workspace-embed.md)
- [SysAdmin workflow](./sysadmin-workflow.md)
- [Configuration](./configuration.md)
