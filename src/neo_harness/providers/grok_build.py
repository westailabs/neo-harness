"""Grok Build provider — headless single-turn CLI via `grok -p`."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Any

from neo_harness.providers.base import ReasoningProvider
from neo_harness.providers.fallback import raise_or_fallback, resolve_fallback
from neo_harness.providers.json_util import (
    ACT_SCHEMA,
    PLAN_SCHEMA,
    REFLECT_SCHEMA,
    from_grok_headless,
)
from neo_harness.schemas.plan import Plan, PlanStep
from neo_harness.schemas.reflection import NextAction, Reflection, ReflectionTrigger

logger = logging.getLogger(__name__)

# Tools that cause long agent loops; strip for pure reasoning states.
DEFAULT_REASONING_DENY = (
    "run_terminal_command,web_search,open_page,open_page_with_find,"
    "image_gen,image_edit,image_to_video,reference_to_video,"
    "spawn_subagent,workflow,monitor"
)


class GrokBuildProvider(ReasoningProvider):
    """
    Use the Grok Build CLI as the reasoning engine.

    Contract (grok ≥ 0.2):
      grok -p PROMPT
          --json-schema SCHEMA
          --system-prompt-override SYSTEM
          --always-approve
          --max-turns N
          [--disallowed-tools …]
          [--model …]

    Response is a JSON envelope; structured fields live under ``structuredOutput``.
    Falls back per NEO_PROVIDER_FALLBACK (mock default, or none = fail-closed).
    """

    name = "grok_build"

    def __init__(
        self,
        *,
        command: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
        max_turns_reason: int = 1,
        max_turns_act: int = 8,
        allow_tools_on_act: bool | None = None,
        cwd: str | None = None,
        fallback: ReasoningProvider | None | object = ...,  # noqa: B008
    ) -> None:
        self.command = command or os.environ.get("GROK_BUILD_CMD") or "grok"
        self.model = model or os.environ.get("GROK_MODEL") or os.environ.get("NEO_GROK_MODEL")
        self.timeout_s = float(
            timeout_s
            if timeout_s is not None
            else os.environ.get("NEO_GROK_TIMEOUT", "180")
        )
        self.max_turns_reason = max_turns_reason
        self.max_turns_act = int(os.environ.get("NEO_GROK_ACT_TURNS", str(max_turns_act)))
        if allow_tools_on_act is None:
            allow_tools_on_act = os.environ.get("NEO_ACT_ALLOW_TOOLS", "1") not in (
                "0",
                "false",
                "False",
            )
        self.allow_tools_on_act = allow_tools_on_act
        self.cwd = cwd or os.environ.get("NEO_PROVIDER_CWD") or os.getcwd()
        self._fallback = resolve_fallback(fallback)
        self._binary = self.command.split()[0]
        self._available = shutil.which(self._binary) is not None

    @property
    def available(self) -> bool:
        return self._available

    def _base_cmd(self) -> list[str]:
        return list(self.command.split())

    def _invoke(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_turns: int,
        allow_tools: bool,
    ) -> dict[str, Any] | None:
        if not self._available:
            logger.warning("Grok Build not found on PATH: %s", self._binary)
            return None

        cmd = [
            *self._base_cmd(),
            "-p",
            prompt,
            "--json-schema",
            json.dumps(schema),
            "--system-prompt-override",
            system,
            "--always-approve",
            "--max-turns",
            str(max_turns),
            "--verbatim",
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if not allow_tools:
            cmd.extend(["--disallowed-tools", DEFAULT_REASONING_DENY])

        logger.info("grok invoke: turns=%s tools=%s cwd=%s", max_turns, allow_tools, self.cwd)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                cwd=self.cwd,
                check=False,
                env={**os.environ, "NO_COLOR": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Grok Build invoke failed: %s", exc)
            return None

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[:800]
            logger.warning("Grok Build exit %s: %s", proc.returncode, err)
            # Still try to parse stdout — some failures still emit partial JSON.
        raw = (proc.stdout or "").strip()
        if not raw:
            logger.warning("Grok Build empty stdout: %s", (proc.stderr or "")[:400])
            return None

        parsed = from_grok_headless(raw)
        if not parsed:
            logger.warning("Grok Build could not parse response: %s", raw[:400])
            return None
        # Attach usage if present in envelope
        envelope = None
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            pass
        if isinstance(envelope, dict) and "usage" in envelope:
            parsed["_usage"] = envelope["usage"]
        return parsed

    async def plan(self, *, system: str, prompt: str, session_id: str) -> Plan:
        full_system = (
            system
            + "\nYou are inside neo-harness PLAN state. "
            "Return only fields matching the schema. Prefer 2–6 concrete steps."
        )
        data = self._invoke(
            system=full_system,
            prompt=prompt,
            schema=PLAN_SCHEMA,
            max_turns=self.max_turns_reason,
            allow_tools=False,
        )
        if not data:
            fb = raise_or_fallback(
                self._fallback, provider_name=self.name, reason="invoke/binary failed"
            )
            return await fb.plan(system=system, prompt=prompt, session_id=session_id)

        steps_raw = data.get("steps") or []
        steps = [
            PlanStep(
                index=int(s.get("index", i)),
                description=str(s.get("description") or f"Step {i}"),
                rationale=str(s.get("rationale") or ""),
            )
            for i, s in enumerate(steps_raw)
            if isinstance(s, dict)
        ]
        if not steps:
            fb = raise_or_fallback(
                self._fallback, provider_name=self.name, reason="empty plan steps"
            )
            return await fb.plan(system=system, prompt=prompt, session_id=session_id)

        return Plan(
            session_id=session_id,
            goal=str(data.get("goal") or "Untitled goal"),
            steps=steps,
            assumptions=[str(a) for a in (data.get("assumptions") or [])],
            risks=[str(r) for r in (data.get("risks") or [])],
        )

    async def act(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
        step: PlanStep,
    ) -> dict[str, Any]:
        full_system = (
            system
            + "\nYou are inside neo-harness ACT state. "
            "Execute or simulate the current step, then return summary+success. "
            "If tools are available, use them only as needed for this step."
        )
        data = self._invoke(
            system=full_system,
            prompt=prompt,
            schema=ACT_SCHEMA,
            max_turns=self.max_turns_act if self.allow_tools_on_act else self.max_turns_reason,
            allow_tools=self.allow_tools_on_act,
        )
        if not data:
            fb = raise_or_fallback(
                self._fallback, provider_name=self.name, reason="act invoke failed"
            )
            return await fb.act(
                system=system, prompt=prompt, session_id=session_id, step=step
            )
        return {
            "summary": str(data.get("summary") or f"Acted on: {step.description}"),
            "success": bool(data.get("success", True)),
            "output": data.get("output") if isinstance(data.get("output"), dict) else {},
            "tokens_used": (data.get("_usage") or {}).get("total_tokens"),
            "provider": self.name,
        }

    async def reflect(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
    ) -> Reflection:
        full_system = (
            system
            + "\nYou are inside neo-harness REFLECT state. "
            "next_action must be one of: continue, replan, done, fail, block."
        )
        data = self._invoke(
            system=full_system,
            prompt=prompt,
            schema=REFLECT_SCHEMA,
            max_turns=self.max_turns_reason,
            allow_tools=False,
        )
        if not data:
            fb = raise_or_fallback(
                self._fallback, provider_name=self.name, reason="reflect invoke failed"
            )
            return await fb.reflect(system=system, prompt=prompt, session_id=session_id)
        try:
            next_action = NextAction(str(data.get("next_action", "continue")))
        except ValueError:
            next_action = NextAction.CONTINUE
        conf = data.get("confidence", 0.5)
        try:
            confidence = float(conf)
        except (TypeError, ValueError):
            confidence = 0.5
        return Reflection(
            session_id=session_id,
            trigger=ReflectionTrigger.INTERVAL,
            what_happened=str(data.get("what_happened") or "Reflection complete"),
            what_worked=[str(x) for x in (data.get("what_worked") or [])],
            what_failed=[str(x) for x in (data.get("what_failed") or [])],
            lessons=[str(x) for x in (data.get("lessons") or [])],
            decisions=[str(x) for x in (data.get("decisions") or [])],
            open_questions=[str(x) for x in (data.get("open_questions") or [])],
            next_action=next_action,
            confidence=max(0.0, min(1.0, confidence)),
            metadata={"provider": self.name},
        )
