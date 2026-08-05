# Public release checklist

Use before flipping the GitHub repository from **private → public**.

## Must complete

- [x] Root `LICENSE` (MIT)
- [x] `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- [x] CI: `.github/workflows/ci.yml` (pytest + ruff)
- [x] Scrub personal hostnames / user ids from tracked docs and packs
- [x] Session notes removed from default docs tree (or marked internal-only)
- [x] Stranger-friendly README + quickstart (Docker Neo4j)
- [ ] Final `git grep` audit on `develop` (secrets, absolute home paths)
- [ ] `origin/develop` pushed and green CI on GitHub
- [ ] Repo description + topics set on GitHub
- [ ] Confirm no private submodules or LFS secrets
- [ ] Tag `v0.1.0` (or next) after public-ready merge
- [ ] Flip visibility → Public (org owner)

## Optional (soon after flip)

- [ ] Publish to PyPI / TestPyPI (`neo-harness`)
- [ ] GitHub Discussions or issue templates
- [ ] Example consumer repo (minimal IaC workspace)

## Pre-push audit

See [security-and-publishing.md](./security-and-publishing.md).
