# Policy packs — tiers and path gates

InfoSec control plane for ACT tooling. Policy is **code-enforced** in the
harness (not only a prompt suggestion).

## Tiers (`NEO_POLICY_TIER`)

| Value | Tools | Use when |
|-------|-------|----------|
| `report` (0) | **Forced off** | Read-only assessment, token-cheap plans |
| `propose` (1) | Allowed if `NEO_ACT_ALLOW_TOOLS=1` | Draft patches; human applies |
| `apply` (2) | Allowed if tools on | Automated edits within path policy |

Default: **`propose`**.

```bash
export NEO_POLICY_TIER=report
uv run neo start "Assess Makefile targets" -p mock
uv run neo policy
```

## Path gates

| Env | Meaning |
|-----|---------|
| `NEO_PROVIDER_CWD` | Workspace root; paths outside are denied when set |
| `NEO_PATH_ALLOW` | Optional comma-separated globs (relative); if set, must match |
| `NEO_PATH_DENY` | Always denied (defaults include `.env`, PEMs, credentials) |

```bash
export NEO_PROVIDER_CWD=/path/to/repo
export NEO_PATH_ALLOW="src/**,docs/**,tests/**"
export NEO_PATH_DENY=".env,**/*.pem,secrets/**"
uv run neo policy --check-path src/neo_harness/cli.py
uv run neo policy --check-path .env
```

Policy text is injected into PLAN/ACT system prompts via `policy_preamble`.

## CLI

```bash
uv run neo policy
uv run neo policy --check-path ./README.md
```

## Agent packs vs policy

Agent packs shape **how** the model reasons. Policy shapes **what is allowed**.
Keep org-specific allowlists in the **workspace** env / runner, not forked core.
