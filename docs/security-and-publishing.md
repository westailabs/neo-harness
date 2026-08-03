# Security and publishing

Rules for keeping **secrets** and **bloat** out of the published tree
(`origin` on GitHub: keep this checklist before every push).

## Current audit (maintainer checklist)

Run from repo root:

```bash
# 1. What will be in the next commit?
git status
git diff --stat

# 2. No env files or venvs staged
git status --porcelain | rg -i '\.env$|\.venv|credentials|secrets' || true

# 3. No high-risk patterns in tracked / staged content
git grep -nI -E 'WestAILabs[0-9]+|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]+|xai-[A-Za-z0-9]{20,}|NEO4J_PASSWORD=[^p<\n][^<\n]+' \
  $(git ls-files) || echo "OK: no high-risk patterns in tracked files"

# 4. Confirm .env is ignored and untracked
git check-ignore -v .env
test ! -f .env || git status --porcelain .env | rg . && echo "FAIL: .env tracked" || echo "OK: .env not tracked"

# 5. Preview publish set
git archive HEAD | tar -t | head -80
```

### Snapshot (as of docs authoring)

| Item | Status |
|------|--------|
| `.env` (real lab password) | **Gitignored**, never in `HEAD` |
| `.venv/` | Gitignored |
| `.pytest_cache/` | Gitignored |
| High-risk secrets in tracked files | **None found** |
| Absolute `/home/…` paths in tracked files | **None found** |
| `uv.lock` | Tracked on purpose (~50KB, reproducible installs) |
| Remote | Clean initial tree; re-audit after local changes |

## Never commit

- `.env`, `.env.local`, `.env.production`, etc. (only **`.env.example`** with placeholders)
- API keys: `XAI_API_KEY`, GitHub tokens, Grok session tokens
- Real database passwords (lab Neo4j password lives only in local `.env` / compose outside this repo)
- Private keys (`*.pem`, `id_rsa*`, …)
- Virtualenvs (`.venv/`, `venv/`)
- Local session pointer `~/.neo-harness/` or in-repo copies
- Large binary dumps, DB exports, log directories

## Safe to commit

- Source under `src/`, tests, `docs/`, `README.md`, `pyproject.toml`
- `.env.example` with **placeholder** values only (`password`, empty keys)
- `uv.lock` for reproducible installs
- Default code fallbacks like Neo4j password `"password"` (local Docker example only — not a lab secret)

## Docs hygiene

- Prefer “set `NEO4J_PASSWORD` to match your instance” over embedding real passwords.
- Lab paths like `~/neo4j/docker-compose.yml` are operational hints, not secrets — still avoid pasting the actual `NEO4J_AUTH` value into markdown.
- Demo session UUIDs are fine; do not paste episode content that includes proprietary customer data.

## Bloat policy

| Keep out | Why |
|----------|-----|
| `.venv` | Tens of MB; rebuild with `uv sync` |
| `__pycache__`, `.pytest_cache`, coverage HTML | Regenerable |
| `dist/`, `build/`, `*.egg-info` | Build artifacts |
| Scratch clones, screenshots, downloads | Use `~/scratch` outside the repo |
| Vendor copies of other monorepos | Link, don’t subtree |

If something large must be shared, use a release asset or external store — not git history.

## If a secret is committed by mistake

1. **Rotate** the credential immediately (Neo4j password, API key, token).  
2. Remove from the tree and tighten `.gitignore`.  
3. If already pushed: treat history as compromised; rewrite only with team agreement (`git filter-repo` / BFG), force-push policy, and re-rotate.  
4. Prefer rotation over “we deleted the commit” alone — clones may retain the blob.

## Pre-push habit

```bash
uv run pytest -q
git status   # clean, no .env
# optional: run the audit block at the top of this file
git push     # only develop (or release tags), per lab git policy
```

Feature branches are local-only in the West AI Labs workflow; merge to `develop` before push.
