#!/usr/bin/env bash
# Generate a basic SBOM for the neo-harness environment.
# Prefer cyclonedx-bom when installed; otherwise list packages as JSON.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p dist
OUT="${1:-dist/sbom.json}"

if command -v uv >/dev/null 2>&1; then
  PY=(uv run python)
elif [[ -x .venv/bin/python ]]; then
  PY=(.venv/bin/python)
else
  PY=(python3)
fi

if "${PY[@]}" -c "import cyclonedx" 2>/dev/null; then
  echo "==> cyclonedx available — generating CycloneDX JSON"
  "${PY[@]}" -m cyclonedx_py environment -o "$OUT" 2>/dev/null \
    || "${PY[@]}" -c "print('cyclonedx CLI missing; falling back')" 
fi

if [[ ! -f "$OUT" ]] || [[ ! -s "$OUT" ]]; then
  echo "==> Writing simple package SBOM to $OUT"
  "${PY[@]}" - <<'PY' "$OUT"
import json, sys
from datetime import datetime, timezone
from importlib import metadata

out = sys.argv[1]
pkgs = []
for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
    name = dist.metadata["Name"]
    version = dist.version
    pkgs.append({"name": name, "version": version, "type": "pypi"})
doc = {
    "bomFormat": "neo-harness-simple-sbom",
    "specVersion": "0.1",
    "generated": datetime.now(timezone.utc).isoformat(),
    "components": pkgs,
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
print(f"Wrote {out} ({len(pkgs)} components)")
PY
fi

echo "SBOM: $OUT"
