"""GitHub Models LLM client.

All agent inference calls must use the `client` instance configured here so
that the auth + base URL contract is enforced in exactly one place.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Iterable

from openai import OpenAI

def _load_env():
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
            break

_load_env()

log = logging.getLogger("research_assistant.llm")

# Global rotation state
_rotation_index = 0
_rotation_lock = threading.Lock()
_client_cache: dict[str, OpenAI] = {}
_cache_lock = threading.Lock()


def get_groq_keys() -> list[str]:
    keys = []
    # Check GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3, GROQ_API_KEY
    for var_name in ["GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY"]:
        val = os.environ.get(var_name)
        if val and val.strip():
            keys.append(val.strip())
            
    # Check GROQ_API_KEYS (comma separated)
    keys_str = os.environ.get("GROQ_API_KEYS")
    if keys_str:
        for k in keys_str.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in keys:
                keys.append(k_clean)
                
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            deduped.append(k)
    return deduped


def get_client(api_key: str, base_url: str) -> OpenAI:
    with _cache_lock:
        cache_key = f"{base_url}:{api_key}"
        if cache_key not in _client_cache:
            _client_cache[cache_key] = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        return _client_cache[cache_key]


def resolve_model(requested_model: str | None, is_groq: bool) -> str:
    if is_groq:
        groq_default = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        if not requested_model or "gpt-" in requested_model or "openai/" in requested_model:
            return groq_default
        return requested_model
    else:
        return requested_model or os.environ.get("GITHUB_MODEL", "openai/gpt-4.1")


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
    keys = get_groq_keys()
    
    kwargs: dict[str, Any] = {
        "messages": list(messages),
        "temperature": temperature,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    if keys:
        # Rotate Groq keys
        global _rotation_index
        with _rotation_lock:
            start_idx = _rotation_index
            _rotation_index = (_rotation_index + 1) % len(keys)

        last_ex = None
        for attempt in range(len(keys)):
            current_idx = (start_idx + attempt) % len(keys)
            key = keys[current_idx]
            
            # Mask key for logging
            masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "..."
            log.info("Using Groq API Key %d/%d (%s) for attempt %d", current_idx + 1, len(keys), masked_key, attempt + 1)
            
            try:
                # Resolve Groq model
                resolved = resolve_model(model, is_groq=True)
                # Create or reuse client
                groq_client = get_client(key, "https://api.groq.com/openai/v1")
                
                resp = groq_client.chat.completions.create(
                    model=resolved,
                    **kwargs
                )
                return resp.choices[0].message.content or ""
            except Exception as exc:
                last_ex = exc
                log.warning(
                    "Groq call failed with key %d (%s) on attempt %d: %s",
                    current_idx + 1,
                    masked_key,
                    attempt + 1,
                    exc
                )
                continue
                
        raise RuntimeError(f"All Groq API keys failed. Last error: {last_ex}") from last_ex

    else:
        # Fallback to GitHub Models
        if not os.environ.get("GITHUB_TOKEN"):
            raise RuntimeError(
                "Neither GROQ API keys nor GITHUB_TOKEN environment variable is set. "
                "Set GROQ_API_KEY_1/2/3 or GITHUB_TOKEN before running."
            )
            
        resolved = resolve_model(model, is_groq=False)
        github_client = get_client(
            os.environ.get("GITHUB_TOKEN", ""),
            "https://models.github.ai/inference"
        )
        resp = github_client.chat.completions.create(
            model=resolved,
            **kwargs
        )
        return resp.choices[0].message.content or ""


def chat_json(messages: Iterable[dict[str, str]], **kwargs: Any) -> Any:
    """Convenience wrapper that requests JSON and parses the response.

    Falls back to best-effort extraction if the model returns a fenced block.
    """
    kwargs.setdefault("response_format", {"type": "json_object"})
    raw = chat(messages, **kwargs)
    raw = raw.strip()
    if raw.startswith("```"):
        # Strip fenced code blocks if the model decided to wrap them.
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Final defensive parse: find the outermost JSON object/array.
        for opener, closer in (("{", "}"), ("[", "]")):
            start = raw.find(opener)
            end = raw.rfind(closer)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise
