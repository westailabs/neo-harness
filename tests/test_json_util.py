"""JSON extraction helpers for CLI providers."""

from neo_harness.providers.json_util import extract_json_object, from_grok_headless


def test_extract_plain() -> None:
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_extract_fenced() -> None:
    text = 'Here:\n```json\n{"goal": "x", "steps": []}\n```\n'
    assert extract_json_object(text) == {"goal": "x", "steps": []}


def test_from_grok_structured_output() -> None:
    raw = """
    {
      "text": "{\\"ping\\":\\"pong\\"}",
      "stopReason": "end_turn",
      "structuredOutput": {"ping": "pong"},
      "usage": {"total_tokens": 10}
    }
    """
    assert from_grok_headless(raw) == {"ping": "pong"}


def test_from_grok_text_json() -> None:
    raw = '{"text": "{\\"summary\\": \\"ok\\", \\"success\\": true}", "stopReason": "end_turn"}'
    assert from_grok_headless(raw) == {"summary": "ok", "success": True}
