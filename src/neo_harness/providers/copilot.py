"""GitHub Copilot CLI provider — non-interactive `copilot -p`."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Any

from neo_harness.providers.base import ReasoningProvider
from neo_harness.providers.json_util import (
    ACT_SCHEMA,
    PLAN_SCHEMA,
    REFLECT_SCHEMA,
    extract_json_object,
)
from neo_harness.providers.mock import MockProvider
from neo_harness.schemas.plan import Plan, PlanStep
from neo_harness.schemas.reflection import NextAction, Reflection, ReflectionTrigger

logger = logging.getLogger(__name__)


class CopilotProvider(ReasoningProvider):
    """
    Use GitHub Copilot CLI as the reasoning engine.

    Contract (copilot ≥ 1.0):
      copilot -p PROMPT
          --allow-all-tools   # required for non-interactive
          --no-ask-user
          -s / --silent       # response only on stdout
          [--model …]
          [--effort …]
          [-C cwd]

    Copilot does not take a JSON Schema flag; we instruct JSON-only and parse.
    Falls back to MockProvider on missing binary or parse failure.
    """

    name = "copilot"

    def __init__(
        self,
        *,
        command: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        timeout_s: float | None = None,
        allow_tools_on_act: bool | None = None,
        cwd: str | None = None,
        fallback: ReasoningProvider | None = None,
    ) -> None:
        self.command = command or os.environ.get("COPILOT_CMD") or "copilot"
        self.model = model or os.environ.get("COPILOT_MODEL") or os.environ.get("NEO_COPILOT_MODEL")
        self.effort = (
            effort
            or os.environ.get("COPILOT_EFFORT")
            or os.environ.get("NEO_COPILOT_EFFORT")
            or "low"
        )
        self.timeout_s = float(
            timeout_s
            if timeout_s is not None
            else os.environ.get("NEO_COPILOT_TIMEOUT", "300")
        )
        if allow_tools_on_act is None:
            allow_tools_on_act = os.environ.get("NEO_ACT_ALLOW_TOOLS", "1") not in (
                "0",
                "false",
                "False",
            )
        self.allow_tools_on_act = allow_tools_on_act
        self.cwd = cwd or os.environ.get("NEO_PROVIDER_CWD") or os.getcwd()
        self._fallback = fallback or MockProvider()
        self._binary = self.command.split()[0]
        self._available = shutil.which(self._binary) is not None

    @property
    def available(self) -> bool:
        return self._available

    def _schema_hint(self, schema: dict[str, Any]) -> str:
        return (
            "\n\nRespond with ONLY a single JSON object matching this schema "
            f"(no markdown fences, no prose):\n{schema}"
        )

    def _invoke(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        allow_tools: bool,
    ) -> dict[str, Any] | None:
        if not self._available:
            logger.warning("Copilot CLI not found on PATH: %s", self._binary)
            return None

        full_prompt = f"{system}\n\n---\n\n{prompt}{self._schema_hint(schema)}"
        cmd = [
            *self.command.split(),
            "-C",
            self.cwd,
            "-p",
            full_prompt,
            "--allow-all-tools",  # required for non-interactive
            "--no-ask-user",
            "-s",
            "--effort",
            self.effort,
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        # When tools should be denied for pure reasoning, exclude shell/edit tools.
        if not allow_tools:
            cmd.extend(
                [
                    "--excluded-tools",
                    "shell,bash,edit,write,read,grep,glob,view,create",
                ]
            )

        logger.info("copilot invoke: tools=%s effort=%s cwd=%s", allow_tools, self.effort, self.cwd)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                cwd=self.cwd,
                check=False,
                env={**os.environ, "NO_COLOR": "1", "COPILOT_ALLOW_ALL": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Copilot invoke failed: %s", exc)
            return None

        raw = (proc.stdout or "").strip()
        if proc.returncode != 0 and not raw:
            logger.warning(
                "Copilot exit %s: %s", proc.returncode, (proc.stderr or "")[:800]
            )
            return None
        if not raw:
            logger.warning("Copilot empty stdout: %s", (proc.stderr or "")[:400])
            return None

        data = extract_json_object(raw)
        if not data:
            # Accept free text as act summary
            logger.warning("Copilot non-JSON response (using as text): %s", raw[:200])
            return {"summary": raw[:2000], "success": True, "raw_text": raw}
        return data

    async def plan(self, *, system: str, prompt: str, session_id: str) -> Plan:
        full_system = (
            system
            + "\nYou are inside neo-harness PLAN state. "
            "Prefer 2–6 concrete ordered steps. Do not edit files."
        )
        data = self._invoke(
            system=full_system,
            prompt=prompt,
            schema=PLAN_SCHEMA,
            allow_tools=False,
        )
        if not data or not data.get("steps"):
            return await self._fallback.plan(system=system, prompt=prompt, session_id=session_id)

        steps = [
            PlanStep(
                index=int(s.get("index", i)),
                description=str(s.get("description") or f"Step {i}"),
                rationale=str(s.get("rationale") or ""),
            )
            for i, s in enumerate(data.get("steps") or [])
            if isinstance(s, dict)
        ]
        if not steps:
            return await self._fallback.plan(system=system, prompt=prompt, session_id=session_id)

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
            "Execute the current step. Return summary and success as JSON."
        )
        data = self._invoke(
            system=full_system,
            prompt=prompt,
            schema=ACT_SCHEMA,
            allow_tools=self.allow_tools_on_act,
        )
        if not data:
            return await self._fallback.act(
                system=system, prompt=prompt, session_id=session_id, step=step
            )
        return {
            "summary": str(data.get("summary") or data.get("raw_text") or step.description),
            "success": bool(data.get("success", True)),
            "output": data.get("output") if isinstance(data.get("output"), dict) else {},
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
            "next_action ∈ continue|replan|done|fail|block. Do not edit files."
        )
        data = self._invoke(
            system=full_system,
            prompt=prompt,
            schema=REFLECT_SCHEMA,
            allow_tools=False,
        )
        if not data or "what_happened" not in data:
            return await self._fallback.reflect(
                system=system, prompt=prompt, session_id=session_id
            )
        try:
            next_action = NextAction(str(data.get("next_action", "continue")))
        except ValueError:
            next_action = NextAction.CONTINUE
        try:
            confidence = float(data.get("confidence", 0.5))
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
