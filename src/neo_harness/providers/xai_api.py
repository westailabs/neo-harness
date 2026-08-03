"""Direct xAI API provider (skeleton — real HTTP wiring optional for v0.1)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from neo_harness.providers.base import ReasoningProvider
from neo_harness.providers.mock import MockProvider
from neo_harness.schemas.plan import Plan, PlanStep
from neo_harness.schemas.reflection import NextAction, Reflection, ReflectionTrigger

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-2-latest"


class XAIAPIProvider(ReasoningProvider):
    """
    Calls the xAI chat completions API when XAI_API_KEY is set.

    Without a key, delegates to MockProvider so offline demos still work.
    """

    name = "xai_api"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 60.0,
        fallback: ReasoningProvider | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        self.base_url = (base_url or os.environ.get("XAI_BASE_URL") or DEFAULT_BASE_URL).rstrip(
            "/"
        )
        self.model = model or os.environ.get("XAI_MODEL") or DEFAULT_MODEL
        self.timeout_s = timeout_s
        self._fallback = fallback or MockProvider()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def _chat(self, system: str, prompt: str) -> str | None:
        if not self.api_key:
            return None
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("xAI API call failed: %s", exc)
            return None

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | None:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # drop fence
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    return None
        return None

    async def plan(self, *, system: str, prompt: str, session_id: str) -> Plan:
        schema_hint = (
            "\nRespond ONLY with JSON matching: "
            '{"goal": str, "steps": [{"index": int, "description": str}], '
            '"assumptions": [str], "risks": [str]}'
        )
        raw = await self._chat(system, prompt + schema_hint)
        if raw:
            data = self._extract_json(raw)
            if data:
                steps = [
                    PlanStep(index=s.get("index", i), description=s["description"])
                    for i, s in enumerate(data.get("steps") or [])
                ]
                return Plan(
                    session_id=session_id,
                    goal=data.get("goal") or "Untitled goal",
                    steps=steps,
                    assumptions=list(data.get("assumptions") or []),
                    risks=list(data.get("risks") or []),
                )
        return await self._fallback.plan(system=system, prompt=prompt, session_id=session_id)

    async def act(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
        step: PlanStep,
    ) -> dict[str, Any]:
        schema_hint = (
            '\nRespond ONLY with JSON: {"summary": str, "success": bool, "output": object}'
        )
        raw = await self._chat(system, prompt + schema_hint)
        if raw:
            data = self._extract_json(raw)
            if data:
                return {
                    "summary": data.get("summary") or raw[:500],
                    "success": bool(data.get("success", True)),
                    "output": data.get("output") or {},
                }
            return {"summary": raw[:1000], "success": True}
        return await self._fallback.act(
            system=system, prompt=prompt, session_id=session_id, step=step
        )

    async def reflect(
        self,
        *,
        system: str,
        prompt: str,
        session_id: str,
    ) -> Reflection:
        schema_hint = (
            "\nRespond ONLY with JSON: "
            '{"what_happened": str, "what_worked": [str], "what_failed": [str], '
            '"lessons": [str], "decisions": [str], "open_questions": [str], '
            '"next_action": "continue|replan|done|fail|block", "confidence": float}'
        )
        raw = await self._chat(system, prompt + schema_hint)
        if raw:
            data = self._extract_json(raw)
            if data:
                try:
                    next_action = NextAction(data.get("next_action", "continue"))
                except ValueError:
                    next_action = NextAction.CONTINUE
                return Reflection(
                    session_id=session_id,
                    trigger=ReflectionTrigger.INTERVAL,
                    what_happened=data.get("what_happened") or raw[:500],
                    what_worked=list(data.get("what_worked") or []),
                    what_failed=list(data.get("what_failed") or []),
                    lessons=list(data.get("lessons") or []),
                    decisions=list(data.get("decisions") or []),
                    open_questions=list(data.get("open_questions") or []),
                    next_action=next_action,
                    confidence=float(data.get("confidence", 0.5)),
                )
        return await self._fallback.reflect(
            system=system, prompt=prompt, session_id=session_id
        )
