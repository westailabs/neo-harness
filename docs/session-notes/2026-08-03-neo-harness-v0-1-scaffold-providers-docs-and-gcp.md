# Session Notes: neo-harness v0.1 scaffold providers docs and GCP patterns

**Date:** 2026-08-03  
**Branch:** develop | **Commit:** d2bfeeb

## Decisions Made
- Harness owns control flow; providers only plan/act/reflect
- Prefer uv run over foreign venv; .env for Neo4j secrets never committed
- Default ACT tools off for design demos; tools on only with allowlisted scripts for ops

## Key Nuances & Gotchas
- uv warns when VIRTUAL_ENV is .python3_venv but uses project .venv — safe to ignore with uv run
- Lab Neo4j password is NEO4J_AUTH in ~/neo4j/docker-compose.yml, not the package default password
- Real provider runs look hung on running loop; watch neo status -s or Neo4j
- ACT cannot transition to PLAN; replan only via REFLECT

## Work Completed
- Scaffolded neo-harness: state machine memory Neo4j CLI mock loop
- Wired grok_build and copilot providers with JSON schemas and mock fallback
- Docs suite including demo GCP Terraform DBA security-and-publishing
- Pushed develop and master with publish hygiene; later docs commits to develop only

## State at End of Session
- Branch `develop` @ `d2bfeeb`
- Notes written via west-ai-session-save

## Next Steps
- [ ] Optional: live progress output during long provider calls
- [ ] Optional: nightly mock smoke + queue worker automation
- [ ] Optional: merge develop to master for later docs commits if desired
