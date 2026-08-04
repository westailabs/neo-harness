# Plan: token diet + workspace embed

**Status:** agreed direction · ready to implement  
**Owner:** West AI Labs  
**Repo:** `neo-harness` (this tree)  
**Working branch (implementation):** `feat/token-diet-and-embed`  
**Related docs:** [sysadmin-workflow.md](../sysadmin-workflow.md), [architecture.md](../architecture.md), [../agents/README.md](../../agents/README.md)

---

## 1. Product direction (locked)

| Principle | Meaning |
|-----------|---------|
| **Harness ≠ workspace** | This package is a **thin runner**. Monorepos (`west_ai_labs`, `oap-*`, `wsl-shurtugal`) are **source of truth + flavor**, not the harness. |
| **WAL builds core** | Develop and publish **neo-harness** as a library/CLI. Downstream (OAP, other workspaces) **pull a pin** and add packs/policy only. |
| **Do not fork the brain** | Wrong path: fork neo-harness to add org features. Right path: **depend + private packs + thin runner**. |
| **Workspace bootstrap** | Clone workspace → bootstrap installs `neo-harness` + deps → run constrained jobs. Bob’s your uncle for the runner path. |
| **Cheap by design** | Short system contracts, tools mainly in ACT, small task briefs, durable memory in Neo4j instead of reloading monorepo context. |
| **Distribution** | Lab: editable install. Corp: **pip from JFrog / private index** (`neo-harness==x.y`). Packs may ship separately or live in the workspace. |

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

### Token thesis (demo)

Opening a free-form agent on a fat monorepo burns tokens on orientation every session.  
Running a **bounded job** through neo-harness should cost a **fraction** of that: small pack prompts, one task, few acts, sparse reflection.

---

## 2. Implementation fence — “tonight” / next coding session

Ship a **slice**, not the entire backlog.

### Track 1 — Token diet (core)

| # | Item | Outcome |
|---|------|---------|
| 1 | **Short model persona** | Packs prefer `prompts/persona.short.md` (or capped text) for PLAN/ACT/REFLECT. Full `AGENT.md` remains human-facing / optional full mode. |
| 2 | **Phase prompt budgets** | Settings for max chars; shorter episode/observation tails in prompts. |
| 3 | **PLAN / REFLECT cheap** | Tools always off; `max_turns=1` (or equivalent) for those phases on CLI providers. |
| 4 | **Smarter reflect cadence** | Skip interval reflect on short all-green plans; still reflect on plan complete, error, session end. |
| 5 | **Status truncation** | CLI status shows short task summary; full brief not dumped every time. |

**Done when:** tests green; short jobs no longer inject full `AGENT.md` on every phase by default; prompt/context size measurably smaller for sysadmin-class tasks.

### Track 2 — Workspace embed

| # | Item | Outcome |
|---|------|---------|
| 6 | **CWD-aware agent discovery** | Search order includes `$NEO_PROVIDER_CWD/agents`, then `NEO_AGENTS_DIR`, then package/repo packs. |
| 7 | **`--task-file` / stdin** | First-class task input (not only quoted string / shell `$(cat …)`). |
| 8 | **Docs: consume, don’t fork** | Document package pin + bootstrap + workspace `agents/`; link this plan and sysadmin workflow. |
| 9 | **Lab embed stub** | In a consumer workspace (prefer `wsl-shurtugal`): requirements or Makefile target for lab install path; JFrog called out as future. |

**Done when:** documented one-liner can run with cwd/agents from a workspace without living only inside the neo-harness git tree.

### Track 3 — Git / hygiene

| # | Item |
|---|------|
| 10 | Implementation on **`feat/token-diet-and-embed`** (not silent commits only on `master`). |
| 11 | Never commit `.env`, passwords, or API keys. |
| 12 | No push unless explicitly requested. |

---

## 3. Explicitly out of scope (this fence)

- JFrog/Artifactory CI publish pipeline (design OK; implement later)
- Jira / ServiceNow webhooks and ticket lifecycle
- Jenkins (or other CI) as a productized orchestrator inside this repo
- Harness-owned generic patch-tool framework
- Absorbing neo-harness into `west_ai_labs/products/` without product-boundary review
- OAP-specific code or employer IP in this tree
- Prompt-cache provider work, multi-model plan routing (nice-to-haves after fence)

---

## 4. Suggested order of battle

```text
1. Create/switch to feat/token-diet-and-embed
   (carry uncommitted agent-pack work if not already merged)
2. Track 1 — token diet + tests
3. Track 2 — discovery + --task-file + docs
4. Optional: wsl-shurtugal bootstrap stub
5. pytest; mock (and optional grok) smoke
6. Stop; summarize shipped vs next
```

### Optional if fence finishes early

- `--profile cheap` preset (steps, reflect interval, act turns)
- Persist `agent_id` on `Session` for resume
- Pointer note only under `west_ai_labs` docs (no monorepo absorb)

---

## 5. Related uncommitted / prior work (context)

Already exercised or staged in lab (may land on feat branch separately or with this fence):

| Item | Notes |
|------|--------|
| Agent pack loader + `neo agents` | `src/neo_harness/agents/`, `agents/sysadmin/` |
| SysAdmin pack | Persona + plan/act/reflect prompts |
| Docs: sysadmin foobar workflow | Branch `docs/sysadmin-workflow` · commit documenting CLI recipe |
| Real run | `apt-up` alias via `--agent sysadmin` + `NEO_PROVIDER_CWD=wsl-shurtugal` |

Land **agent packs + loader** before or with Track 1 so short-persona work has a pack to attach to.

---

## 6. Success picture

After this fence, we can say:

> A workspace pulls a pin (or editable install). Bootstrap installs `neo`.  
> Jobs use short packs and cheap PLAN/REFLECT.  
> Downstream orgs only add flavor (packs, policy, triggers)—core stayed a library.  
> Demo: fraction of the tokens of “open the whole monorepo agent.”

---

## 7. Later roadmap (not this fence)

| Phase | Themes |
|-------|--------|
| **Publish** | `python -m build` + twine/JFrog; semver tags; consumer `pip install neo-harness==x.y` |
| **Automation edge** | Thin external runner (cron/ticket → task file → `neo start|resume`); exit codes; dedupe by external id |
| **Policy packs** | Path allowlists, tier 0/1/2 (report / propose / apply) |
| **Product boundary** | Whether/when harness is a Nebulus SKU vs lab platform dependency (`west_ai_labs` product docs) |
| **Deeper token work** | Static system prefix caching; harness-owned apply_patch tools; plan rehydrate without full replan |

---

## 8. References

| Doc | Use |
|-----|-----|
| [SysAdmin workflow](../sysadmin-workflow.md) | Host IaC CLI recipe (foobar / apt-up class) |
| [Architecture](../architecture.md) | State machine, memory, agent packs |
| [Usage & demo](../usage-and-demo.md) | When to use harness vs free chat |
| [Security & publishing](../security-and-publishing.md) | Secrets, pre-push audit |
| WAL monorepo | `~/projects/west_ai_labs` — company control plane; **not** this harness |

---

## 9. Decision log (short)

| Date | Decision |
|------|----------|
| 2026-08-04 | Harness is library + CLI; workspaces consume it. |
| 2026-08-04 | OAP/corp = pull pin + flavor; do not fork core for org features. |
| 2026-08-04 | Configured monorepo ≠ harness; token demo is bounded jobs vs fat chat. |
| 2026-08-04 | Next build fence = token diet + workspace embed only. |
