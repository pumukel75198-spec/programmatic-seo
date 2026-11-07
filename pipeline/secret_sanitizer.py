"""Deterministic secret sanitizer for generated content.

GitHub Push Protection blocks a push when generated mock data or code contains
a string that matches a known credential format. The LLM frequently invents
realistic-looking mock identifiers (for example a Twilio Account SID that
consists of the prefix AC followed by 32 hexadecimal characters), which is
harmless in a blueprint but aborts the unattended deploy.

This module replaces every known credential pattern with a clearly fake
placeholder. In generated Python code, quoted literals are replaced with
``os.environ.get(...)`` lookups, so the shipped client remains runnable with
real credentials supplied by the buyer.
"""

from __future__ import annotations

import re
from typing import Any

# Twilio Account SID – the exact pattern GitHub Push Protection flags.
_TWILIO_ACCOUNT = re.compile(r"\bAC[0-9a-fA-F]{32}\b")
# Other Twilio resource SIDs (conversation, call, message, phone, API key, ...).
_TWILIO_RESOURCE = re.compile(
    r"\b(?:CH|CA|SM|PN|SK|MG|MM|US|UU|VA|ZS)[0-9a-fA-F]{32}\b"
)

_SLACK_TOKEN = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")
_OPENAI_KEY = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
_AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GOOGLE_KEY = re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")
_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")
_STRIPE_KEY = re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
_SLACK_WEBHOOK = re.compile(
    r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+"
)

_QUOTED = r"""([\"']){pattern}\1"""


def sanitize_text(text: str, *, code: bool = False) -> str:
    """Replace credential-shaped substrings in one string."""
    if not isinstance(text, str) or not text:
        return text

    value = text

    if code:
        # Turn quoted mock credentials into real environment lookups. This keeps
        # the generated snippet executable and removes the scanner pattern.
        value = re.sub(
            _QUOTED.format(pattern=r"AC[0-9a-fA-F]{32}"),
            'os.environ.get("TWILIO_ACCOUNT_SID", "")',
            value,
        )
        value = re.sub(
            _QUOTED.format(
                pattern=r"(?:CH|CA|SM|PN|SK|MG|MM|US|UU|VA|ZS)[0-9a-fA-F]{32}"
            ),
            'os.environ.get("TWILIO_RESOURCE_SID", "")',
            value,
        )
        value = re.sub(
            _QUOTED.format(pattern=r"xox[baprs]-[A-Za-z0-9-]{10,}"),
            'os.environ.get("SLACK_BOT_TOKEN", "")',
            value,
        )
        value = re.sub(
            _QUOTED.format(pattern=r"sk-[A-Za-z0-9]{20,}"),
            'os.environ.get("API_KEY", "")',
            value,
        )
        value = re.sub(
            _QUOTED.format(pattern=r"AKIA[0-9A-Z]{16}"),
            'os.environ.get("AWS_ACCESS_KEY_ID", "")',
            value,
        )
        value = re.sub(
            _QUOTED.format(pattern=r"AIza[0-9A-Za-z_-]{30,}"),
            'os.environ.get("GOOGLE_API_KEY", "")',
            value,
        )
        value = re.sub(
            _QUOTED.format(pattern=r"gh[pousr]_[A-Za-z0-9]{20,}"),
            'os.environ.get("GITHUB_TOKEN", "")',
            value,
        )

    # Any remaining occurrence (mock data, descriptions, URLs, unquoted code)
    # becomes an unmistakably fake placeholder.
    value = _PRIVATE_KEY.sub("MOCK_PRIVATE_KEY_REMOVED", value)
    value = _SLACK_WEBHOOK.sub(
        "https://hooks.slack.com/services/MOCK/MOCK/MOCK", value
    )
    value = _TWILIO_ACCOUNT.sub("MOCK_TWILIO_ACCOUNT_SID", value)
    value = _TWILIO_RESOURCE.sub("MOCK_TWILIO_RESOURCE_SID", value)
    value = _SLACK_TOKEN.sub("MOCK_SLACK_TOKEN", value)
    value = _OPENAI_KEY.sub("MOCK_API_KEY", value)
    value = _AWS_KEY.sub("MOCK_AWS_ACCESS_KEY", value)
    value = _GOOGLE_KEY.sub("MOCK_GOOGLE_API_KEY", value)
    value = _GITHUB_TOKEN.sub("MOCK_GITHUB_TOKEN", value)
    value = _STRIPE_KEY.sub("MOCK_STRIPE_KEY", value)
    return value


def sanitize_value(value: Any, *, code: bool = False) -> Any:
    """Recursively sanitize strings in dicts/lists/scalars."""
    if isinstance(value, str):
        return sanitize_text(value, code=code)
    if isinstance(value, list):
        return [sanitize_value(item, code=code) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item, code=code) for item in value)
    if isinstance(value, dict):
        return {
            key: sanitize_value(item, code=code) for key, item in value.items()
        }
    return value


def sanitize_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a workflow record, treating code snippets as code."""
    details = workflow.get("details") or {}
    for step in details.get("steps") or []:
        if not isinstance(step, dict):
            continue
        code = step.get("code_snippet")
        if isinstance(code, str):
            step["code_snippet"] = sanitize_text(code, code=True)
        if "mock_response" in step:
            step["mock_response"] = sanitize_value(step["mock_response"])
    return sanitize_value(workflow)


def sanitize_records(records: Any) -> Any:
    """Sanitize a whole JSON dataset (apis/alternatives/workflows)."""
    return sanitize_value(records)


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    # Build the samples at runtime so the source file itself does not contain
    # a literal credential-shaped string (GitHub scans source files too).
    twilio_sid = "AC" + ("0" * 32)
    slack_token = "xoxb-" + ("0" * 24)
    openai_key = "sk-" + ("a" * 32)
    slack_webhook = "https://hooks.slack.com/services/" + "X" * 8
    samples = [
        '{"account_sid": "' + twilio_sid + '"}',
        "token = '" + slack_token + "'",
        "key = '" + openai_key + "'",
        slack_webhook,
    ]
    for sample in samples:
        print(sanitize_text(sample, code=True))