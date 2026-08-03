# Using neo-harness in GCP / Terraform and DBA environments

How the harness fits **GCP + Terraform** and **DBA** work: controlled phases, durable
audit memory, multi-day continuity — without turning the model into an unsupervised
cloud admin.

**Start here for a GCP-only overview:** [Using neo-harness in GCP](./gcp.md)

**Related:** [Architecture](./architecture.md) · [Usage & demo](./usage-and-demo.md) ·
[Security & publishing](./security-and-publishing.md) · [Providers](./providers.md)

---

## Why a harness fits infra & DBA work

GCP/Terraform and DBA work fail more often from **drift, partial runs, and lost context**
than from “the model isn’t smart enough.” neo-harness is a good fit when you want:

| Need | How the harness helps |
|------|------------------------|
| Controlled phases | PLAN (what/risk) → ACT (one change) → OBSERVE (verify) → REFLECT (promote decisions) |
| Audit trail | Neo4j episodes/reflections = who/what/when for reviews & RCA |
| Multi-day jobs | Migrations, cutovers, multi-env rollouts via `neo resume` |
| Bounded risk | Step/token budgets, forced reflection, optional tools-off planning |
| Swappable brains | Copilot/Grok for reasoning; harness never lets the model own “apply all the things” |

**Rule of thumb:** use the harness as an **ops runbook executor with memory**, not as an
unsupervised cloud admin.

The harness does **not** replace Terraform state, Cloud Build, or DBA tooling. It
**orchestrates and remembers** human + scripted work around them.

---

## GCP / Terraform patterns

### 1. Plan-only change advisory (safest, tools off)

**Example task**

> Review `infra/envs/prod` for adding a Cloud SQL private IP. List blast radius, IAM,
> networking, and a phased apply order. No applies.

```bash
NEO_ACT_ALLOW_TOOLS=0 \
  uv run neo start "Review prod TF for private Cloud SQL IP; no applies" \
  --provider grok_build --steps 12
```

**Output in Neo4j:** plan steps, observations, reflections, `Decision` nodes
(e.g. “use PSC not public IP”, “apply network first”).

**Human** (or a gated pipeline) still runs `terraform plan` / `apply`.

### 2. Read-only inventory & drift detection (tools limited)

ACT may run **read** commands only (via allowlists you enforce outside the model):

- `terraform plan -detailed-exitcode` (no apply)
- `gcloud asset search-all-resources`, `gcloud sql instances list`
- `bq ls`, dataset/table metadata
- Compare desired (TF state / config) vs live

Harness **OBSERVE** records drift; **REFLECT** decides: replan, block (need human), or done.

### 3. Phased apply with hard gates (tools on, worktree + CI)

```text
PLAN   → ordered phases (network → IAM → SQL → app)
ACT    → one phase: terraform plan, then apply only if plan clean
OBSERVE→ health checks (Cloud SQL up, connectivity, IAM bindings)
REFLECT→ continue | block | fail
```

Wire **outside** the model:

- Working directory = TF root or generated worktree
- `NEO_PROVIDER_CWD` = that root
- Provider tools **must not** hold org-wide owner keys; use short-lived SA via Workload Identity Federation
- After each ACT: your script runs `terraform plan` / smoke tests; results are recorded as observations (inject via resume/context if needed)

Ideal automation flow:

```text
PR opened  → neo session (tools off) produces design + apply order
PR approved → CI applies with human-approved plan file
neo resume → records outcomes + decisions in Neo4j
```

### 4. Multi-env promotion (dev → staging → prod)

- Prefer **one session per env**, or one session with explicit phase episodes.
- **Episodic:** what was applied, plan hashes, errors.
- **Semantic:** standing rules (“prod requires CMEK”, “no public IPs on SQL”) as `Decision` nodes, reused on resume.

Resume after a multi-day rollout without re-explaining the world.

### 5. Incident / RCA for cloud outages

```text
PLAN    → hypotheses
ACT     → gather logs/metrics (read-only)
OBSERVE → evidence
REFLECT → root cause + follow-ups as Decisions
```

Better than chat scrollback when writing the postmortem.

---

## DBA environment patterns

### 1. Change ticket → structured runbook

> Prepare runbook for adding index on `orders(customer_id, created_at)` on Cloud SQL
> Postgres prod: prechecks, concurrent index, rollback, monitoring.

- **Tools off** → design note in episodes.
- **Tools on (dev only)** → run `EXPLAIN`, create index on non-prod, capture timings in OBSERVE.

### 2. Migration sessions (multi-hour / multi-day)

```text
PLAN    → backup → expand schema → dual-write check → cutover → contract
ACT     → one step only
OBSERVE → row counts, lag, lock waits, error rates
REFLECT → go / no-go / block for human
```

`neo resume <session_id>` is the continuity story for long migrations. Neo4j holds the
timeline across on-call handoffs.

### 3. Health & capacity reviews (scheduled)

```text
cron weekly
  → neo start "Weekly DBA review for instance X" --provider … --steps 8
  → ACT: collect stats (connections, bloat candidates, slow queries) via read scripts
  → REFLECT: open_questions + decisions
  → digest bot posts summary (optional)
```

### 4. Privilege / schema audit

Read `information_schema`, IAM DB users, TF `google_sql_user` vs live. REFLECT promotes
SOPs: “app role never owns tables”, “migrations only via CI SA”.

### 5. Break-glass with BLOCKED

