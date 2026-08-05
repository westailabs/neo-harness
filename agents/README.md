# neo-harness agents

Named **agent packs** specialize the harness PLAN / ACT / REFLECT system prompts
for a class of work. The harness still owns the state machine; the agent only
shapes how the model reasons inside each state.

## Layout

```
agents/
  <id>/
    AGENT.md              # Full persona (human-facing / optional full mode)
    manifest.yml          # name, description, target_repos
    prompts/
      plan.md             # PLAN system prompt
      act.md              # ACT system prompt
      reflect.md          # REFLECT system prompt
      persona.short.md    # Preferred short persona (token thrift)
```

A directory is a pack only if it has **`manifest.yml`** or phase prompts under
`prompts/`. Free-form `AGENT.md`-only profiles are ignored.

## Built-in packs

| Id | Use for |
|----|---------|
| `sysadmin` | Workstation / host IaC repos (Ansible, packages, dotfiles, Makefile control plane) |

## CLI / env

```bash
# Explicit agent for a workstation IaC task
NEO_ACT_ALLOW_TOOLS=1 \
  NEO_PROVIDER_CWD=~/path/to/your-host-iac \
  uv run neo start "Add ripgrep to apt manifest and role" \
    --provider grok_build \
    --agent sysadmin

# Default via env
export NEO_AGENT=sysadmin
```

List packs:

```bash
uv run neo agents
```

Optional search path (prepended after workspace cwd):

```bash
export NEO_AGENTS_DIR=~/.neo-harness/agents
```

## Target repos (SysAdmin class)

Patterns this agent is built for:

- Ansible + `packages/` + roles + Makefile + environment docs
- Dotfiles managed from the repo
- Optional local compose under `services/`

Do **not** use `sysadmin` as the default for product app monorepos unless the task
is host/IaC related. Add a workspace pack under `$NEO_PROVIDER_CWD/agents` for
product work.
