# Supply chain

How neo-harness manages dependencies and release integrity (alpha).

## Pinned dependencies

| Artifact | Role |
|----------|------|
| `uv.lock` | Locked transitive graph for reproducible `uv sync` |
| `pyproject.toml` | Direct dependency lower bounds |
| GitHub Actions CI | pytest + ruff on every push/PR to `develop`/`master` |

```bash
uv sync --all-extras
uv run pytest -q
```

## SBOM (software bill of materials)

Generate a CycloneDX-style JSON list of installed packages from the project env:

```bash
./scripts/generate-sbom.sh
# → dist/sbom.json
```

Requires a synced `.venv` or `uv run`. For richer SBOMs, optionally install
`cyclonedx-bom` in the environment; the script falls back to a simple package
list if it is not present.

## Releases

| Step | Practice |
|------|----------|
| Tag | Annotated `vX.Y.Z` on the release commit |
| GitHub Release | Notes + source archive from tag |
| PyPI | **Not published yet** — install from git/source |
| Signing | Prefer GitHub artifact attestations when publishing binaries/wheels |

## Operator advice

- Prefer `uv sync` over unpinned `pip install neo-harness` from unknown forks.
- Review `uv.lock` diffs on upgrades.
- Do not vendor secrets into the package tree (see security-and-publishing).

## Related

- [threat-model.md](./threat-model.md)  
- [security-and-publishing.md](./security-and-publishing.md)  
