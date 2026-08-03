# Providers

Providers implement `ReasoningProvider` and only serve **plan / act / reflect**.
They do not own outer control flow.

Factory:

```python
from neo_harness.providers import get_provider
p = get_provider("mock")          # mock | grok_build | copilot | xai
```

CLI:

```bash
uv run neo start "…" --provider grok_build
# or NEO_PROVIDER=copilot in .env
```

On hard failure, real providers **fall back to mock** so the loop can continue
(logged as warnings).

## Comparison

| Name | Backend | Structured output | Tools on ACT | Offline |
|------|---------|-------------------|--------------|---------|
| `mock` | In-process | Fixed 3-step plan | Simulated | Yes |
| `grok_build` | `grok` CLI | `--json-schema` → `structuredOutput` | Optional | Needs auth + binary |
| `copilot` | `copilot` CLI | Instruct JSON + parse | Optional | Needs auth + binary |
| `xai` | HTTP `chat/completions` | Instruct JSON + parse | No tools | Needs `XAI_API_KEY` |

## mock

- Deterministic plan (3 steps), successful acts, reflection heuristics.
- Use for: unit tests, CI, structural demos, Neo4j wiring checks.
- No network.

## grok_build

Invokes Grok Build headless single-turn mode:

```text
grok -p <prompt>
     --json-schema <schema>
     --system-prompt-override <system>
     --always-approve
     --max-turns <n>
     [--disallowed-tools …]
     [--model …]
```

Response envelope includes `structuredOutput` when a schema is provided
(see `providers/json_util.py` → `from_grok_headless`).

| Env | Role |
|-----|------|
| `GROK_BUILD_CMD` | Binary / command (default `grok`) |
| `GROK_MODEL` / `NEO_GROK_MODEL` | Optional model id |
| `NEO_GROK_TIMEOUT` | Seconds (default 180) |
| `NEO_GROK_ACT_TURNS` | Max turns for ACT when tools allowed |
| `NEO_ACT_ALLOW_TOOLS` | `1`/`0` — tools during ACT only |
| `NEO_PROVIDER_CWD` | Working directory for the CLI |

PLAN and REFLECT strip heavy tools via `--disallowed-tools`.

**Prerequisite:** `grok` on PATH, logged in (`grok login` if needed).

## copilot

Invokes GitHub Copilot CLI non-interactively:

```text
copilot -C <cwd> -p <prompt>
        --allow-all-tools
        --no-ask-user
        -s / --silent
        --effort <level>
        [--model …]
        [--excluded-tools …]   # reasoning states
```

No native JSON Schema flag — prompt includes schema; stdout parsed as JSON.

| Env | Role |
|-----|------|
| `COPILOT_CMD` | Binary (default `copilot`) |
| `COPILOT_MODEL` / `NEO_COPILOT_MODEL` | Optional model |
| `COPILOT_EFFORT` / `NEO_COPILOT_EFFORT` | default `low` |
| `NEO_COPILOT_TIMEOUT` | Seconds (default 300) |
| `NEO_ACT_ALLOW_TOOLS` | Tools during ACT |
| `NEO_PROVIDER_CWD` | Working directory |

**Prerequisite:** `copilot` on PATH, authenticated for non-interactive use.

## xai

HTTP client to xAI chat completions (`XAI_API_KEY`, optional `XAI_BASE_URL`, `XAI_MODEL`).
JSON instructed in the prompt; no tool loop. Falls back to mock without a key or on HTTP errors.

## ACT and tools

| `NEO_ACT_ALLOW_TOOLS` | Behavior |
|----------------------|----------|
| `0` / `false` | Pure reasoning; good for design notes and demos |
| `1` / `true` (default in code if unset) | Provider may use shell/file tools during ACT |

Project `.env` often sets `NEO_ACT_ALLOW_TOOLS=0` for safer first runs.

**With tools off**, the agent still produces high-quality episode summaries and
reflections, but may not write files to disk. **With tools on**, ACT can edit the repo
under `NEO_PROVIDER_CWD` — use a disposable branch or worktree for demos.

## Latency expectations

Each real plan/act/reflect call is often **20–90+ seconds**. A full session
(plan + several acts + reflections) can take **several minutes**. The CLI currently
prints the full history when the loop returns — use `neo status` to watch live Neo4j state.

## Adding a provider

1. Subclass `ReasoningProvider` in `providers/`.
2. Map results into `Plan` / act dict / `Reflection`.
3. Register aliases in `get_provider()`.
4. Document env vars here and in [configuration.md](./configuration.md).
5. Prefer mock fallback for resilience.
