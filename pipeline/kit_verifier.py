"""Hard content verification for generated Implementation Kits.

The sandbox already executes the shipped code. This module additionally proves
that every required file exists and contains the contractually promised
content (dry-run mode, request helper, auth/error tests, env example, PDF
markers, mock data, schema, HTTP requests, AI prompt and README).

A kit that fails any assertion is never uploaded to R2 and never persisted.
"""

from __future__ import annotations

import ast
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from . import config as cfg

_ENV_RE = re.compile(
    r"os\.(?:environ\.get|getenv)\(\s*['\"]([A-Z0-9_]+)['\"]"
)
_ENV_INDEX_RE = re.compile(r"os\.environ\[\s*['\"]([A-Z0-9_]+)['\"]\s*\]")
_PAGE_RE = re.compile(rb"/Type\s*/Page\b")


def _read_zip(kit_path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(kit_path, "r") as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }


def _text(files: dict[str, bytes], name: str) -> str:
    return files.get(name, b"").decode("utf-8", "replace")


def _pdf_errors(data: bytes, label: str, markers: tuple[bytes, ...] = ()) -> list[str]:
    errors: list[str] = []
    if not data.startswith(b"%PDF"):
        errors.append(f"{label}: invalid PDF header")
        return errors
    pages = len(_PAGE_RE.findall(data))
    if pages < 2:
        errors.append(f"{label}: only {pages} page(s), expected >= 2")
    if len(data) < 8000:
        errors.append(f"{label}: suspiciously small ({len(data)} bytes)")
    for marker in markers:
        if marker not in data:
            errors.append(f"{label}: missing marker {marker!r}")
    return errors


def _stdlib_import_errors(
    source: str, label: str, allowed_local: set[str] | None = None
) -> list[str]:
    allowed_local = allowed_local or set()
    errors: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [f"{label}: SyntaxError: {error.msg}"]
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for imported in names:
            top = imported.split(".")[0]
            if top in cfg.FORBIDDEN_IMPORTS:
                errors.append(f"{label}: forbidden import '{imported}'")
            elif top not in cfg.STDLIB_MODULES and top not in allowed_local:
                errors.append(f"{label}: non-stdlib import '{imported}'")
    return errors


def verify_api_kit(kit_path: Path, api: dict[str, Any]) -> list[str]:
    """Return a list of content errors for one API kit (empty = perfect)."""
    errors: list[str] = []
    if not kit_path.exists():
        return [f"API kit missing: {kit_path}"]
    try:
        files = _read_zip(kit_path)
    except Exception as error:  # noqa: BLE001
        return [f"API kit unreadable: {type(error).__name__}: {error}"]

    for required in cfg.API_KIT_FILES:
        if required not in files:
            errors.append(f"API kit missing required file '{required}'")

    client = _text(files, "api_client.py")
    test = _text(files, "test_mock.py")
    env_example = _text(files, ".env.example")
    requests_http = _text(files, "requests.http")
    ai_prompt = _text(files, "AI_INTEGRATION_PROMPT.md")
    readme = _text(files, "README.md")

    if "def request_json(" not in client:
        errors.append("api_client.py: missing top-level request_json(...)")
    if "--dry-run" not in client:
        errors.append("api_client.py: missing --dry-run mode")
    if "os.environ" not in client:
        errors.append("api_client.py: configuration must use os.environ")
    errors.extend(_stdlib_import_errors(client, "api_client.py"))

    if "unittest" not in test:
        errors.append("test_mock.py: missing unittest")
    if "mock.patch" not in test:
        errors.append("test_mock.py: missing mock.patch")
    if "Authorization" not in test:
        errors.append("test_mock.py: does not assert the Authorization header")
    if "HTTPError" not in test:
        errors.append("test_mock.py: does not test HTTPError handling")
    errors.extend(
        _stdlib_import_errors(test, "test_mock.py", allowed_local={"api_client"})
    )

    env_names = set(_ENV_RE.findall(client)) | set(_ENV_INDEX_RE.findall(client))
    for name in sorted(env_names):
        if name not in env_example:
            errors.append(f".env.example: missing variable {name}")

    if len(requests_http.strip()) < 20 or "http" not in requests_http.lower():
        errors.append("requests.http: missing real HTTP requests")
    if len(ai_prompt.strip()) < 40:
        errors.append("AI_INTEGRATION_PROMPT.md: too short")
    if len(readme.strip()) < 40:
        errors.append("README.md: too short")

    errors.extend(
        _pdf_errors(
            files.get("api-cheatsheet.pdf", b""),
            "api-cheatsheet.pdf",
            (
                b"Premium Kit",
                b"Created & Verified on",
                b"Verification & Link Validity Notice",
            ),
        )
    )
    return errors


def verify_workflow_kit(
    kit_path: Path, workflow: dict[str, Any]
) -> list[str]:
    """Return a list of content errors for one workflow kit (empty = perfect)."""
    errors: list[str] = []
    if not kit_path.exists():
        return [f"Workflow kit missing: {kit_path}"]
    try:
        files = _read_zip(kit_path)
    except Exception as error:  # noqa: BLE001
        return [f"Workflow kit unreadable: {type(error).__name__}: {error}"]

    for required in cfg.WORKFLOW_KIT_FILES:
        if required not in files:
            errors.append(f"Workflow kit missing required file '{required}'")

    script = _text(files, "workflow.py")
    mock_data = _text(files, "mock_data.json")
    schema = _text(files, "schema.sql")
    requests_http = _text(files, "requests.http")
    ai_prompt = _text(files, "AI_IMPLEMENTATION_PROMPT.md")
    readme = _text(files, "README.md")

    if "--dry-run" not in script:
        errors.append("workflow.py: missing --dry-run mode")
    if "def run_workflow(" not in script:
        errors.append("workflow.py: missing run_workflow()")
    if "mock.patch" not in script:
        errors.append("workflow.py: missing mock.patch for the dry-run")
    errors.extend(_stdlib_import_errors(script, "workflow.py"))

    try:
        parsed = json.loads(mock_data)
        if not parsed:
            errors.append("mock_data.json: empty JSON payload")
    except json.JSONDecodeError as error:
        errors.append(f"mock_data.json: invalid JSON: {error}")

    if len(schema.strip()) < 20:
        errors.append("schema.sql: too short")
    if len(requests_http.strip()) < 20 or "http" not in requests_http.lower():
        errors.append("requests.http: missing real HTTP requests")
    if len(ai_prompt.strip()) < 40:
        errors.append("AI_IMPLEMENTATION_PROMPT.md: too short")
    if len(readme.strip()) < 40:
        errors.append("README.md: too short")

    errors.extend(_pdf_errors(files.get("blueprint.pdf", b""), "blueprint.pdf"))
    return errors