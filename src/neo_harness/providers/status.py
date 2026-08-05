"""Provider readiness probes for ``neo providers``."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderStatus:
    name: str
    available: bool
    detail: str
    binary: str | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "detail": self.detail,
            "binary": self.binary,
            "notes": self.notes,
        }


def probe_mock() -> ProviderStatus:
    return ProviderStatus(
        name="mock",
        available=True,
        detail="in-process (always available)",
        notes="Deterministic; use for CI and structure tests",
    )


def probe_grok_build() -> ProviderStatus:
    cmd = os.environ.get("GROK_BUILD_CMD") or "grok"
    binary = cmd.split()[0]
    path = shutil.which(binary)
    if not path:
        return ProviderStatus(
            name="grok_build",
            available=False,
            detail=f"binary not found: {binary}",
            binary=binary,
            notes="Install Grok Build CLI and ensure it is on PATH",
        )
    return ProviderStatus(
        name="grok_build",
        available=True,
        detail=f"found: {path}",
        binary=binary,
        notes="Auth via `grok login` if required",
    )


def probe_copilot() -> ProviderStatus:
    cmd = os.environ.get("COPILOT_CMD") or "copilot"
    binary = cmd.split()[0]
    path = shutil.which(binary)
    if not path:
        return ProviderStatus(
            name="copilot",
            available=False,
            detail=f"binary not found: {binary}",
            binary=binary,
            notes="Install GitHub Copilot CLI",
        )
    return ProviderStatus(
        name="copilot",
        available=True,
        detail=f"found: {path}",
        binary=binary,
        notes="Must be authenticated for live runs",
    )


def probe_xai() -> ProviderStatus:
    key = os.environ.get("XAI_API_KEY") or ""
    if not key.strip():
        return ProviderStatus(
            name="xai",
            available=False,
            detail="XAI_API_KEY unset",
            notes="Set XAI_API_KEY for direct API provider",
        )
    return ProviderStatus(
        name="xai",
        available=True,
        detail="XAI_API_KEY set",
        notes="HTTP chat/completions; no tool loop",
    )


def probe_all() -> list[ProviderStatus]:
    return [probe_mock(), probe_grok_build(), probe_copilot(), probe_xai()]
