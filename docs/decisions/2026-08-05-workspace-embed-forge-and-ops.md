# Session notes: workspace embed, Forge compose, Neo4j ops

**Date:** 2026-08-05  
**Repo:** neo-harness  
**Status:** Captured for continuity (also mirrored in west_ai_labs / nebulus-forge notes)

## Decisions

1. **Harness ≠ workspace** — neo-harness is a library/CLI; monorepos and apps **consume** it via embed (`init-workspace`, project `.venv-neo`), not a global-only install.
2. **Preferred entrypoint** — workspace `./scripts/neo` loads that repo’s `.env` and sets `NEO_PROVIDER_CWD` to the monorepo root.
3. **`neo init-db` is not a server manager** — connects to already-running Neo4j using `NEO4J_*` env; creates constraints/indexes only. Timeout on 7687 is usually wrong host port; Unauthorized is wrong password.
4. **Lab Bolt remapping** — e.g. Docker `17687->7687` means clients use `bolt://localhost:17687`. Documented in troubleshooting FAQ.
5. **Multiple workspaces on one machine** — per-project venv/env/packs/CWD; shared Neo4j is optional and mixes session history if URI is shared.
6. **Compose with Forge** — `forge new` scaffolds tree; optional post-hook runs `neo init-workspace --pack workspace`. Cross-links: `docs/related-projects.md`.
7. **InfoSec controls (0.2+)** — policy tiers, path gates, audit export, secret redaction.
8. **init-workspace + providers (0.3+)** — thin embed + provider readiness + `NEO_PROVIDER_FALLBACK`.

## Releases / refs

- Public: https://github.com/westailabs/neo-harness  
- Tags discussed this arc: `v0.1.0`, `v0.2.0`, `v0.3.0` (+ later docs on master)

## Operator tips captured in docs

| Topic | Doc |
|-------|-----|
| New workspace walkthrough | [starting-a-workspace.md](../starting-a-workspace.md) |
| init-db / remapped ports FAQ | [troubleshooting.md](../troubleshooting.md) |
| Multi-instance Neo4j | [neo4j.md](../neo4j.md) |
| Forge vs neo | [related-projects.md](../related-projects.md) |

## Next (optional)

- Multi-workspace Neo4j namespacing (feature, not bug)
- Richer `neo doctor` for URI/password probe messaging
