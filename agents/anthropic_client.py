"""Thin wrapper around the Anthropic Messages API for JSON-structured agent
output. Every CaseLens agent is a Claude Sonnet call through this module."""

import json
import re
from typing import Any

import anthropic

from shared.config import settings

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _extract_json(text: str) -> Any:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    return json.loads(text)


async def complete_json(*, system: str, user: str, max_tokens: int = 4000) -> Any:
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not configured. Set it in the environment to run "
            "agents against the live Claude API, or omit it to use the offline "
            "heuristic fallback (see agents/heuristics.py)."
        )
    client = _get_client()
    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json(text)
