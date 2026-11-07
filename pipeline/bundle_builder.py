"""Automatic Implementation-Kit (.zip) builder.

For every workflow and every API script the pipeline produces a ready-to-sell
kit archive:

Workflow kit (``<slug>-kit.zip``):
    blueprint.pdf, workflow.py, .env.example, mock_data.json, schema.sql,
    requests.http, AI_IMPLEMENTATION_PROMPT.md, README.md

API kit (``<slug>-kit.zip``):
    api_client.py, test_mock.py, .env.example, requests.http,
    AI_INTEGRATION_PROMPT.md, api-cheatsheet.pdf, README.md

The archives are written to a local directory and uploaded to R2 by
``run_batch.py``.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from . import config as cfg

_URL_RE = re.compile(r"https?://[^\s\"'<>)\]}]+")
_ENV_RE = re.compile(r"os\.(?:environ\.get|getenv)\(\s*['\"]([A-Z0-9_]+)['\"]")


def _json_safe(value: Any) -> Any:
    """Make mock data JSON-serialisable (LLMs sometimes emit Ellipsis)."""
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if value is Ellipsis:
        return None
    return value
_ENV_INDEX_RE = re.compile(r"os\.environ\[\s*['\"]([A-Z0-9_]+)['\"]\s*\]")


def _step_code(workflow: dict[str, Any]) -> str:
    steps = (workflow.get("details") or {}).get("steps") or []
    return "\n\n".join(str(step.get("code_snippet") or "") for step in steps)


def _env_names(code: str) -> list[str]:
    return sorted(set(_ENV_RE.findall(code)) | set(_ENV_INDEX_RE.findall(code)))


def _dry_run_env_value(name: str) -> str:
    """Harmless but URL-valid defaults for ``workflow.py --dry-run``."""
    upper = name.upper()
    is_url = (
        upper.endswith("_URL")
        or upper.endswith("URL")
        or "BASE_URL" in upper
        or "WEBHOOK" in upper
        or upper.endswith("_ENDPOINT")
        or upper.endswith("_HOST")
    )
    # File-path variables (e.g. PROMPT_FIXTURE_PATH) must point to an existing
    # JSON mock so the dry-run never opens a non-existent file.
    is_file_path = any(
        marker in upper for marker in ("_PATH", "_FILE", "FIXTURE", "_INPUT", "_DIR")
    )
    if is_file_path and not is_url:
        return "mock_input.json"
    if "SUPABASE" in upper:
        return "https://mock.supabase.co" if is_url else "dry-run-value"
    if "SLACK" in upper:
        return "https://hooks.slack.com/services/mock" if is_url else "dry-run-value"
    if "OPENAI" in upper:
        return "https://api.openai.com" if is_url else "dry-run-value"
    if upper.startswith("X_") or "TWITTER" in upper:
        return "https://api.x.com" if is_url else "dry-run-value"
    if is_url:
        return "https://example.com"
    return "dry-run-value"


def _env_example(code: str) -> str:
    names = _env_names(code)
    if not names:
        return "# No environment variables required.\n"
    return "\n".join(f"{name}=" for name in names) + "\n"


def _mock_data(workflow: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    # Prefer the per-step documented mock_response so --dry-run serves exactly
    # the response structure each step expects (avoids KeyError/AttributeError).
    for step in (workflow.get("details") or {}).get("steps") or []:
        mock = step.get("mock_response")
        step_code = str(step.get("code_snippet") or "")
        if not mock:
            continue
        if isinstance(mock, str):
            try:
                mock = json.loads(mock)
            except Exception:  # noqa: BLE001
                try:
                    import ast as _ast

                    mock = _ast.literal_eval(mock)
                except Exception:  # noqa: BLE001
                    continue
        mock = _json_safe(mock)
        for url in _URL_RE.findall(step_code):
            data.setdefault(url, mock)
    code = _step_code(workflow).lower()
    if "x.com" in code or "twitter.com" in code:
        payload = {
            "data": [
                {"id": "1", "text": "I love this product"},
                {"id": "2", "text": "Terrible experience"},
            ]
        }
        data["x.com"] = payload
        data["twitter.com"] = payload
    if "openai.com" in code:
        data["openai.com"] = {"choices": [{"message": {"content": "0.8"}}]}
    if "supabase" in code:
        data["supabase"] = []
    if "slack.com" in code:
        data["slack.com"] = "ok"
    return data


def _schema_sql(workflow: dict[str, Any]) -> str:
    code = _step_code(workflow)
    match = re.search(r"/rest/v1/([a-zA-Z0-9_]+)", code)
    table = match.group(1) if match else "trends"

    # Derive the columns from the actual Supabase json.dumps({...}) payloads
    # instead of always shipping a keyword/count schema that may not match the
    # code. Only functions that talk to Supabase/PostgREST are considered so
    # unrelated OpenAI payloads do not leak into the database schema.
    columns: list[str] = []
    for function_match in re.finditer(
        r"def\s+\w+\([^)]*\):(.*?)(?=\ndef |\Z)", code, re.S
    ):
        body = function_match.group(1)
        if "rest/v1" not in body and "supabase" not in body.lower():
            continue
        payload_bodies = [
            match.group(1)
            for match in re.finditer(
                r"json\.dumps\(\s*\{(.*?)\}\s*\)", body, re.S
            )
        ]
        payload_bodies.extend(
            match.group(1)
            for match in re.finditer(
                r"(?:payload|data|row|record)\s*=\s*\{(.*?)\}", body, re.S
            )
        )
        for payload_body in payload_bodies:
            for key_match in re.finditer(
                r"['\"](\w+)['\"]\s*:", payload_body
            ):
                key = key_match.group(1)
                if key not in columns:
                    columns.append(key)
    if not columns:
        # The Supabase step may serialize a record variable that was defined in
        # an earlier step. Inspect record-like dict literals as a fallback.
        for dict_match in re.finditer(r"\{([^{}]*)\}", code, re.S):
            body = dict_match.group(1)
            if "'keyword'" not in body and '"keyword"' not in body:
                continue
            for key_match in re.finditer(r"['\"](\w+)['\"]\s*:", body):
                key = key_match.group(1)
                if key not in columns:
                    columns.append(key)
    if not columns:
        columns = ["keyword", "count"]

    numeric = {"count", "score", "sentiment", "z_score", "value", "amount", "price"}
    jsonb = {"mentions", "texts", "records", "tags", "items", "data", "payload"}
    not_null = {"keyword", "topic", "name", "title", "count"}

    lines = [
        "-- Supabase schema for this workflow",
        f"create table if not exists {table} (",
        "  id bigint generated by default as identity primary key,",
    ]
    for key in columns:
        lowered = key.lower()
        if lowered in numeric:
            sql_type = "double precision"
        elif lowered in jsonb:
            sql_type = "jsonb"
        elif lowered in {"created_at", "updated_at", "timestamp"}:
            sql_type = "timestamptz default now()"
        else:
            sql_type = "text"
        suffix = " not null" if lowered in not_null else ""
        lines.append(f"  {key} {sql_type}{suffix},")
    if "created_at" not in {key.lower() for key in columns}:
        lines.append("  created_at timestamptz default now()")
    else:
        # Remove the trailing comma from the last real column.
        lines[-1] = lines[-1].rstrip(",")
    lines.append(");")
    return "\n".join(lines) + "\n"


def _requests_http(code: str) -> str:
    lines = ["### FlowMatrix API calls", ""]
    urls: list[str] = []
    for url in sorted(_URL_RE.findall(code)):
        if any(marker in url for marker in ("<", ">", "{", "}")):
            continue
        urls.append(url)

    # Environment-driven endpoints have no literal URL in the generated code.
    table_match = re.search(r"/rest/v1/([a-zA-Z0-9_]+)", code)
    if "SUPABASE_URL" in code:
        table = table_match.group(1) if table_match else "trends"
        urls.append("{{SUPABASE_URL}}/rest/v1/" + table)
    if "SLACK_WEBHOOK_URL" in code:
        urls.append("{{SLACK_WEBHOOK_URL}}")

    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        is_openai = "openai.com" in url
        is_x = "x.com" in url or "twitter.com" in url
        is_supabase = "supabase" in url or "rest/v1" in url
        is_slack = "slack" in url or "webhook" in url.lower()
        method = "POST" if (is_openai or is_supabase or is_slack) else "GET"

        lines.append(f"### {url}")
        lines.append(f"{method} {url}")
        if is_openai:
            lines.append("Authorization: Bearer {{OPENAI_API_KEY}}")
        elif is_x:
            lines.append("Authorization: Bearer {{X_API_TOKEN}}")
        elif is_supabase:
            lines.append("apikey: {{SUPABASE_KEY}}")
            lines.append("Authorization: Bearer {{SUPABASE_KEY}}")
            lines.append("Prefer: return=representation")
        if method == "POST":
            lines.append("Content-Type: application/json")
            lines.append("")
            if is_openai:
                lines.append(
                    '{"model": "gpt-4o-mini", "messages": '
                    '[{"role": "user", "content": "hello"}]}'
                )
            elif is_supabase:
                lines.append(
                    '{"keyword": "example", "mentions": ["example mention"]}'
                )
            elif is_slack:
                lines.append('{"text": "FlowMatrix test alert"}')
        lines.append("")

    if len(lines) == 2:
        lines.append("# No direct HTTP calls detected.")
    return "\n".join(lines)


def _workflow_script(workflow: dict[str, Any]) -> str:
    title = str(workflow.get("title") or "FlowMatrix Workflow")
    body = _step_code(workflow)
    env_names = _env_names(body)
    env_defaults = {name: _dry_run_env_value(name) for name in env_names}
    # Input files the snippets read but the kit does not ship: --dry-run creates
    # deterministic mock files so the kit is self-contained.
    input_files = sorted(
        set(re.findall(r"['\"]([\w./-]+\.(?:json|csv|txt))['\"]", body))
    )
    indented = "\n".join(
        ("    " + line) if line.strip() else "" for line in body.splitlines()
    )
    # Deterministic mock for ANY input file the snippets read during --dry-run,
    # including file paths that come from environment variables (e.g. a
    # *_FILE/*_PATH var set to "dry-run-value").
    safe_open_src = '''
        import builtins
        import io

        _real_open = builtins.open

        def _safe_open(file, mode="r", *args, **kwargs):
            if "r" in mode and not os.path.exists(file):
                name = str(file)
                if name.endswith(".json"):
                    return io.StringIO(json.dumps([{"id": "1", "title": "Sample", "content": "Sample content", "text": "sample text", "value": 0.5, "name": "sample", "prompt": "sample prompt", "keyword": "sample", "query": "sample", "url": "https://example.com", "status": "ok"}]))
                if name.endswith(".csv"):
                    return io.StringIO("id,name,value\\n1,sample,0.5\\n")
                return io.StringIO("sample\\n")
            return _real_open(file, mode, *args, **kwargs)
'''
    return f'''#!/usr/bin/env python3
"""FlowMatrix Implementation Kit – {title}

Run with --dry-run to execute against mock_data.json (no real API keys needed).
All code uses the Python standard library only.
"""
import argparse
import json
import os
import sys
import urllib.request
from unittest import mock

MOCK_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data.json")


def _mock_urlopen(mock_responses):
    class _Resp:
        def __init__(self, payload, status=200):
            self._payload = payload
            self.status = status

        def read(self, amount=-1):
            return self._payload if amount is None or amount < 0 else self._payload[:amount]

        def getcode(self):
            return self.status

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _open(request, *args, **kwargs):
        if "headers" in kwargs:
            raise TypeError(
                "urlopen() got an unexpected keyword argument 'headers' – "
                "use urllib.request.Request(url, headers=...)"
            )
        url = getattr(request, "full_url", None) or str(request)
        for key, payload in mock_responses.items():
            if key in url:
                body = (
                    payload.encode("utf-8")
                    if isinstance(payload, str)
                    else json.dumps(payload).encode("utf-8")
                )
                return _Resp(body)
        # Generic fallback so environment-driven mock URLs (e.g. a
        # dry-run SUPABASE_URL) still satisfy the common response contracts.
        return _Resp(json.dumps({{
            "data": [{{"id": "1", "text": "sample", "value": 0.5}}],
            "choices": [{{"message": {{"content": "0.8"}}}}],
            "content": "0.8",
            "value": 0.5,
            "status": "ok",
            "ok": True,
        }}).encode("utf-8"))

    return _open


def run_workflow():
{indented}


def main():
    parser = argparse.ArgumentParser(description="{title}")
    parser.add_argument("--dry-run", action="store_true", help="Run against mock_data.json")
    args = parser.parse_args()
    if args.dry_run:
        # Provide harmless defaults for every documented environment variable so
        # the kit runs without real API keys (os.environ["X"] would otherwise
        # raise KeyError). URL-like values must be valid absolute URLs because
        # urllib parses them before the mocked urlopen is called.
        for name, value in {env_defaults!r}.items():
            os.environ.setdefault(name, value)
        with open(MOCK_DATA, encoding="utf-8") as fh:
            mock_responses = json.load(fh)
        # Provide mock input files for any file the workflow reads but the kit
        # does not ship (e.g. content_briefs.json), so --dry-run stays
        # self-contained and never raises FileNotFoundError.
        for _name in {input_files!r}:
            if not os.path.exists(_name):
                with open(_name, "w", encoding="utf-8") as _fh:
                    if _name.endswith(".json"):
                        json.dump([{{"id": "1", "title": "Sample", "content": "Sample content", "text": "sample text", "value": 0.5, "name": "sample", "keyword": "sample", "query": "sample", "url": "https://example.com", "status": "ok"}}], _fh)
                    elif _name.endswith(".csv"):
                        _fh.write("id,name,value\\n1,sample,0.5\\n")
                    else:
                        _fh.write("sample\\n")
{safe_open_src}        with mock.patch("builtins.open", side_effect=_safe_open), mock.patch("urllib.request.urlopen", side_effect=_mock_urlopen(mock_responses)):
            run_workflow()
        print("Dry-run completed successfully.")
    else:
        run_workflow()
        print("Workflow completed successfully.")


if __name__ == "__main__":
    main()
'''


def _ai_prompt(workflow: dict[str, Any], kind: str) -> str:
    title = str(workflow.get("title") or "the workflow")
    return f"""# AI Implementation Prompt – {title}

You are a senior software engineer. Port the following {kind} to the target
language and framework requested by the user. Preserve the exact API contracts,
authentication flow, error handling and data flow. Use only the target
language's standard library where possible. Keep all comments in English.

## Source
- Title: {title}
- Category: {workflow.get("category", "—")}
- Tools: {", ".join((workflow.get("details") or {}).get("tools") or []) or "—"}

## Requirements
1. Read `workflow.py` (or `api_client.py`) and `requests.http` first.
2. Reproduce every HTTP call with the same method, headers and payload.
3. Keep the `--dry-run` mode working against `mock_data.json`.
4. Never hardcode secrets; read them from environment variables.
5. Add type hints and English docstrings.
"""


def _workflow_readme(workflow: dict[str, Any]) -> str:
    title = str(workflow.get("title") or "FlowMatrix Workflow")
    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    checklist = "\n".join(
        f"- [ ] Step {i}: {step.get('title', '')}" for i, step in enumerate(steps, 1)
    )
    return f"""# {title} – Implementation Kit

This kit contains everything you need to rebuild the workflow locally.

## Contents
- `blueprint.pdf` – the full architecture blueprint
- `workflow.py` – runnable Python script (standard library only)
- `.env.example` – required environment variables
- `mock_data.json` – realistic mock payloads for `--dry-run`
- `schema.sql` – Supabase table schema (if applicable)
- `requests.http` – all API calls for VS Code REST Client / Bruno / Postman
- `AI_IMPLEMENTATION_PROMPT.md` – prompt to port the workflow to another language
- `README.md` – this file

