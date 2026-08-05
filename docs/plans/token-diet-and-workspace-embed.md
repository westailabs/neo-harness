# Plan: token diet + workspace embed

**Status:** largely implemented on develop · lab-validated  
**Related docs:** [sysadmin-workflow.md](../sysadmin-workflow.md), [architecture.md](../architecture.md), [../agents/README.md](../../agents/README.md)

---

## 1. Product direction (locked)

| Principle | Meaning |
|-----------|---------|
| **Harness ≠ workspace** | This package is a **thin runner**. Consumer monorepos and IaC trees are **source of truth + flavor**, not the harness. |
| **Core stays a library** | Publish **neo-harness** as a library/CLI. Downstream projects **pull a pin** and add packs/policy only. |
| **Do not fork the brain** | Wrong path: fork neo-harness for org features. Right path: **depend + private packs + thin runner**. |
| **Workspace bootstrap** | Clone workspace → bootstrap installs `neo-harness` + deps → run constrained jobs. |
| **Cheap by design** | Short system contracts, tools mainly in ACT, small task briefs, durable memory in Neo4j instead of reloading monorepo context. |
| **Distribution** | Lab: editable install. Shared: **pip / private index** (`neo-harness==x.y`). Packs may ship separately or live in the workspace. |

### Mental model

```text
WORKSPACE  (git clone)
  · code, docs, IaC, optional agents/ + jobs/
  · bootstrap → venv + pip install neo-harness
        │
        ▼
HARNESS  (package)
  · state machine, budgets, providers, neo CLI
  · NEO_PROVIDER_CWD = workspace root
  · packs: built-in and/or workspace agents/
        │
        ▼
Human / CI
  · review diff · apply (make configure / pipeline)
```

### What a harness is (one line)

Code-owned **PLAN → ACT → OBSERVE → REFLECT** with budgets and typed memory; the model only reasons inside a state. A configured monorepo with `AGENTS.md` is a **workspace**, not a harness—even when it feels agentic.

### Token thesis

Opening a free-form agent on a fat monorepo burns tokens on orientation every session.  
Running a **bounded job** through neo-harness should cost a **fraction** of that: small pack prompts, one task, few acts, sparse reflection.

---

## 2. Implementation fence (shipped themes)

### Track 1 — Token diet (core)

| Item | Outcome |
|------|---------|
| Short model persona | Packs prefer `prompts/persona.short.md` |
| Phase prompt budgets | Settings for max chars; shorter episode/observation tails |
| PLAN / REFLECT cheap | Tools off; single-turn style for those phases on CLI providers |
| Smarter reflect cadence | Skip interval reflect on short all-green plans |
| Status truncation | CLI status shows short task summary |

### Track 2 — Workspace embed

| Item | Outcome |
|------|---------|
| CWD-aware agent discovery | `$NEO_PROVIDER_CWD/agents`, then `NEO_AGENTS_DIR`, then package packs |
| `--task-file` | First-class task input |
| Docs: consume, don’t fork | Package pin + bootstrap + workspace `agents/` |
| Lab embed stub | Consumer workspace requirements / runner pattern |

### Track 3 — Git / hygiene

- Implementation on feature branches; merge to `develop`
- Never commit `.env`, passwords, or API keys
- No push of unfinished local-only branches without intent

---

## 3. Explicitly out of scope (this fence)

- Private-index CI publish pipeline (design OK; implement later)
- Ticket webhooks and enterprise lifecycle
- Absorbing neo-harness into a product monorepo without boundary review
- Org-specific code or employer IP in this tree
- Prompt-cache provider work, multi-model plan routing (later)

---

## 4. Success picture

> A workspace pulls a pin (or editable install). Bootstrap installs `neo`.  
> Jobs use short packs and cheap PLAN/REFLECT.  
> Downstream orgs only add flavor (packs, policy, triggers)—core stayed a library.  
> Demo: fraction of the tokens of “open the whole monorepo agent.”

---

## 5. Later roadmap

| Phase | Themes |
|-------|--------|
| **Publish** | `python -m build` + PyPI/private index; semver tags |
| **Automation edge** | Thin external runner (cron/ticket → task file → `neo start\|resume`) |
| **Policy packs** | Path allowlists, tier 0/1/2 (report / propose / apply) |
| **Deeper token work** | Static system prefix caching; harness-owned apply_patch tools |

---

## 6. Decision log (short)

| Date | Decision |
|------|----------|
| 2026-08-04 | Harness is library + CLI; workspaces consume it. |
| 2026-08-04 | Corp = pull pin + flavor; do not fork core for org features. |
| 2026-08-04 | Configured monorepo ≠ harness; token demo is bounded jobs vs fat chat. |
| 2026-08-04 | Build fence = token diet + workspace embed. |
