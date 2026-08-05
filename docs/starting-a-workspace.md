# Starting a new workspace

End-to-end process for embedding **neo-harness** in a project so engineers (and
AI agents) can run bounded PLAN→ACT→REFLECT jobs without opening the whole
monorepo in free-form chat.

**Principle:** the **workspace** owns code, packs, and jobs; **neo-harness** is
a library/CLI dependency — not a full project generator.

For a **full** project skeleton (docs, `src/`, AGENTS, CI), use
**[nebulus-forge](https://github.com/westailabs/nebulus-forge)** first, then this
guide (or `forge new … --neo auto`). Cross-links: [related-projects.md](./related-projects.md).

**Worked example root:** `~/projects/test`  
Substitute your own path everywhere.

### With Forge (optional)

```bash
export PATH="$HOME/.local/bin:$PATH"
forge new ~/projects/test -p base --no-interactive --neo auto
# then continue from §4 (configure .env) if neo ran; else §2–3
```

---

## Prerequisites

| Need | Why |
|------|-----|
| Git repository at the workspace root | `init-workspace` expects `.git` (or use `--force-no-git`) |
| Python **3.12+** | Project venv + package |
| Neo4j **5.x** over Bolt | Session / episode memory (use a **dedicated** DB) |
| neo-harness install | Editable lab clone and/or `pip` / `uv` |

There is often **no global `neo` on PATH**. Prefer:

```bash
# From a neo-harness clone (lab)
/path/to/neo-harness/.venv/bin/neo …

# After init (workspace runner)
./scripts/neo …
```

---

## 1. Create or enter the workspace

### New project

```bash
mkdir -p ~/projects/test
cd ~/projects/test
git init
echo "# test" > README.md
git add README.md && git commit -m "chore: initial commit"
```

### Existing repo (example)

```bash
cd ~/projects/test
git status -sb
```

---

## 2. Populate the harness embed

From the workspace root, run `init-workspace` using any installed neo CLI
(package venv, `uv run neo` from the neo-harness repo, etc.):

```bash
cd ~/projects/test

# Lab example (neo-harness checked out beside projects/)
~/projects/neo-harness/.venv/bin/neo init-workspace --pack workspace

# Or, from the neo-harness repo:
# cd ~/projects/neo-harness && uv run neo init-workspace ~/projects/test --pack workspace
```

| Flag | Meaning |
|------|---------|
| `--pack NAME` | Starter pack id → `agents/NAME/` |
| `--force` | Overwrite existing embed files |
| `--no-pack` | Skip starter agent pack |
| `--no-runner` | Skip `scripts/neo` |
| `--force-no-git` | Allow non-git directories |

### What gets created

```text
~/projects/test/
  env.neo.example          # copy → .env (never commit real secrets)
  requirements-neo.txt     # neo-harness dependency pin / install hint
  jobs/smoke-mock.md       # first task brief
  agents/workspace/        # starter pack (manifest + phase prompts)
  scripts/neo              # workspace runner (uses .venv-neo only)
  .gitignore               # + .venv-neo/, .env
  README.md                # + neo-harness section
```

CLI details: [init-workspace.md](./init-workspace.md).

---

## 3. Install neo-harness into a project venv

Workspace-local only — **not** a system-wide install.

```bash
cd ~/projects/test

python3 -m venv .venv-neo
.venv-neo/bin/pip install -U pip

# Lab: editable install of a local clone
.venv-neo/bin/pip install -e ~/projects/neo-harness

# Released / pin (when published or from git tag):
# .venv-neo/bin/pip install -r requirements-neo.txt
# .venv-neo/bin/pip install "neo-harness @ git+https://github.com/westailabs/neo-harness.git@v0.3.0"
```

`scripts/neo` can bootstrap `.venv-neo` on first run if the binary is missing,
but an explicit install is clearer for first-time setup.

---

## 4. Configure environment

```bash
cd ~/projects/test
cp env.neo.example .env
# edit .env — never commit it
```

Minimum settings:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password          # must match the running instance

NEO_PROVIDER=mock
NEO_POLICY_TIER=propose          # report | propose | apply
NEO_ACT_ALLOW_TOOLS=0
NEO_PROVIDER_FALLBACK=mock       # none = fail-closed on provider errors
NEO_AGENT=workspace
NEO_PROVIDER_CWD=/home/you/projects/test   # absolute path to this workspace
```

### Neo4j notes

- Harness **session memory** should use a **dedicated** Neo4j (lab Docker or
  remapped ports). Do not casually point at shared production graphs.
- Lab stacks sometimes expose Bolt on **non-default** host ports (e.g. `17687`).
  Set `NEO4J_URI` to match.
- **`neo init-db` does not start Neo4j.** If you see a timeout on
  `localhost:7687`, check `docker ps` port mappings — often the host Bolt port
  is **17687**. FAQ: [troubleshooting.md](./troubleshooting.md#faq--tip-init-db-times-out-on-localhost7687).

Fresh Docker (default ports):

```bash
docker run -d --name neo4j-harness \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5
```

Browser: http://localhost:7474

---

## 5. Health checks

```bash
cd ~/projects/test

./scripts/neo providers     # mock / grok_build / copilot / xai
./scripts/neo policy        # tier + path gates (.env should be denied)
./scripts/neo agents        # workspace pack (+ package sysadmin if present)
./scripts/neo init-db       # once per Neo4j instance (schema)
```

---

## 6. First job (mock — no model spend)

```bash
cd ~/projects/test

./scripts/neo start \
  --task-file jobs/smoke-mock.md \
  --agent workspace \
  -p mock

./scripts/neo status --all
./scripts/neo audit <session-id> -o /tmp/test-audit.json
```

---

## 7. Day-to-day work loop

```text
1. Branch (feat/* etc. — follow the workspace’s git policy)
2. Write jobs/<slug>.md   (goal, constraints, success criteria)
3. Choose policy: report → propose → apply
4. ./scripts/neo start --task-file jobs/<slug>.md --agent workspace -p <provider>
5. Human reviews git; commit / apply / push
6. Optional: neo audit <id> for review / InfoSec
```

### Examples

```bash
# Read-only assessment (tools forced off at report tier)
NEO_POLICY_TIER=report NEO_ACT_ALLOW_TOOLS=0 \
  ./scripts/neo start --task-file jobs/assess.md -a workspace -p grok_build

# Tools on, path policy enforced
NEO_POLICY_TIER=apply NEO_ACT_ALLOW_TOOLS=1 \
  ./scripts/neo start --task-file jobs/implement.md -a workspace -p grok_build
```

Providers: [providers.md](./providers.md). Policy: [policy.md](./policy.md).

---

## 8. Minimal cheat sheet

```bash
cd ~/projects/test
# init (from any neo CLI that has v0.3+)
/path/to/neo-harness/.venv/bin/neo init-workspace --pack workspace

python3 -m venv .venv-neo
.venv-neo/bin/pip install -e /path/to/neo-harness   # or pip install neo-harness

cp env.neo.example .env          # set NEO4J_* and NEO_PROVIDER_CWD
./scripts/neo init-db
./scripts/neo start --task-file jobs/smoke-mock.md --agent workspace -p mock
```

---

## 9. How this differs from a large monorepo

| | Small workspace (`~/projects/test`) | Large monorepo (e.g. org control plane) |
|--|-------------------------------------|------------------------------------------|
| Init | `neo init-workspace` | Often hand-embedded + org session bootstrap |
| Runner | `./scripts/neo` | Same pattern |
| Packs | `agents/workspace` (starter) | Domain packs (`platform`, …) + free-form profiles |
| AI session awareness | Optional | May inject harness status on session start |

Same harness package; different **flavor** in the workspace.

---

## Related docs

| Doc | Use |
|-----|-----|
| [related-projects.md](./related-projects.md) | **Forge vs neo-harness** composition |
| [init-workspace.md](./init-workspace.md) | CLI flags and file list |
| [workspace-embed.md](./workspace-embed.md) | Pack search order, thrift knobs |
| [quickstart.md](./quickstart.md) | Running neo-harness itself |
| [policy.md](./policy.md) | report / propose / apply |
| [threat-model.md](./threat-model.md) | Operator vs model boundaries |
| [troubleshooting.md](./troubleshooting.md) | Auth, venv, hung runs |
| [nebulus-forge](https://github.com/westailabs/nebulus-forge) | Full project scaffolder |
