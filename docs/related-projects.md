# Related projects

## nebulus-forge (project scaffolder)

| | **neo-harness** (this repo) | **[nebulus-forge](https://github.com/westailabs/nebulus-forge)** |
|--|------------------------------|------------------------------------------------------------------|
| **Job** | Agent **runtime**: PLAN→ACT→REFLECT, Neo4j memory, policy, audit | Project **scaffold**: docs, src/, AGENTS, CI, governance layout |
| **CLI** | `neo start`, `init-workspace`, `policy`, `audit` | `forge new`, `forge update`, `forge profiles` |
| **Creates** | Thin embed: `jobs/`, `scripts/neo`, packs, `env.neo.example` | Full tree: `docs/`, `workspace/scratchpad/`, hooks, tests, … |
| **Does not** | Generate full product skeletons (not a Forge) | Run long agent loops or own Neo4j sessions |

### Compose them

```text
forge new ~/projects/app -p base|fullstack --neo auto
        │
        ├─► full project tree (Forge)
        └─► neo init-workspace (if neo installed)
                 │
                 ▼
           harness-ready repo → ./scripts/neo start …
```

Manual compose:

```bash
# 1) Scaffold
forge new ~/projects/app -p base --neo off

# 2) Harness embed
cd ~/projects/app
neo init-workspace --pack workspace
# or: /path/to/neo-harness/.venv/bin/neo init-workspace --pack workspace
```

### Forge docs to read

| Link | Topic |
|------|--------|
| [nebulus-forge README](https://github.com/westailabs/nebulus-forge#readme) | Install `forge`, profiles, `--neo` hook |
| [creating-a-profile.md](https://github.com/westailabs/nebulus-forge/blob/master/docs/creating-a-profile.md) | Write custom Forge profiles |
| [Forge profiles](https://github.com/westailabs/nebulus-forge/blob/master/docs/profiles.md) | Shipped `base` / `fullstack` |
| [reevaluation-2026-08](https://github.com/westailabs/nebulus-forge/blob/master/docs/reevaluation-2026-08.md) | Layout decisions, Forge vs neo |

### neo-harness docs for Forge users

| Doc | Topic |
|-----|--------|
| [starting-a-workspace.md](./starting-a-workspace.md) | Embed harness without Forge |
| [init-workspace.md](./init-workspace.md) | `neo init-workspace` flags |
| [policy.md](./policy.md) | report / propose / apply |
