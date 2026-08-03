"""Shared JSON extraction helpers for CLI providers."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object from model/CLI text."""
    if not text:
        return None
    text = text.strip()

    # Prefer whole-document parse.
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Fenced code block
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            data = json.loads(fence.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # First balanced-ish object slice
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None
    return None


def from_grok_headless(raw: str) -> dict[str, Any] | None:
    """
    Parse Grok Build headless JSON envelope.

    With --json-schema, payload includes structuredOutput.
    Without schema, prefer the text field.
    """
    data = extract_json_object(raw)
    if not data:
        return None
    if isinstance(data.get("structuredOutput"), dict):
        return data["structuredOutput"]
    text = data.get("text")
    if isinstance(text, str):
        inner = extract_json_object(text)
        if inner:
            return inner
        # plain text answer wrapped in envelope
        return {"summary": text, "success": True, "raw_text": text}
    # Already the structured payload (no envelope)
    if "goal" in data or "summary" in data or "what_happened" in data or "next_action" in data:
        return data
    return data


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "description": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["index", "description"],
            },
        },
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["goal", "steps"],
}

ACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "success": {"type": "boolean"},
        "output": {"type": "object"},
    },
    "required": ["summary", "success"],
}

REFLECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "what_happened": {"type": "string"},
        "what_worked": {"type": "array", "items": {"type": "string"}},
        "what_failed": {"type": "array", "items": {"type": "string"}},
        "lessons": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "next_action": {
            "type": "string",
            "enum": ["continue", "replan", "done", "fail", "block"],
        },
        "confidence": {"type": "number"},
    },
    "required": ["what_happened", "next_action"],
}
