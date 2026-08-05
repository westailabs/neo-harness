# Threat model — neo-harness

**Status:** Alpha control document (InfoSec-oriented)  
**Audience:** Security reviewers, platform engineers, operators  
**Scope:** The neo-harness package, CLI, providers, and Neo4j session memory

## 1. System summary

neo-harness is a **local/operator-controlled** agent harness. A human starts a
session; a replaceable model reasons inside **PLAN / ACT / REFLECT**; the harness
owns transitions, budgets, and typed memory in Neo4j.

```text
Operator ──CLI──► HarnessLoop ──► Provider (mock | grok | copilot | xai)
                      │
                      ├── Policy tier + path gates
                      ├── Secret redaction
                      └── Neo4j (session / episode / reflection)
                                ▲
Workspace (NEO_PROVIDER_CWD) ───┘  (files tools may touch when allowed)
```

## 2. Assets

| Asset | Sensitivity |
|-------|-------------|
| Workspace source code / IaC | High (may include internal IP) |
| Neo4j harness memory (episodes, plans) | Medium–High (task content, paths) |
| API keys / DB passwords in env | Critical |
| Operator machine credentials | Critical |
| Audit export files | Medium–High |

## 3. Trust boundaries

| Boundary | Inside | Outside |
|----------|--------|---------|
| **Harness process** | State machine, redaction, policy | Model provider process/CLI |
| **Workspace root** | Paths under `NEO_PROVIDER_CWD` | Rest of filesystem |
| **Operator** | Review, apply, push, secrets | Untrusted model output |
| **Shared graphs** | Optional separate AI Heirloom | Must not be harness memory without design |

**Rule:** The model is **untrusted**. The harness and operator are **trusted control planes**.

## 4. Actors

| Actor | Intent | Capabilities |
|-------|--------|--------------|
| Operator | Legitimate engineering | Starts sessions, reviews diffs, holds secrets |
| Model / provider CLI | Helpful but non-deterministic | Suggests and (if tools on) may edit within policy |
| Malicious task brief | Abuse tools | Injected via task file / env |
| Compromised Neo4j | Read/alter memory | Network access to Bolt |
| Supply-chain attacker | Malicious dependency | PyPI/git compromise |

## 5. Threats & mitigations

| ID | Threat | Mitigation (current / planned) |
|----|--------|--------------------------------|
| T1 | Model edits secrets (`.env`, keys) | Default **path deny** for `.env`, keys, PEMs; redaction on persist |
| T2 | Model escapes workspace | `path_allowed` requires path under `NEO_PROVIDER_CWD` when set |
| T3 | Over-privileged ACT | **Policy tiers**: report / propose / apply; report forces tools off |
| T4 | Secrets in Neo4j episodes | `redact_secrets` on episode/reflection/decision write |
| T5 | Secrets in prompts | Policy preamble + redaction of system text; never put `.env` in tasks |
| T6 | Unreviewed push | Operator owns git; docs forbid push of session branches without approval |
| T7 | Confused deputy (wrong CWD) | Explicit `NEO_PROVIDER_CWD`; `neo policy` shows root |
| T8 | Audit failure | `neo audit <session_id>` export JSON/MD for review |
| T9 | Dependency compromise | `uv.lock` pinned; supply-chain doc + SBOM script |
| T10 | Shared graph pollution | Separate harness Neo4j from org knowledge graph by default |

## 6. Policy tiers (control objective)

| Tier | Tools | Intent |
|------|-------|--------|
| **report** | Forced off | Observe / describe only |
| **propose** | Optional | Draft changes; prefer human apply |
| **apply** | Optional | Write within path policy |

Set via `NEO_POLICY_TIER`. See [policy.md](./policy.md).

## 7. Residual risks (alpha)

- Provider CLIs may have their own tool implementations; harness path checks are
  **defense in depth**, not a full OS sandbox.
- Redaction is pattern-based (false negatives possible).
- No multi-tenant isolation; one operator machine / lab DB assumed.
- No formal third-party pen-test yet.

## 8. Operator checklist (InfoSec-friendly run)

1. Use a **dedicated** Neo4j for harness memory (not production customer DBs).  
2. Set `NEO_PROVIDER_CWD` to the smallest repo that needs changes.  
3. Start with `NEO_POLICY_TIER=report` or `propose` + `NEO_ACT_ALLOW_TOOLS=0`.  
4. Enable tools only with `apply` + reviewed allow/deny.  
5. `neo audit <id> -o review.json` before merging high-risk changes.  
6. Never commit `.env`; rotate if leaked into chat history.

## 9. Related docs

- [policy.md](./policy.md)  
- [security-and-publishing.md](./security-and-publishing.md)  
- [supply-chain.md](./supply-chain.md)  
- [SECURITY.md](../SECURITY.md)  
