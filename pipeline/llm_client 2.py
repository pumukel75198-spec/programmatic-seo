"""Minimal OpenRouter client built on the Python standard library.

Only this module talks to the LLM. It handles retries, exponential backoff,
JSON extraction and the self-healing feedback loop is driven by run_batch.py.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from . import config


class LLMError(RuntimeError):
    """Raised when the LLM cannot be reached or returns unusable content."""


def _extract_json(text: str) -> dict[str, Any] | None:
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines.pop()
        cleaned = "\n".join(lines)
    return cleaned


def _post(payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{config.OPENROUTER_URL}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {config.get_api_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://flowmatrix.dev",
            "X-Title": "FlowMatrix Unified Pipeline",
        },
    )
    with urllib.request.urlopen(request, timeout=config.LLM_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _chat(messages: list[dict[str, str]], json_mode: bool = True) -> str:
    payload: dict[str, Any] = {
        "model": config.LLM_MODEL,
        "temperature": 0.25,
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_error: Exception | None = None
    for attempt in range(1, config.LLM_MAX_ATTEMPTS + 1):
        try:
            data = _post(payload)
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise LLMError("Leere LLM-Antwort.")
            return content
        except urllib.error.HTTPError as error:
            last_error = error
            body = error.read().decode("utf-8", "replace")  # type: ignore[union-attr]
            # Some models reject response_format; retry once without it.
            if error.code == 400 and json_mode:
                json_mode = False
                payload.pop("response_format", None)
                continue
            if error.code == 429 or error.code >= 500:
                time.sleep(2 ** (attempt - 1))
                continue
            raise LLMError(f"OpenRouter HTTP {error.code}: {body[:300]}") from error
        except (
            urllib.error.URLError,
            TimeoutError,
            KeyError,
            ConnectionResetError,
            OSError,
        ) as error:
            last_error = error
            if attempt < config.LLM_MAX_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))
                continue
            raise LLMError(f"OpenRouter nicht erreichbar: {error}") from error

    raise LLMError(f"LLM fehlgeschlagen nach {config.LLM_MAX_ATTEMPTS} Versuchen: {last_error}")


def chat_json(system: str, user: str) -> dict[str, Any]:
    content = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_mode=True,
    )
    parsed = _extract_json(content)
    if parsed is None:
        raise LLMError("LLM lieferte kein gültiges JSON.")
    return parsed


def chat_code(system: str, user: str) -> str:
    content = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_mode=False,
    )
    return _strip_code_fences(content)
