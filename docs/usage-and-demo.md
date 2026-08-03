# Usage and demo

This page answers: **What is a good way to use this harness?** and **How do I demo it?**

## Mental model

**neo-harness is not another chat window.**

| Free-form agent chat | neo-harness |
|----------------------|-------------|
| Model invents next steps | Code enforces PLAN / ACT / OBSERVE / REFLECT |
| History = scrollback | History = Neo4j episodes + reflections |
| Hard to resume days later | `neo resume <session_id>` with full graph context |
| Provider owns the loop | Harness owns the loop; provider only reasons |

Use the harness when you care about **traceability, budgets, and multi-day continuity**.  
Use plain Grok/Copilot when you want a fast one-off answer.

## Good day-to-day patterns

| Pattern | When | How |
|---------|------|-----|
| **Design / spike** | ADRs, design notes, architecture | `NEO_ACT_ALLOW_TOOLS=0`, `copilot` or `grok_build` |
| **Repo work** | Implement something in a checkout | `NEO_ACT_ALLOW_TOOLS=1`, set `NEO_PROVIDER_CWD`, short task |
| **Continuity** | Start Friday, resume Monday | `start` → pause/`end` → `resume <id>` |
| **Audit** | “What did we decide?” | `status -s <id>`, Neo4j Browser |
| **Smoke / CI** | Is wiring healthy? | `--provider mock` |

### Task phrasing that works

**Good**

- “Draft a short design note for typed Working/Episodic/Semantic memory”
- “List risks of adding vector retrieval to SemanticMemory”
- “Propose a 5-step plan to add live progress to the CLI”

**Bad**

- “Build the whole platform” (unbounded; burns turns and money)
- Empty or vague one-word tasks

### Provider choice

| Provider | Best for | Speed / cost |
|----------|----------|--------------|
| `mock` | Structure-only demos, tests | Instant, free |
| `grok_build` | Lab default, structured JSON | ~20–60s+ per call |
| `copilot` | Repo-aware reasoning | Similar |
| `xai` | Pure HTTP API | Depends on key |

### Tools on vs off

```bash
NEO_ACT_ALLOW_TOOLS=0   # design/demo: reason + record episodes (safer)
NEO_ACT_ALLOW_TOOLS=1   # ACT may edit files / run shell (powerful)
```

With tools **off**, you still get rich episode summaries; you may not get new files on disk.  
With tools **on**, use a branch or worktree.

### Weekly recipe

```bash
cd ~/projects/neo-harness
source .venv/bin/activate   # or always uv run

# Open work
uv run neo start "…" --provider grok_build

# Check
uv run neo status
uv run neo status --all

# Pause
uv run neo end
# or Ctrl+C mid-run, then later:
uv run neo resume <session_id> --provider grok_build
```

While a long run is silent on stdout:

```bash
# second terminal
uv run neo status -s <session_id>
```

---

## Demo guide (~8 minutes)

Goal: show **control flow**, **real reasoning**, **durable memory**, **continuity**.

### 0. Setup (30s)

```bash
cd ~/projects/neo-harness
uv sync --all-extras
# .env with valid NEO4J_PASSWORD; Neo4j healthy on :7687
uv run neo init-db
```

### 1. Control flow is code (2 min) — mock

```bash
uv run neo start "Explain the PLAN→ACT→REFLECT loop in one paragraph" --provider mock
```

**Talking points**

- Explicit transitions printed at the end  
- Session ends **DONE**  
- Model never jumped `INIT → ACT` illegally  

### 2. Real reasoning + durable memory (4 min) — copilot or grok_build

```bash
NEO_ACT_ALLOW_TOOLS=0 \
  uv run neo start "Draft a short design note for typed Working/Episodic/Semantic memory" \
  --provider copilot
```

While it runs (terminal may only show `running loop…`):

```bash
watch -n 5 'uv run neo status --all'
# or
uv run neo status -s <session_id>
```

**Talking points**

- Harness owns state; provider only answers inside PLAN / ACT / REFLECT  
- Episodes appear as work progresses  
- Forced reflection after N actions  

Real lab result (example): session completed with multiple actions and reflections
stored as Episode + Reflection nodes (e.g. design-note task with 5 actions / 2 reflections).

### 3. Source of truth is Neo4j (1–2 min)

Browser: http://localhost:7474

```cypher
MATCH (s:Session)
RETURN s.id, s.task, s.status, s.state, s.action_count, s.reflection_count
ORDER BY s.updated_at DESC
LIMIT 5
```

```cypher
MATCH (s:Session {id: $sessionId})-[:HAS_EPISODE]->(e:Episode)
RETURN e.kind, e.state, left(e.summary, 120) AS summary
ORDER BY e.created_at
```

### 4. Session continuity (1 min)

```bash
uv run neo start "Spike: promote Decisions to shared semantic store" --provider mock --no-run
uv run neo status
uv run neo resume <session_id> --provider mock
uv run neo end
```

**Story:** open a session, walk away, resume with full graph context.

### Demo narrative (one slide)

1. **Problem:** Free-form agents drift; chat history is not a memory system.  
2. **Harness:** State machine + budgets + forced reflection.  
3. **Memory:** Working · Episodic · Semantic in Neo4j.  
4. **Model:** Swappable (`mock` / `grok_build` / `copilot` / `xai`).  
5. **Proof:** Live `neo start` + Browser + `resume`.

### What not to demo yet

- Unbounded “build everything” tasks  
- Tools-on ACT against a precious main branch without a worktree  
- Expecting polished markdown files when `NEO_ACT_ALLOW_TOOLS=0`  

### Optional second demo (tools on)

```bash
NEO_ACT_ALLOW_TOOLS=1 \
  uv run neo start "Write docs/memory-design.md summarizing typed memory layers" \
  --provider grok_build
```

Show the new file **and** the episode trail.

---

## Interpreting a completed session

```bash
uv run neo status -s <uuid>
uv run neo status --all
```

| Field | Meaning |
|-------|---------|
| `status` | Session lifecycle: active / completed / failed / blocked |
| `state` | Harness state machine position |
| `steps / actions / reflections` | Loop counters |
| Episodes | Ordered audit trail (plan, action, observation, reflection) |

---

## Domain: GCP, Terraform, DBA

For change management, drift, migrations, and cloud RCA patterns, see
**[GCP / Terraform / DBA](./gcp-terraform-dba.md)**.

## FAQ

**Why does `neo status` say no active session after a successful run?**  
Terminal `DONE` clears the local active pointer. Use `--all` or `-s <id>`.

**Is a quiet terminal hung?**  
Usually no — real providers are slow. Confirm with `ps` / `status -s` / Neo4j.

**Mock vs real for demos?**  
Mock for structure; one real provider run for intelligence. Don’t make the audience stare at silence without a second-terminal status view.

**Can I use Grok Build and Copilot together?**  
Not in one loop simultaneously. Pick one provider per run; compare sessions side by side in Neo4j.
