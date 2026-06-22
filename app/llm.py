from __future__ import annotations

import json
import os
from typing import Any, Iterable

from openai import OpenAI

ENDPOINT = "https://models.github.ai/inference"
DEFAULT_MODEL = os.environ.get("GITHUB_MODEL", "openai/gpt-4.1")

_token = os.environ.get("GITHUB_TOKEN")
if not _token:
    _token = ""

client = OpenAI(
    base_url=ENDPOINT,
    api_key=_token or "missing-token",
)


def chat(
    messages: Iterable[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    response_format: dict[str, Any] | None = None,
    max_tokens: int | None = None,
) -> str:
    """Single-turn chat helper. Returns the raw assistant content string.

    Centralising this here keeps every agent's call shape identical and makes
    retries / logging / cost tracking trivial to bolt on later.
    """
    if not os.environ.get("GITHUB_TOKEN"):
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is not set. "
            "Export a GitHub Models access token before starting the backend."
        )

    kwargs: dict[str, Any] = {
        "model": model or DEFAULT_MODEL,
        "messages": list(messages),
        "temperature": temperature,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_json(messages: Iterable[dict[str, str]], **kwargs: Any) -> Any:
    """Convenience wrapper that requests JSON and parses the response.

    Falls back to best-effort extraction if the model returns a fenced block.
    """
    kwargs.setdefault("response_format", {"type": "json_object"})
    raw = chat(messages, **kwargs)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for opener, closer in (("{", "}"), ("[", "]")):
            start = raw.find(opener)
            end = raw.rfind(closer)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise
