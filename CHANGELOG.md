# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
