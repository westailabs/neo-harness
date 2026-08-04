# neo-harness agents

Named **agent packs** specialize the harness PLAN / ACT / REFLECT system prompts
for a class of work. The harness still owns the state machine; the agent only
shapes how the model reasons inside each state.

## Layout

```
agents/
  <id>/
    AGENT.md              # Full persona (also prepended to phase prompts)
    manifest.yml          # name, description, target_repos
    prompts/
      plan.md             # PLAN system prompt
      act.md              # ACT system prompt
      reflect.md          # REFLECT system prompt
```

## Built-in packs

| Id | Use for |
|----|---------|
| `sysadmin` | Workstation / host IaC repos (Ansible, packages, dotfiles, Makefile control plane) |

## CLI / env

```bash
# Explicit agent for a workstation IaC task
NEO_ACT_ALLOW_TOOLS=1 \
  NEO_PROVIDER_CWD=~/projects/wsl-shurtugal \
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

Optional search path (prepended):

```bash
export NEO_AGENTS_DIR=~/.neo-harness/agents
```

## Target repos (SysAdmin class)

Patterns this agent is built for:

- `wsl-shurtugal` — personal WSL2 Ubuntu IaC
- `L213196-WSL2-Ubuntu` — work WSL2 Ubuntu IaC (reference; do not mix secrets)
- `shurtugal-lnx` — bare-metal / desktop Ubuntu recovery suite
- Similar: Ansible + `packages/` + roles + Makefile + docs/environment facts

Do **not** use `sysadmin` as the default for product app monorepos unless the task
is host/IaC related.
