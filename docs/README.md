# neo-harness documentation

Production-style **agent harness**: the model is a replaceable reasoning engine;
the harness owns control flow, typed memory (Neo4j), budgets, and reflection.

| Document | Contents |
|----------|----------|
| [Quick Start](./quickstart.md) | Install, venv, Neo4j, first `neo start` |
| [Architecture](./architecture.md) | State machine, memory layers, loop, ownership |
| [CLI reference](./cli.md) | `start` · `resume` · `status` · `end` · `init-db` |
| [Providers](./providers.md) | `mock` · `grok_build` · `copilot` · `xai` |
| [Neo4j](./neo4j.md) | Graph schema, constraints, Browser queries |
| [Configuration](./configuration.md) | Environment variables and defaults |
| [Usage & demo](./usage-and-demo.md) | How to use it well; 8-minute demo script |
| [GCP overview](./gcp.md) | How to use the harness on Google Cloud |
| [GCP / Terraform / DBA](./gcp-terraform-dba.md) | Ops patterns: plan-only, drift, migrations, identity |
| [Development](./development.md) | Layout, tests, extending the harness |
| [Troubleshooting](./troubleshooting.md) | Venv warnings, auth failures, “frozen” UI |
| [Security & publishing](./security-and-publishing.md) | Secrets, bloat, pre-push audit |

**Package version:** see `src/neo_harness/__init__.py` / `pyproject.toml`  
**Root overview:** [../README.md](../README.md)

**Do not commit** `.env`, `.venv`, or real passwords/API keys — see [Security & publishing](./security-and-publishing.md).

## Design principles (v0.1)

1. **Explicit state machine** — illegal transitions raise; the model cannot invent control flow.
2. **Neo4j is source of truth** — sessions, episodes, reflections, decisions, artifacts.
3. **Session continuity** — start → work → end/pause → resume with full graph context.
4. **Swappable providers** — Grok Build, Copilot, xAI API, or mock; harness stays the same.
5. **Forced reflection** — after every N actions, on error, plan complete, and session end.

## Mental model

```
┌─────────────────────────────────────────────────────────┐
│  CLI (neo)  →  HarnessLoop  →  StateMachine + Budget    │
│                     │                                    │
│         ┌───────────┼───────────┐                        │
│         ▼           ▼           ▼                        │
│     Provider    MemoryBundle   Neo4j                     │
│   plan/act/     Working /      Session · Episode · …     │
│   reflect       Episodic /                               │
│                 Semantic                                 │
└─────────────────────────────────────────────────────────┘
```

Free-form chat agents *drift*. This repo exists so planning, acting, and reflecting
are **code-enforced phases**, and every meaningful event is **queryable later**.
