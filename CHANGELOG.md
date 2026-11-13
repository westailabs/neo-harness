# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-11-13

Everything since 0.3.0: the documentation shipped under the docs-only `v0.3.1`
tag, plus the two commits that landed after that tag (smoke-path / agent-pack
discovery, and ignoring `.serena/`).

### Added

- End-to-end [starting-a-workspace](docs/starting-a-workspace.md) guide — embed
  neo-harness in a new or existing git repo, through the first mock job.
- [related-projects.md](docs/related-projects.md) — neo-harness (runtime) vs
  [nebulus-forge](https://github.com/westailabs/nebulus-forge) (scaffold), with
  compose examples (`forge new … --neo auto`).
- Session decision log:
  [2026-08-05-workspace-embed-forge-and-ops.md](docs/decisions/2026-08-05-workspace-embed-forge-and-ops.md).
- Troubleshooting FAQ for `init-db` timeouts when Bolt is remapped (lab hosts
  often publish **17687**, not 7687). `init-db` does not start Neo4j; it only
  uses `NEO4J_URI` from the environment.
- README, docs index, and workspace-embed links to the new guides.

### Fixed

- Clearer error when an agent pack such as `workspace` is not found:
  neo-harness only ships the built-in `sysadmin` pack; project packs require
  `NEO_PROVIDER_CWD` and `./scripts/neo` (a bare `.venv-neo/bin/neo` often loads
  neither `.env` nor CWD).
- `init-workspace` generated env / README snippets document `NEO_AGENT`,
  `NEO_PROVIDER_CWD`, and the `./scripts/neo` entrypoint rule.
- Troubleshooting and workspace docs for the same smoke path.

### Changed

- Ignore `.serena/` (local IDE / agent memory) in `.gitignore`.

## [0.3.1] - 2026-08-05

Documentation-only tag (`20438e8`). This changelog entry was not written at
tag time. The docs below also ship in 0.3.2, which additionally includes two
commits after this tag (`0ea1d42`, `61a6346`).

### Docs

- [starting-a-workspace.md](docs/starting-a-workspace.md)
- [related-projects.md](docs/related-projects.md) (Forge cross-reference)
- FAQ for `init-db` timeout when Bolt is remapped
- Session decision capture for workspace ops and multi-project Neo4j

## [0.3.0] - 2026-08-05

### Added

- **`neo init-workspace`** — thin harness embed (env, jobs, starter pack, scripts/neo)
- **`neo providers`** — readiness probes for mock / grok_build / copilot / xai
- **`NEO_PROVIDER_FALLBACK=mock|none`** — soft mock fallback or fail-closed

### Docs

- [init-workspace.md](docs/init-workspace.md); providers/workspace-embed updates

## [0.2.0] - 2026-08-05

### Added

- **Policy tiers** (`NEO_POLICY_TIER=report|propose|apply`) and path allow/deny gates
- **`neo policy`** CLI — show policy; `--check-path` for gate tests
- **`neo audit`** CLI — export session audit package (JSON/MD) with redaction
- **Secret redaction** on episodic memory, reflections, decisions, and system prompts
- Docs: [threat-model.md](docs/threat-model.md), [policy.md](docs/policy.md), [supply-chain.md](docs/supply-chain.md)
- `scripts/generate-sbom.sh` for environment SBOM export

### Security

- Default path denylist for `.env`, PEMs, credentials
- Report tier forces `NEO_ACT_ALLOW_TOOLS=0`

## [0.1.0] - 2026-08-03

### Added

- Initial alpha: state machine harness, Neo4j typed memory, CLI (`neo`)
- Providers: `mock`, `grok_build`, `copilot`, `xai`
- Budgets, reflection cadence, session start / resume / status / end
