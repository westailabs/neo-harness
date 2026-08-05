# SysAdmin workflow — host IaC via CLI

End-to-end recipe for using **neo-harness** with the **`sysadmin`** agent pack
to change a **workstation / host IaC** repository (Ansible, packages, dotfiles,
Makefile), with optional live-home follow-up.

This is the practical “Jenkins-shaped” stage: **you own trigger + review + apply**;
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
| Declared host changes (alias, package pin, role task) | One-off “what does apt-up mean?” questions |
| You want episodes + resume in Neo4j | Pure design prose with no repo effect |
| Target is an IaC checkout (`wsl-shurtugal`, etc.) | Product app monorepo work (use another agent pack later) |

**Principle:** the agent edits **the repo** (source of truth). You review git,
then apply with the repo’s control plane (`make configure`, tagged playbook).
Do not treat the harness as silent root on the host.

---

## Prerequisites

1. **neo-harness** installed (venv / `uv sync`); CLI via `uv run neo` or `.venv/bin/neo`.
2. **Neo4j** reachable. Lab stacks often use non-default Bolt ports (example:
   Shurtugal memory Neo4j on **`17687`**, not `7687`). Match `.env` to the live DB:
   ```bash
   # example — copy from .env.example; never commit real .env
   NEO4J_URI=bolt://localhost:17687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=…   # must match the running instance
   ```
3. **`neo init-db`** once (or after schema changes).
4. **Provider** on `PATH` (`grok` or `copilot`) for real ACT; use `mock` for smoke only.
5. **Target IaC repo** on a non-protected branch (`session/*`, `feat/*`, `docs/*` — never commit
   straight to integration `main`/`master` of the *target* without policy).
6. **Agent pack** present: `agents/sysadmin/` (list with `neo agents`).

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
Target repo (e.g. wsl-shurtugal)
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

## Example: add a `foobar` alias (walkthrough)

Toy change: add a harmless shell alias so you can practice the full path without
running package upgrades.

### 1. Branch the target IaC repo

```bash
cd ~/projects/wsl-shurtugal   # or your host IaC tree
git status -sb
# work on session/* or feat/* per that repo’s policy
```

### 2. Write a task brief (markdown)

Task-as-file is the durable form (pipe into CLI until `--task-file` exists):

```bash
mkdir -p /tmp/neo-jobs
cat > /tmp/neo-jobs/foobar-alias.md <<'EOF'
# Task: add foobar zsh alias (SysAdmin / host IaC)

## Goal
Add a demo shell alias to the **IaC-controlled** zsh profile.

## Alias
```bash
alias foobar='echo "foobar: sysadmin harness demo"'
```

## Source of truth
- Repo: `dotfiles/.zshrc` under the IaC checkout (Ansible `dotfiles` role deploys it).
- Place the alias **inside** the marked local block if present:
  ```
  # >>> shurtugal local (safe to edit) >>>
  ...
  # <<< shurtugal local <<<
  ```
- One-line comment above the alias: demo alias for neo-harness SysAdmin workflow.

## Live home (optional but recommended)
- If `~/.zshrc` already exists and has the same local markers, add the **same**
  alias there so the operator can use it without an immediate full redeploy.
- **Do not** replace a richer live `~/.zshrc` with a thin repo baseline.

## Must not
- Run destructive host commands.
- Commit or push (operator owns git).
- Touch unrelated plugins or theme settings.

## Validation
- `grep -n foobar` on both `dotfiles/.zshrc` and `~/.zshrc` (if live was updated).
- Confirm placement inside local markers when those markers exist.
EOF
```

### 3. Start the harness session

```bash
cd ~/projects/neo-harness

# Schema (idempotent)
uv run neo init-db
# or: .venv/bin/neo init-db

NEO_ACT_ALLOW_TOOLS=1 \
NEO_PROVIDER_CWD="$HOME/projects/wsl-shurtugal" \
uv run neo start "$(cat /tmp/neo-jobs/foobar-alias.md)" \
  --provider grok_build \
  --agent sysadmin \
  --steps 15
```

Equivalent with env defaults (optional in `.env`, never commit secrets):

```bash
# NEO_AGENT=sysadmin
# NEO_PROVIDER_CWD=/home/…/wsl-shurtugal
# NEO_ACT_ALLOW_TOOLS=1
uv run neo start "$(cat /tmp/neo-jobs/foobar-alias.md)" -p grok_build -a sysadmin
```

List packs anytime:

```bash
uv run neo agents
```

### 4. Watch progress

While the first terminal may only print `running loop…`:

