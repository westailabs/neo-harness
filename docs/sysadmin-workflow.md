# SysAdmin workflow — host IaC via CLI

End-to-end recipe for using **neo-harness** with the **`sysadmin`** agent pack
to change a **workstation / host IaC** repository (Ansible, packages, dotfiles,
Makefile), with optional live-home follow-up.

This is the practical “CI-shaped” stage: **you own trigger + review + apply**;
the harness owns **PLAN → ACT → OBSERVE → REFLECT** and Neo4j memory.

| Related | |
|---------|--|
| Agent pack | [`../agents/sysadmin/`](../agents/sysadmin/) · [agents README](../agents/README.md) |
| CLI | [cli.md](./cli.md) (`--agent`, `neo agents`) |
| Config | [configuration.md](./configuration.md) (`NEO_AGENT`, `NEO_PROVIDER_CWD`, tools) |
| Usage patterns | [usage-and-demo.md](./usage-and-demo.md) |

---

## When to use this

| Use | Skip / use free-form chat instead |
|-----|-----------------------------------|
| Declared host changes (alias, package pin, role task) | One-off “what does this Makefile target mean?” questions |
| You want episodes + resume in Neo4j | Pure design prose with no repo effect |
| Target is an IaC checkout | Product app monorepo work (use another agent pack later) |

**Principle:** the agent edits **the repo** (source of truth). You review git,
then apply with the repo’s control plane (`make configure`, tagged playbook).
Do not treat the harness as silent root on the host.

---

## Prerequisites

1. **neo-harness** installed (venv / `uv sync`); CLI via `uv run neo` or `.venv/bin/neo`.
2. **Neo4j** reachable. Match `.env` to the live DB (default Docker is
   `bolt://localhost:7687`; some labs map Bolt to other host ports):
   ```bash
   # example — copy from .env.example; never commit real .env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=…   # must match the running instance
   ```
3. **`neo init-db`** once (or after schema changes).
4. **Provider** on `PATH` (`grok` or `copilot`) for real ACT; use `mock` for smoke only.
5. **Target IaC repo** on a non-protected branch per that repo’s policy
   (feature branches; avoid committing straight to `main` without review).
6. **Agent pack** present: built-in `sysadmin` (list with `neo agents`).

---

## Mental model (roles)

```text
You (operator)
  · write task (markdown or string)
  · set branch on target IaC
  · review diff / apply / commit
        │
        ▼
neo-harness  --agent sysadmin
  · state machine + budgets
  · Neo4j episodes
  · injects SysAdmin PLAN/ACT/REFLECT prompts
        │
        ▼
Provider (e.g. grok_build)  cwd = NEO_PROVIDER_CWD
  · reasons + tools during ACT when NEO_ACT_ALLOW_TOOLS=1
        │
        ▼
Target repo (your host IaC checkout)
  · packages/ · roles/ · dotfiles/ · docs/
```

| Env / flag | Meaning |
|------------|---------|
| `--agent sysadmin` / `NEO_AGENT=sysadmin` | Load SysAdmin pack |
| `NEO_PROVIDER_CWD=/path/to/iac` | Tools run **in the IaC checkout** |
| `NEO_ACT_ALLOW_TOOLS=1` | ACT may edit files / run shell |
| `NEO_ACT_ALLOW_TOOLS=0` | Plan/reflect only (no durable host/repo edits) |
| `--steps N` | Cap loop iterations **this invocation** |

---

## Example: add a demo shell alias (walkthrough)

Toy change: add a harmless shell alias so you can practice the full path without
running package upgrades.

### 1. Branch the target IaC repo

```bash
cd ~/path/to/your-host-iac
git status -sb
# work on a feature/docs branch per that repo’s policy
```

### 2. Write a task brief (markdown)

```bash
mkdir -p /tmp/neo-jobs
cat > /tmp/neo-jobs/demo-alias.md <<'EOF'
# Task: add demo zsh alias (SysAdmin / host IaC)

## Goal
Add a demo shell alias to the **IaC-controlled** zsh profile.

## Alias
```bash
alias neo_demo='echo "neo_demo: sysadmin harness demo"'
```

## Source of truth
- Repo: `dotfiles/.zshrc` under the IaC checkout (or the path your roles deploy).
- Prefer a marked local block if the file has one, so upstream templates stay clean.

## Constraints
- No secrets
- Prefer repo edit over only changing live `~/.zshrc`
- Leave apply (`make configure` / tagged playbook) for the operator unless asked

## Success
- Alias present in repo dotfiles
- Optional: note how operator applies to live home
EOF
```

### 3. Run the harness

```bash
cd /path/to/neo-harness
export NEO_PROVIDER_CWD="$HOME/path/to/your-host-iac"
export NEO_ACT_ALLOW_TOOLS=1

uv run neo start --task-file /tmp/neo-jobs/demo-alias.md \
  --provider grok_build \
  --agent sysadmin
```

Mock smoke (no model):

```bash
uv run neo start --task-file /tmp/neo-jobs/demo-alias.md -p mock -a sysadmin
```

### 4. Review and apply

```bash
cd ~/path/to/your-host-iac
git diff
# apply via your control plane, then verify:
# grep -n neo_demo dotfiles/.zshrc
# neo_demo
```

---

## Git / safety

| Surface | Guidance |
|---------|----------|
| **Harness repo** | No secrets in commits; keep `.env` local |
| **Target IaC** | Feature branches; no secrets; operator owns push |
| **Live home** | Prefer deploying from repo; avoid permanent one-off host state |

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Neo4j auth failure | Password / URI vs running container |
| Pack not listed | `uv run neo agents`; built-in `sysadmin` ships with the package |
| Tools did nothing | `NEO_ACT_ALLOW_TOOLS=1` and correct `NEO_PROVIDER_CWD` |
| Wrong files edited | CWD must be the IaC root, not neo-harness |

See also [troubleshooting.md](./troubleshooting.md).
