# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Public-release hygiene: `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, CI workflow
- Workspace agent pack discovery requires `manifest.yml` or phase prompts (skips free-form `AGENT.md`-only profiles)
- Token diet defaults, `--task-file`, run profiles (`cheap` / `deep`)
- Built-in `sysadmin` agent pack and workspace-embed documentation

### Changed

- Docs and examples use generic host IaC paths (no personal machine names)

## [0.1.0] - 2026-08-03

### Added

- Initial alpha: state machine harness, Neo4j typed memory, CLI (`neo`)
- Providers: `mock`, `grok_build`, `copilot`, `xai`
- Budgets, reflection cadence, session start / resume / status / end