When the model is unsure (destructive DDL, data wipe):

- Transition **BLOCKED**
- Human unblocks via `neo resume` after approval
- Episode trail shows why it stopped

Maps cleanly to change-management gates.

---

## Shaping the harness for this domain

### Provider & tools policy

| Mode | Tools | Use |
|------|-------|-----|
| **Advise** | Off (`NEO_ACT_ALLOW_TOOLS=0`) | Design, risk, runbooks |
| **Inspect** | Read-only scripts / allowlisted gcloud/bq/psql | Drift, health, RCA |
| **Change** | Narrow scripts only (`tf-plan.sh`, `tf-apply-phase.sh`, `migrate-step.sh`) | Never free-form `terraform apply` as first design |

Prefer **wrapping Terraform/DBA actions in scripts** the agent may call, rather than
unbounded shell from the model.

### Memory layers for ops

| Layer | Ops content |
|-------|-------------|
| **Working** | Current goal, last plan output, last health snapshot |
| **Episodic** | Each plan / apply / check / failure |
| **Semantic** | Standing decisions: naming, networking standards, “deletion protection on in prod”, index policies |

Over time Semantic memory becomes a **living ops SOP graph**, not a stale wiki page.

### Budgets that match risk

- Prod change sessions: **low** `--steps` / `NEO_LOOP_ITERATIONS`, **frequent** reflection (`NEO_REFLECT_EVERY_N` small)
- Tools on: short ACT turns; plans should include an explicit verification (OBSERVE) step
- Fail closed: budget exceed → **FAILED**, not “keep trying apply”

### Identity (GCP)

- Workload Identity Federation → short-lived tokens
- Separate SAs: e.g. `neo-readonly`, `neo-tf-dev` — never org-admin for agent jobs
- ACT scripts use the right SA; the model must not see long-lived JSON keys
- Keys never enter git (see [Security & publishing](./security-and-publishing.md))

### Where Neo4j sits

- Harness graph = **session / ops memory** (lab Neo4j or a dedicated ops-memory instance)
- Do **not** confuse with application data planes (customer Cloud SQL / AlloyDB data)
- Optional later: link `Session` → change ticket id / TF workspace name as properties

**Redaction:** do not store DB passwords, connection strings with secrets, or SA private
keys in episode `content`. Store handles, resource names, and plan hashes instead.

---

## Example automated workflows

### Terraform PR gate

```text
on pull_request (paths: infra/**)
  1. neo start tools-off: "Review TF diff for risk and apply order"
  2. CI: terraform fmt / validate / plan (+ OPA/policy if any)
  3. neo resume: attach plan summary as observation (scripted)
  4. On merge: separate pipeline applies; neo end with result episode
```

### DBA migration day

```text
T-0    neo start "Migration M-42 expand phase" --steps 6
T+n    neo resume <id>   # after each manual or scripted step
T-end  neo end           # or neo end --fail if rollback
```

### Nightly GCP hygiene (read-only)

```text
cron
  neo start "List SQL instances without deletion protection" --provider xai --steps 8
  ACT calls allowlisted inventory script only
  Decisions → weekly digest
```

---

## What *not* to do

- Unbounded “fix prod” or “optimize all queries” sessions with tools on
- Letting the model run `terraform apply -auto-approve` on prod without a plan file + policy gate
- Storing secrets in Neo4j episode payloads
- One mega-session for whole-org Terraform — split by workspace / env
- Treating `--provider mock` as a real change agent
- Auto-push of temporary feature branches (lab policy: merge locally to `develop`, then push `develop`)

---

## Mapping to a broader ecosystem

| Component | Role |
|-----------|------|
| **neo-harness** | Session lifecycle, state machine, Neo4j audit memory |
| **Domain scripts / skills** | Safe interfaces to BigQuery, Cloud SQL, TF modules, etc. |
| **CI/CD** (Cloud Build, GitHub Actions, Terraform Cloud, …) | Actual apply authority |
| **Provider** (Grok Build / Copilot / xAI) | Draft plans, interpret errors, write runbooks **inside** harness states |

---

## Thin vertical slice (try first)

1. **Tools-off** session: “Design TF + IAM for a private Cloud SQL instance.”
2. Human implements / CI runs `terraform plan`.
3. **Resume** session with plan output attached (paste or script-injected observation).
4. **Reflect** → `Decision` nodes in Neo4j.
5. Only later: allowlisted `terraform plan` (dev) inside ACT — still no unattended prod apply.

That proves value (**memory + structure**) before any automated cloud mutation.

---

## Example CLI snippets

```bash
# Advise only
NEO_ACT_ALLOW_TOOLS=0 \
  uv run neo start "Design phased TF apply for private Cloud SQL" \
  --provider grok_build --steps 10

# Multi-day migration continuity
uv run neo resume <session_id> --provider copilot --steps 6

# End after cutover or rollback
uv run neo end
uv run neo end --fail

# Inspect trail
uv run neo status -s <session_id>
uv run neo status --all
```

Browser (audit): see [Neo4j](./neo4j.md) for Cypher examples on `Session` / `Episode` / `Reflection`.

---

## Bottom line

In GCP/Terraform and DBA worlds, neo-harness shines as a **change-management agent shell**:

- Plan and verify in **code-enforced phases**
- Persist every step for **audit and handoff**
- Keep destructive power in **scripts, CI, and short-lived identities** — not free-form model control