```bash
# second terminal
cd ~/projects/neo-harness
uv run neo status
uv run neo status --all
uv run neo status -s <session_id>
```

Healthy completion looks like: episodes for PLAN/ACT/OBSERVE/REFLECT, final
**state `DONE`**, **status `completed`**.

### 5. Operator review (required)

```bash
cd ~/projects/wsl-shurtugal
git diff -- dotfiles/.zshrc
grep -n foobar dotfiles/.zshrc ~/.zshrc

# Try live alias without redeploying whole profile
source ~/.zshrc
foobar
# → foobar: sysadmin harness demo
```

Expected shape in the managed local block:

```bash
# >>> shurtugal local (safe to edit) >>>
# …
# Demo alias for neo-harness SysAdmin workflow
alias foobar='echo "foobar: sysadmin harness demo"'
# <<< shurtugal local <<<
```

### 6. Apply via IaC (when you mean it)

For a real managed change, prefer the repo’s control plane after review:

```bash
# example — only when you intend to redeploy managed dotfiles
make configure
# or tagged: ansible-playbook … --tags dotfiles
```

**Caution:** if live `~/.zshrc` has diverged from the thin repo file, a blind
`copy` of the baseline can drop host-only customizations. Prefer:

1. Keep durable aliases in **repo** `dotfiles/.zshrc` (or templates), and/or  
2. Only patch the **local marker** section, and  
3. Reconcile live vs repo before mass redeploy.

### 7. Git policy (target + harness)

| Repo | Do |
|------|-----|
| **Target IaC** (`wsl-shurtugal`, …) | Commit on `session/*` / `feat/*` / `docs/*`; no direct `main`; no push of `session/*` without approval; no secrets |
| **neo-harness** | Feature or docs branch for harness changes; never commit `.env` / passwords; see [security-and-publishing.md](./security-and-publishing.md) |

The SysAdmin task should usually say **“do not commit or push”** so the harness
stops at a reviewable tree. You commit when satisfied.

---

## Task brief template (copy/paste)

```markdown
# Task: <one line>

## Goal
<what “done” means in the repo>

## Change
<exact alias / package / file snippet if known>

## Source of truth
- Paths under the IaC checkout (relative)
- Role / Makefile entry that applies it (if known)

## Placement / constraints
- Markers, tags, become user vs root, etc.

## Live host
- Update `~/…` only if needed; never clobber divergent profiles wholesale

## Must not
- Secrets, push, unbounded installs, whole-disk find

## Validation
- Commands the agent (or you) should run to prove the change
```

---

## Failure modes

| Symptom | Check |
|---------|--------|
| `Cannot connect to Neo4j` | URI/port/password vs running DB; `neo init-db` |
| Session DONE but no file change | `NEO_ACT_ALLOW_TOOLS=0` or wrong `NEO_PROVIDER_CWD` |
| Edits in neo-harness tree | CWD still neo-harness — set `NEO_PROVIDER_CWD` to IaC |
| Grok “max turns reached” | Raise `NEO_GROK_ACT_TURNS` / simplify task; inspect episodes |
| Live profile wiped later | Repo baseline thinner than `~/.zshrc` — reconcile before `make configure` |
| Agent not found | `neo agents`; pack under `agents/sysadmin/`; `NEO_AGENTS_DIR` |

More: [troubleshooting.md](./troubleshooting.md).

---

## What “good” looks like (checklist)

- [ ] Task brief is **bounded** (one concern)
- [ ] `--agent sysadmin` and correct `NEO_PROVIDER_CWD`
- [ ] Tools **on** only when you want edits
- [ ] Session ends **DONE** (or **BLOCKED** with a clear human ask)
- [ ] `git diff` on the IaC repo is minimal and correct
- [ ] You validated (grep / `source` / `make status` as appropriate)
- [ ] You decided commit / apply; harness did not invent push policy

---

## Lab note (real run)

A production-shaped run of this pattern (apt maintenance alias `apt-up` instead of
`foobar`) completed with `grok_build` + `sysadmin` against `wsl-shurtugal`: dual
edit of `dotfiles/.zshrc` and live `~/.zshrc` local markers, Neo4j session
**DONE**, operator left to commit. Use `foobar` above for safe rehearsal; swap
the alias body for real QoL aliases once the path is muscle memory.

---

## Next automation (out of scope here)

Timer or ticket triggers can wrap the same CLI (`neo start "$(cat job.md)" …`)
behind policy gates. The harness remains the **worker**; cron/Jira/CI remain the
**trigger**. See discussion in session notes / architecture agent packs — do not
put webhook auth inside the PLAN/ACT loop.