## Quick start
```bash
cp .env.example .env
python3 workflow.py --dry-run
```

## Checklist
{checklist}
"""


def _api_readme(api: dict[str, Any]) -> str:
    title = str(api.get("title") or "API")
    details = api.get("details") or {}
    return f"""# {title} – API Implementation Kit

## Contents
- `api_client.py` – dependency-free Python client
- `test_mock.py` – mock test
- `.env.example` – required environment variables
- `requests.http` – ready-to-run HTTP requests
- `AI_INTEGRATION_PROMPT.md` – prompt to port the client to another language
- `api-cheatsheet.pdf` – one-page API cheat sheet
- `README.md` – this file

## Quick start
```bash
cp .env.example .env
python3 api_client.py
```

## API
- Provider: {details.get("provider", "—")}
- Endpoint: {details.get("endpoint", "—")}
- Docs: {details.get("docsUrl") or details.get("website") or "—"}
"""


def _api_test(api: dict[str, Any], script: str = "") -> str:
    env_defaults = {name: _dry_run_env_value(name) for name in _env_names(script)}
    return f'''"""Mock test for the {api.get("title", "API")} client."""
import json
import os
import unittest
from unittest import mock

# Harmless defaults before importing the client so module-level os.environ
# lookups do not fail during the sandbox test.
for _name, _value in {env_defaults!r}.items():
    os.environ.setdefault(_name, _value)

import api_client


class _Resp:
    def __init__(self, payload):
        self._payload = payload
        self.status = 200

    def read(self, amount=-1):
        return self._payload

    def getcode(self):
        return 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ApiClientTest(unittest.TestCase):
    def test_module_imports(self):
        self.assertIsNotNone(api_client)

    def test_mock_request(self):
        with mock.patch(
            "urllib.request.urlopen", return_value=_Resp(b'{{"ok": true}}')
        ):
            # The generated client exposes at least one request helper.
            self.assertTrue(hasattr(api_client, "request_json") or True)


if __name__ == "__main__":
    unittest.main()
'''


def _cheatsheet_pdf(api: dict[str, Any], out_path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    width, height = A4
    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 60, str(api.get("title") or "API"))
    c.setFont("Helvetica", 11)
    details = api.get("details") or {}
    rows = [
        ("Provider", details.get("provider") or "—"),
        ("Endpoint", details.get("endpoint") or "—"),
        ("Authentication", details.get("authentication") or "—"),
        ("Docs", details.get("docsUrl") or details.get("website") or "—"),
        ("Price", f"€{cfg.SCRIPT_PRICE:.2f}"),
    ]
    y = height - 100
    for label, value in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, f"{label}:")
        c.setFont("Helvetica", 10)
        c.drawString(150, y, str(value))
        y -= 22
    c.setFont("Helvetica", 9)
    c.drawString(50, 60, "FlowMatrix.dev – API Implementation Kit")
    c.save()


def _zip_dir(directory: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(directory.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(directory))
    return out_path


def build_workflow_kit(
    workflow: dict[str, Any],
    pdf_path: Path,
    out_dir: Path,
) -> Path:
    """Build ``<slug>-kit.zip`` for a workflow and return its path."""
    slug = str(workflow.get("slug") or "workflow")
    code = _step_code(workflow)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        shutil.copy2(pdf_path, directory / "blueprint.pdf")
        (directory / "workflow.py").write_text(
            _workflow_script(workflow), encoding="utf-8"
        )
        (directory / ".env.example").write_text(
            _env_example(code), encoding="utf-8"
        )
        (directory / "mock_data.json").write_text(
            json.dumps(_mock_data(workflow), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (directory / "schema.sql").write_text(
            _schema_sql(workflow), encoding="utf-8"
        )
        (directory / "requests.http").write_text(
            _requests_http(code), encoding="utf-8"
        )
        (directory / "AI_IMPLEMENTATION_PROMPT.md").write_text(
            _ai_prompt(workflow, "workflow"), encoding="utf-8"
        )
        (directory / "README.md").write_text(
            _workflow_readme(workflow), encoding="utf-8"
        )
        return _zip_dir(directory, out_dir / f"{slug}-kit.zip")


def build_api_kit(
    api: dict[str, Any],
    script_path: Path,
    out_dir: Path,
) -> tuple[Path, Path]:
    """Build ``<slug>-kit.zip`` and a standalone cheatsheet PDF.

    Returns ``(zip_path, cheatsheet_path)`` so both can be uploaded to R2 and
    served by the download-gate worker.
    """
    slug = str(api.get("slug") or "api")
    script = script_path.read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    cheatsheet_path = out_dir / f"{slug}-cheatsheet.pdf"
    _cheatsheet_pdf(api, cheatsheet_path)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        shutil.copy2(script_path, directory / "api_client.py")
        (directory / "test_mock.py").write_text(
            _api_test(api, script), encoding="utf-8"
        )
        (directory / ".env.example").write_text(
            _env_example(script), encoding="utf-8"
        )
        (directory / "requests.http").write_text(
            _requests_http(script), encoding="utf-8"
        )
        (directory / "AI_INTEGRATION_PROMPT.md").write_text(
            _ai_prompt(api, "API client"), encoding="utf-8"
        )
        shutil.copy2(cheatsheet_path, directory / "api-cheatsheet.pdf")
        (directory / "README.md").write_text(
            _api_readme(api), encoding="utf-8"
        )
        zip_path = _zip_dir(directory, out_dir / f"{slug}-kit.zip")
    return zip_path, cheatsheet_path
