# Using neo-harness in GCP

Treat **neo-harness as a change-management / ops agent shell on top of GCP**: it owns
**PLAN → ACT → OBSERVE → REFLECT**, writes an audit trail to **Neo4j**, and uses
Grok Build / Copilot / xAI only for reasoning. **GCP APIs, Terraform, Cloud Build, and
short-lived identities** keep real mutate authority—not free-form “the model is admin.”

**Deeper patterns** (Terraform phases, DBA migrations, identity matrix):
[GCP / Terraform / DBA](./gcp-terraform-dba.md)

**Related:** [Architecture](./architecture.md) · [Usage & demo](./usage-and-demo.md) ·
[Security & publishing](./security-and-publishing.md)

---

## High-value GCP uses

### 1. Design before change (tools off)

Sessions that produce apply order, blast radius, and IAM notes—no `gcloud` / TF applies.

```bash
NEO_ACT_ALLOW_TOOLS=0 \
  uv run neo start "Design private Cloud SQL + PSC for project X; no applies" \
  --provider grok_build --steps 10
```

Episodes + `Decision` nodes become the review packet for humans and PRs.

### 2. Read-only inventory & drift

Allowlisted scripts only: Asset Inventory, `gcloud sql` / `bq` / `gke list`,
`terraform plan` (no apply).

- **OBSERVE** records drift  
- **REFLECT** → replan / block / done  

### 3. Phased rollouts (dev → stage → prod)

One session per env (or one multi-day session with `neo resume`):

| Phase | Harness | GCP side |
|-------|---------|----------|
| PLAN | Ordered steps | Maps to TF workspaces / folders |
| ACT | One phase only | Cloud Build / TF apply via **script + SA** |
| OBSERVE | Health checks | SQL up, probes, error rates, IAM |
| REFLECT | go / no-go / BLOCKED | Human gate for prod |

### 4. Data plane & DBA (Cloud SQL, AlloyDB, BigQuery)

- Runbooks and migration timelines in Neo4j  
- Expand–contract / dual-write with `resume` across shifts  
- Weekly health reviews from scheduled sessions  

See also [GCP / Terraform / DBA](./gcp-terraform-dba.md#dba-environment-patterns).

### 5. Incident RCA

Read-only gather (Cloud Logging, Monitoring, Error Reporting) → evidence episodes →
root cause + follow-ups as `Decision` nodes. Better than chat scrollback for postmortems.

### 6. Policy / hygiene automation

Cron examples: instances without deletion protection, public IPs, missing labels →
tools-off or read-only ACT → digest from Reflections.

---

## How it sits in a GCP architecture

```text
  Trigger (cron / PR / ticket)
           │
           ▼
    neo start | resume          ← control flow + budgets
           │
     ┌─────┴─────┐
     ▼           ▼
  Provider    Neo4j           ← plan/act/reflect | audit memory
  (Grok/Copilot/xAI)
           │
           ▼
  Allowlisted scripts only
  (gcloud / terraform / bq / psql wrappers)
           │
           ▼
  GCP via WIF + narrow SAs
  (neo-readonly | neo-tf-dev | …)
           │
           ▼
  CI is apply authority
  (Cloud Build / GitHub Actions / Terraform Cloud)
```

| Piece | Role |
|-------|------|
| **neo-harness** | States, budgets, session continuity, Neo4j trail |
| **Scripts / domain skills** | Safe GCP / TF / DBA verbs |
| **CI + IAM** | Who may mutate; plan files; approvals |
| **Neo4j** | Ops / session memory—not application customer data |

---

## Safety rails (non-negotiable on GCP)

1. **`NEO_ACT_ALLOW_TOOLS=0`** by default for design.  
2. Mutate only through **named scripts**, not open shell.  
3. **Workload Identity Federation** + short-lived tokens; never long-lived keys in episodes or git.  
4. Separate SAs: read-only vs dev-apply; no org-admin for agent jobs.  
5. Low `--steps` on prod-ish jobs; fail → **FAILED** / **BLOCKED**, not endless retry.  
6. Redact secrets from episode content (resource names and plan hashes only).  

Details: [Security & publishing](./security-and-publishing.md).

---

## Thin path to try first

1. Tools-off: design private Cloud SQL + IAM.  
2. Human / CI runs `terraform plan`.  
3. `neo resume` with plan summary as observation.  
4. Reflect → Decisions in Neo4j.  
5. Later: allowlisted **plan** in **dev** only—still no unattended prod apply.  

That proves value (**memory + structure**) before any automated cloud mutation.

---

## What not to do

- Unbounded “fix prod” with tools on  
- Model-driven `terraform apply -auto-approve` on prod  
- Storing SA keys / DB passwords in Neo4j  
- One session for the whole org’s Terraform  

---

## Example CLI

```bash
# Advise only
NEO_ACT_ALLOW_TOOLS=0 \
  uv run neo start "Design phased rollout for private Cloud SQL" \
  --provider grok_build --steps 10

# Continue multi-day work
uv run neo resume <session_id> --provider copilot --steps 6

# Close out
uv run neo end
uv run neo status -s <session_id>
```

---

## Bottom line

In GCP, neo-harness is best as a **governed ops brain with memory**—design, inspect,
phase, hand off, and audit—while **GCP IAM + CI** remain the source of apply power.

For Terraform-specific phases, DBA runbooks, and anti-pattern detail, continue to
**[GCP / Terraform / DBA](./gcp-terraform-dba.md)**.
