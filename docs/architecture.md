# Architecture

## Goals

| Goal | Mechanism |
|------|-----------|
| Stop free-form drift | Explicit state machine with code-enforced edges |
| Durable memory | Neo4j as single source of truth |
| Multi-day work | Session lifecycle: start → work → end → resume |
| Swappable models | `ReasoningProvider` interface only used inside a state |

The **harness owns** control flow, memory retrieval, budgets, and reflection.  
The **provider** only answers plan / act / reflect prompts for the **current** state.

## Package layout

```
src/neo_harness/
  cli.py                 # Typer: neo start|resume|status|end|init-db
  config.py              # pydantic-settings from env / .env
  harness/
    state_machine.py     # HarnessState + ALLOWED_TRANSITIONS
    budget.py            # step/token limits, reflect-every-N
    reflection.py        # structured Reflection + fallback
    memory.py            # Working / Episodic / Semantic
    loop.py              # PLAN → ACT → OBSERVE → REFLECT loop
  providers/
    base.py              # ReasoningProvider ABC
    mock.py              # deterministic offline
    grok_build.py        # grok -p + --json-schema
    copilot.py           # copilot -p -s
    xai_api.py           # HTTP chat completions
    json_util.py         # parse CLI / model JSON
  schemas/               # Pydantic v2 models
  neo4j/                 # client, schema setup, Cypher helpers
tests/
```

## State machine

States (`HarnessState`):

`INIT` · `PLAN` · `ACT` · `OBSERVE` · `REFLECT` · `DONE` · `FAILED` · `BLOCKED`

```
INIT ──► PLAN ──► ACT ──► OBSERVE ⇄ ACT
              │              │
              └────► REFLECT ┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
          PLAN        ACT     DONE/FAILED/BLOCKED
```

- **Terminal:** `DONE`, `FAILED` (no outbound edges).
- **Illegal transitions** raise `IllegalTransitionError` (e.g. `INIT → ACT`, `ACT → PLAN`).
- Resume of a finished session rewrites state carefully in the CLI (e.g. back to `PLAN`).

Authoritative graph: `harness/state_machine.py` → `ALLOWED_TRANSITIONS`.

## Loop (`HarnessLoop`)

Owned sequence for one run (until terminal, budget, or iteration cap):

1. **INIT → PLAN** (if starting fresh).
2. **PLAN** — provider produces a `Plan` (goal + ordered steps); episode recorded.
3. **ACT** — next pending `PlanStep`; provider returns `{summary, success, …}`; episode.
4. **OBSERVE** — push observation into working memory; episode.
5. Branch:
   - more steps → **ACT**
   - reflection interval / plan complete → **REFLECT**
6. **REFLECT** — structured `Reflection`; stored as Reflection **and** Episode; may yield
   decisions into semantic memory; maps `next_action` → next state.

CLI flags: `--steps` / settings `NEO_LOOP_ITERATIONS` cap iterations **per CLI invocation**,
not the lifetime of the session.

## Budgets

`Budget` tracks:

- `max_steps` / `steps_used`
- `max_tokens` / `tokens_used` (when providers report usage)
- `reflect_every_n_actions` → forces REFLECT after N successful ACTs

Exhausted step budget → transition toward **FAILED** when legal.

## Memory (three layers)

| Layer | Lifetime | Storage | Role |
|-------|----------|---------|------|
| **Working** | Current process / turn | In-process (`InMemoryWorkingMemory`) | Goal + recent observations for prompts |
| **Episodic** | Session timeline | Neo4j `Episode`, `Reflection` | What happened, step by step |
| **Semantic** | Longer-lived | Neo4j `Decision`, `Artifact` | Stable facts, decisions, outputs |

`MemoryBundle` wires all three. The loop always writes episodes for plan/act/observe/reflect.

**Important (v0.1):** Working memory is not fully flushed as a first-class Neo4j subgraph;
session fields (`goal`, counters, state) are upserted on the `Session` node. Cross-session
semantic promotion and vector retrieval are extension points, not complete product features.

## Providers

See [providers.md](./providers.md). Contract:

```python
class ReasoningProvider(ABC):
    async def plan(...) -> Plan
    async def act(...) -> dict   # summary, success, …
    async def reflect(...) -> Reflection
```

Providers **must not** own the outer control loop.

## Session lifecycle

| CLI | Behavior |
|-----|----------|
| `neo start "task"` | Create `Session`, optionally run loop |
| `neo resume <id>` | Load from Neo4j, hydrate working memory from recent episodes, run loop |
| `neo status` | Active pointer or latest active; episodes |
| `neo end` | Best-effort final reflection; mark COMPLETED/FAILED; clear local active pointer |

Local convenience only: `~/.neo-harness/active_session.json`  
**Neo4j remains authoritative.**

## Agent packs

Named personas under `agents/<id>/` specialize **system prompts only**.
The harness still owns transitions, budgets, and memory writes.

| Piece | Role |
|-------|------|
| `AGENT.md` | Full persona (appended to every phase system prompt) |
| `prompts/plan.md` · `act.md` · `reflect.md` | Phase system prompts |
| `manifest.yml` | id, name, description, target_repos |
| CLI | `neo agents` · `neo start … --agent <id>` · `NEO_AGENT` |

Built-in: **`sysadmin`** — workstation / host IaC
(`wsl-shurtugal`, `L213196-WSL2-Ubuntu`, `shurtugal-lnx`).

Loader: `neo_harness.agents.loader` — search order:
`NEO_AGENTS_DIR` → repo `agents/` → `~/.neo-harness/agents`.

## Extension points

- New provider: implement `ReasoningProvider`, register in `providers/__init__.py`.
- New agent pack: add `agents/<id>/` with `AGENT.md` + `prompts/`; no code change required.
- Tools during ACT: `NEO_ACT_ALLOW_TOOLS=1` (CLI providers).
- Richer retrieval: extend `SemanticMemory.related` / full-text indexes already in schema.
- Parallel sub-agents: spawn only from harness-owned ACT handlers, not from free model drift.
