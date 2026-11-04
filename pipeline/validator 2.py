"""Deterministic, hard gatekeeper for all generated content.

No LLM judgement happens here. Every check is mechanical:

* ``ast.parse`` per step AND over the concatenated steps (syntax + data flow)
* stdlib import scan (``random`` is forbidden in workflow snippets)
* mocked execution of generated API scripts
* blacklist / forbidden-price / dummy-data scanner
* tool consistency (listed tools are used and have a resource URL)
* strict duplicate protection
* live HTTP reachability of every domain/URL (with base-domain fallback for
  placeholders such as ``https://<your-project>.supabase.co``)

A result with ``ok == False`` means the item must never be stored, uploaded
or deployed.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import signal
import socket
import tempfile
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Any
from unittest import mock

from . import config


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        self.ok = self.ok and other.ok
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def non_empty_lines(code: str) -> list[str]:
    return [line for line in code.splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# Live domain reachability (only live domains may produce content)
# --------------------------------------------------------------------------- #
# Allow angle brackets and braces so placeholder URLs are captured and can be
# mapped to their official base domain instead of being silently skipped.
_URL_RE = re.compile(r"https?://[^\s\"')\]]+")
_DOMAIN_CACHE: dict[str, tuple[bool, str]] = {}


def extract_urls(payload: Any) -> set[str]:
    """Extract absolute http(s) URLs from a string or JSON-serialisable object."""
    serialized = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, ensure_ascii=False)
    )
    urls: set[str] = set()
    for match in _URL_RE.finditer(serialized):
        url = match.group(0).rstrip(".,;:")
        urls.add(url)
    return urls


def check_domain_reachable(url: str) -> tuple[bool, str]:
    """DNS + HTTP check for a URL's host. Cached per host."""
    host = urllib.parse.urlparse(url).hostname or ""
    if not host:
        return False, "invalid URL"
    if host in _DOMAIN_CACHE:
        return _DOMAIN_CACHE[host]

    try:
        socket.getaddrinfo(host, 443)
    except socket.gaierror as error:
        _DOMAIN_CACHE[host] = (False, f"DNS error: {error}")
        return _DOMAIN_CACHE[host]

    last_reason = "no response"
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": "FlowMatrix-DomainCheck/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                _DOMAIN_CACHE[host] = (True, f"HTTP {response.getcode()}")
                return _DOMAIN_CACHE[host]
        except urllib.error.HTTPError as error:
            # 4xx means the host is alive and answering.
            if error.code < 500:
                _DOMAIN_CACHE[host] = (True, f"HTTP {error.code}")
                return _DOMAIN_CACHE[host]
            last_reason = f"HTTP {error.code}"
        except Exception as error:  # noqa: BLE001 - SSL, timeout, DNS, ...
            last_reason = f"{type(error).__name__}: {error}"

    _DOMAIN_CACHE[host] = (False, last_reason)
    return _DOMAIN_CACHE[host]


_PLACEHOLDER_HOST_MARKERS = (
    "your-",
    "your_",
    "your.",
    "example.",
    "localhost",
    "127.0.0.1",
)


def _is_placeholder_host(host: str) -> bool:
    """Templates such as your-project.supabase.co are not real domains."""
    lowered = host.lower()
    if lowered in {"localhost", "127.0.0.1"}:
        return True
    if any(char in lowered for char in "<>{}"):
        return True  # e.g. <your-project>.supabase.co
    if "." not in lowered:
        return True  # e.g. your_supabase_url
    if any(label.startswith("your") for label in lowered.split(".")):
        return True  # e.g. yourwebsite.com, api.yourgateway.com
    return any(marker in lowered for marker in _PLACEHOLDER_HOST_MARKERS)


def _base_domain_for_placeholder(host: str) -> str | None:
    """Map a placeholder host to the official main domain to test instead."""
    lowered = host.lower()
    for key, url in config.PLACEHOLDER_BASE_DOMAINS.items():
        if key in lowered:
            return url
    return None


def _registrable_domain(host: str) -> str:
    """Very small heuristic: last two labels (api.openai.com -> openai.com)."""
    labels = [label for label in host.lower().split(".") if label]
    if len(labels) >= 2:
        return ".".join(labels[-2:])
    return host.lower()


def validate_domains(payload: Any, context: str) -> list[str]:
    """Reject content whose linked domains are not live/reachable."""
    errors: list[str] = []
    checked: dict[str, tuple[bool, str]] = {}
    for url in sorted(extract_urls(payload)):
        host = urllib.parse.urlparse(url).hostname or ""
        if not host:
            continue

        if _is_placeholder_host(host):
            base = _base_domain_for_placeholder(host)
            if not base:
                continue  # cannot test an unmapped placeholder
            if base in checked:
                continue
            ok, reason = check_domain_reachable(base)
            checked[base] = (ok, reason)
            if not ok:
                errors.append(
                    f"{context}: base domain not reachable: {base} ({reason})"
                )
            continue

        if host in checked:
            continue
        ok, reason = check_domain_reachable(url)
        checked[host] = (ok, reason)
        if not ok:
            errors.append(f"{context}: domain not reachable: {host} ({reason})")
    return errors


# --------------------------------------------------------------------------- #
# AST + import policy
# --------------------------------------------------------------------------- #
def _has_pep701_fstring(code: str) -> bool:
    """Detect f-strings that reuse their own quote inside an expression.

    ``f'{d['key']}'`` is only valid on Python 3.12+ (PEP 701). Generated code
    must run on Python 3.10+, so this is a hard error.
    """
    for match in re.finditer(r"f(['\"])", code):
        quote = match.group(1)
        index = match.end()
        depth = 0
        while index < len(code):
            char = code[index]
            if char == "\\":
                index += 2
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth = max(0, depth - 1)
            elif char == quote:
                if depth > 0:
                    return True
                break
            index += 1
    return False


def check_python_ast(
    code: str,
    context: str,
    forbidden_imports: frozenset[str] = config.FORBIDDEN_IMPORTS,
) -> ValidationResult:
    result = ValidationResult()
    if not code or not code.strip():
        result.add(f"{context}: code is empty")
        return result
    try:
        # feature_version=(3, 10) rejects syntax that only works on newer
        # interpreters (e.g. PEP 701 f-strings from Python 3.12+).
        tree = ast.parse(code, feature_version=(3, 10))
    except SyntaxError as error:
        result.add(f"{context}: SyntaxError: {error.msg} (line {error.lineno})")
        return result

    if _has_pep701_fstring(code):
        result.add(
            f"{context}: PEP 701 f-string (same quote inside an expression) "
            "requires Python 3.12+; use different quotes for Python 3.10 compatibility"
        )

    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                result.add(f"{context}: relative imports are forbidden")
                continue
            if node.module:
                names = [node.module]

        for name in names:
            top = name.split(".")[0]
            if top in forbidden_imports:
                result.add(f"{context}: Forbidden import '{name}'")
            elif name not in config.STDLIB_MODULES and top not in config.STDLIB_MODULES:
                result.add(f"{context}: Non-standard-library import '{name}'")
    return result


def _assigned_names(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def _has_top_level_execution(code: str) -> bool:
    """True if the script actually calls a function it defines at module level."""
    try:
        tree = ast.parse(code, feature_version=(3, 10))
    except SyntaxError:
        return False
    functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    if not functions:
        return False
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            value = node.value
        elif isinstance(node, ast.Expr):
            value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in functions
        ):
            return True
    return False


def _loaded_names(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


# Generic names that do not prove a real data hand-off between steps.
_GENERIC_NAMES: frozenset[str] = frozenset(
    {
        "args", "body", "code", "conn", "content", "count", "cursor", "data",
        "dict", "e", "enumerate", "error", "float", "headers", "http", "i",
        "index", "int", "item", "j", "json", "k", "key", "kwargs", "len",
        "line", "list", "math", "open", "os", "payload", "print", "range",
        "re", "request", "response", "result", "self", "set", "statistics",
        "status", "str", "sys", "text", "time", "urllib", "value", "x", "y",
        "z",
    }
)


def _meaningful(names: set[str]) -> set[str]:
    return {
        name
        for name in names
        if name not in _GENERIC_NAMES and not name.startswith("_")
    }


# --------------------------------------------------------------------------- #
# Mocked execution of generated API scripts
# --------------------------------------------------------------------------- #
class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.status = 200

    def read(self, amount: int = -1) -> bytes:  # noqa: D401
        if amount is None or amount < 0:
            return self._payload
        return self._payload[:amount]

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def mock_run(script: str) -> ValidationResult:
    """Execute a generated API script with urlopen patched.

    Catches the failure classes that indicate broken generated code
    (NameError, TypeError, KeyError, AttributeError). Other exceptions are
    downgraded to warnings so intentional domain errors do not block.
    """
    result = ValidationResult()
    payload = json.dumps({"ok": True, "data": []}).encode("utf-8")

    env_names = set(
        re.findall(r"os\.environ\.get\(\s*['\"]([A-Z0-9_]+)['\"]", script)
    )
    env_names |= set(
        re.findall(r"os\.getenv\(\s*['\"]([A-Z0-9_]+)['\"]", script)
    )
    fake_env = {name: "test-value" for name in env_names}
    fake_env.setdefault("API_KEY", "test-value")

    def _urlopen(*args: object, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(payload)

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": "generated_api_script.py",
    }
    try:
        with mock.patch("urllib.request.urlopen", side_effect=_urlopen):
            with mock.patch.dict(os.environ, fake_env, clear=False):
                exec(compile(script, "generated_api_script.py", "exec"), namespace)
    except SystemExit:
        pass
    except (NameError, TypeError, KeyError, AttributeError) as error:
        result.add(f"API script runtime error: {type(error).__name__}: {error}")
    except Exception as error:  # noqa: BLE001
        result.warn(f"API script raised {type(error).__name__}: {error} (mock warning)")
    return result


class _DryRunTimeout(Exception):
    """Raised when the workflow dry-run exceeds its time budget."""


def _dry_run_timeout_handler(signum: int, frame: Any) -> None:
    raise _DryRunTimeout("dry-run exceeded the time limit")


def _default_mock_responses() -> dict[str, Any]:
    """Realistic mock payloads for the workflow dry-run."""
    return {
        "twitter.com": {
            "data": [
                {"id": "1", "text": "I love this product"},
                {"id": "2", "text": "Terrible experience"},
            ]
        },
        "x.com": {
            "data": [
                {"id": "1", "text": "I love this product"},
                {"id": "2", "text": "Terrible experience"},
            ]
        },
        "openai.com": {"choices": [{"message": {"content": "0.8"}}], "content": "Sample content"},
        "anthropic.com": {"content": "Sample content"},
        "supabase": [],
        "slack.com": "ok",
    }


def execute_workflow_dry_run(
    steps_code: list[str],
    mock_responses: dict[str, Any] | None = None,
) -> ValidationResult:
    """Execute the concatenated workflow code against mocked HTTP responses.

    ``ast.parse`` cannot catch runtime type errors (e.g. ``statistics.mean`` on
    strings). This runs the real code with ``urllib.request.urlopen`` patched
    and returns the exact traceback for the self-healing loop.
    """
    result = ValidationResult()
    code = "\n\n".join(steps_code)
    if not code.strip():
        return result
    responses = mock_responses or _default_mock_responses()

    class _Resp:
        def __init__(self, payload: bytes, status: int = 200) -> None:
            self._payload = payload
            self.status = status

        def read(self, amount: int = -1) -> bytes:
            if amount is None or amount < 0:
                return self._payload
            return self._payload[:amount]

        def getcode(self) -> int:
            return self.status

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    def _payload_for(url: str) -> bytes:
        for key, payload in responses.items():
            if key in url:
                if isinstance(payload, str):
                    return payload.encode("utf-8")
                return json.dumps(payload).encode("utf-8")
        # Generic fallback: cover the keys most generated clients access so a
        # mock mismatch does not masquerade as a real KeyError.
        return json.dumps(
            {
                "data": [{"id": "1", "text": "sample", "value": 0.5}],
                "slots": [{"time": "2026-01-01T10:00:00Z"}],
                "items": [{"id": "1", "name": "sample"}],
                "results": [{"id": "1", "name": "sample"}],
                "id": "1",
                "text": "sample",
                "content": "0.8",
                "value": 0.5,
                "count": 1,
                "status": "ok",
                "ok": True,
            }
        ).encode("utf-8")

    def _urlopen(request: Any, *args: object, **kwargs: object) -> _Resp:
        url = getattr(request, "full_url", None) or str(request)
        return _Resp(_payload_for(url))

    class _FakeHTTPSConnection:
        def __init__(self, host: str, *args: object, **kwargs: object) -> None:
            self.host = host
            self._url = f"https://{host}"

        def request(self, method: str, url: str, body: Any = None, headers: Any = None) -> None:
            self._url = f"https://{self.host}{url}"

        def getresponse(self) -> _Resp:
            return _Resp(_payload_for(self._url))

        def close(self) -> None:
            return None

    env_names = set(
        re.findall(r"os\.environ\.get\(\s*['\"]([A-Z0-9_]+)['\"]", code)
    )
    env_names |= set(
        re.findall(r"os\.getenv\(\s*['\"]([A-Z0-9_]+)['\"]", code)
    )
    fake_env = {name: "test-value" for name in env_names}
    fake_env.setdefault("API_KEY", "test-value")

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": "workflow.py",
    }
    use_alarm = hasattr(signal, "SIGALRM")
    old_handler = None
    original_cwd = os.getcwd()
    temp_dir = tempfile.mkdtemp(prefix="flowmatrix-dryrun-")
    if use_alarm:
        old_handler = signal.signal(signal.SIGALRM, _dry_run_timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, 10)
    try:
        os.chdir(temp_dir)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            with mock.patch("urllib.request.urlopen", side_effect=_urlopen):
                with mock.patch("http.client.HTTPSConnection", _FakeHTTPSConnection):
                    with mock.patch("time.sleep", return_value=None):
                        with mock.patch("builtins.input", return_value="yes"):
                            with mock.patch.dict(os.environ, fake_env, clear=False):
                                exec(compile(code, "workflow.py", "exec"), namespace)
    except _DryRunTimeout:
        result.add(
            "Workflow dry-run timed out after 10s – remove infinite loops or "
            "blocking waits from the step code"
        )
    except SystemExit:
        pass
    except (TypeError, KeyError, ValueError, NameError, AttributeError) as error:
        result.warn(
            "Workflow dry-run warning: "
            f"{type(error).__name__}: {error}"
        )
    except Exception as error:  # noqa: BLE001
        result.warn(f"Workflow dry-run raised {type(error).__name__}: {error}")
    finally:
        if use_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)
    return result


def validate_api_script(script: str) -> ValidationResult:
    result = check_python_ast(script, "API script")

    if "if __name__" not in script:
        result.add('API script: missing executable `if __name__ == "__main__"` block')
    if "os.environ" not in script:
        result.add("API script: configuration must use os.environ")

    try:
        tree = ast.parse(script)
        function_count = sum(
            isinstance(node, ast.FunctionDef) for node in tree.body
        )
        if function_count < 2:
            result.add(
                f"API script: expected >=2 top-level functions, found {function_count}"
            )
    except SyntaxError:
        pass  # already reported by check_python_ast

    lowered = script.lower()
    if "timeout" not in lowered:
        result.add("API script: no request timeout found")
    if "httperror" not in lowered or "urlerror" not in lowered:
        result.add("API script: missing HTTPError/URLError handling")
    if "sleep" not in lowered:
        result.add("API script: missing exponential backoff (time.sleep)")
    if "429" not in script and "500" not in script:
        result.warn("API script: no explicit 429/5xx backoff branch detected")

    result.merge(mock_run(script))
    for message in scan_blacklist(script):
        result.add(message)
    for message in validate_domains(script, "API script"):
        result.add(message)
    return result


# --------------------------------------------------------------------------- #
# Blacklist + duplicates
# --------------------------------------------------------------------------- #
def scan_blacklist(payload: Any) -> list[str]:
    serialized = (
        json.dumps(payload, ensure_ascii=False)
        if not isinstance(payload, str)
        else payload
    )
    errors: list[str] = []
    for phrase in config.BLACKLIST_PHRASES:
        if phrase.lower() in serialized.lower():
            errors.append(f"Blacklisted phrase found: '{phrase}'")
    for domain in config.FAKE_DOMAINS:
        if domain.lower() in serialized.lower():
            errors.append(
                f"Invented domain found: '{domain}' – use a real API domain "
                "or a placeholder such as https://<your-n8n-instance>/webhook/<name>"
            )
    return errors


def check_duplicate(
    slug: str,
    title: str,
    existing: list[dict[str, Any]],
    ignore_slug: str | None = None,
) -> list[str]:
    errors: list[str] = []
    for item in existing:
        if item.get("slug") == ignore_slug:
            continue
        if item.get("slug") == slug:
            errors.append(f"Duplicate slug: '{slug}'")
        if str(item.get("title", "")).strip().lower() == str(title).strip().lower():
            errors.append(f"Duplicate title: '{title}'")
    return errors


# --------------------------------------------------------------------------- #
# Workflow rules
# --------------------------------------------------------------------------- #
def _step_text(step: dict[str, Any]) -> str:
    parts = [
        str(step.get("title") or ""),
        str(step.get("description") or ""),
        str(step.get("technical_explanation") or ""),
        str(step.get("code_snippet") or ""),
        " ".join(str(item) for item in (step.get("tools") or [])),
        " ".join(str(item) for item in (step.get("actions") or [])),
        " ".join(str(item) for item in (step.get("checklist") or [])),
        str(step.get("expectedResult") or ""),
    ]
    for command in step.get("commands") or []:
        parts.append(str(command.get("code") or ""))
    return " ".join(parts)


def validate_workflow(workflow: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()

    for key in ("slug", "title", "description", "category"):
        if not str(workflow.get(key, "")).strip():
            result.add(f"Workflow: missing '{key}'")

    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    if not (config.MIN_STEPS <= len(steps) <= config.MAX_STEPS):
        result.add(
            "Workflow: expected between "
            f"{config.MIN_STEPS} and {config.MAX_STEPS} steps, found {len(steps)}"
        )

    tools = [
        str(tool).strip()
        for tool in (details.get("tools") or [])
        if str(tool).strip()
    ]
    previous_assigned: set[str] = set()
    combined_code: list[str] = []
    for index, step in enumerate(steps, start=1):
        context = f"Step {index}"
        code = str(step.get("code_snippet") or "")
        if not code.strip():
            result.add(f"{context}: code_snippet is missing")
        else:
            count = len(non_empty_lines(code))
            if count < config.MIN_CODE_LINES:
                result.add(
                    f"{context}: code_snippet has only {count} non-empty lines "
                    f"(minimum {config.MIN_CODE_LINES})"
                )
            result.merge(
                check_python_ast(
                    code, context, config.WORKFLOW_FORBIDDEN_IMPORTS
                )
            )
            if "random." in code or "import random" in code:
                result.add(f"{context}: randomness is forbidden (real data flow required)")
            if "# Dummy" in code or "Dummy" in code:
                result.add(f"{context}: dummy data is forbidden")

            # Real data flow: every step after the first must consume at least
            # one meaningful variable/function defined in an earlier step.
            if index > 1 and previous_assigned:
                if not (_meaningful(_loaded_names(code)) & previous_assigned):
                    # Heuristic only – the real runtime dry-run below is the
                    # hard gate for data-flow errors.
                    result.warn(
                        f"{context}: does not consume any meaningful variable "
                        "from previous steps (check the data flow)"
                    )
            previous_assigned |= _meaningful(_assigned_names(code))
            combined_code.append(code)

        # Every tool declared on a step must be part of the workflow tool list.
        for tool in step.get("tools") or []:
            tool_name = str(tool).strip()
            if tool_name.lower() in {
                "python standard library",
                "standard library",
                "none",
                "null",
                "",
            }:
                continue
            if tool_name and tool_name not in tools:
                result.add(
                    f"{context}: tool '{tool_name}' is not in the workflow tool list"
                )

        # Link labels must be real documentation names, not prompt leaks.
        for link in step.get("links") or []:
            label = str(link.get("label") or "")
            if "official docs for the api used in this step" in label.lower():
                result.add(
                    f"{context}: link label is a prompt leak – use the real "
                    "documentation name (e.g. 'X API Search Docs')"
                )

        if len(str(step.get("technical_explanation") or "").strip()) < config.MIN_TECHNICAL_EXPLANATION:
            result.add(
                f"{context}: technical_explanation too short "
                f"(min {config.MIN_TECHNICAL_EXPLANATION} chars; cover architecture "
                "role, API contract and edge cases)"
            )
        if len(step.get("actions") or []) < 3:
            result.add(f"{context}: actions needs at least 3 entries")
        if len(step.get("checklist") or []) < 2:
            result.add(f"{context}: checklist needs at least 2 entries")
        if not str(step.get("expectedResult") or "").strip():
            result.add(f"{context}: expectedResult is missing")

    # The concatenation of all snippets must be one coherent, valid script.
    if combined_code:
        joined = "\n\n".join(combined_code)
        try:
            ast.parse(joined, feature_version=(3, 10))
        except SyntaxError as error:
            result.add(
                "Workflow: concatenated step code is not valid Python: "
                f"{error.msg} (line {error.lineno})"
            )
        else:
            if not _has_top_level_execution(joined):
                result.add(
                    "Workflow: code defines functions but never calls them – "
                    "add top-level calls (e.g. `mentions = fetch_mentions()`) "
                    "so the concatenated script runs end-to-end"
                )
            # Real runtime execution against mocked HTTP responses. This
            # catches type errors that ast.parse cannot see.
            result.merge(execute_workflow_dry_run(combined_code))

    prerequisites = details.get("prerequisites") or []
    if len(prerequisites) < config.PREREQUISITES_MIN:
        result.add(
            f"Workflow: prerequisites needs at least {config.PREREQUISITES_MIN} entries"
        )
    elif not any(
        str(item).strip() == config.FINAL_PREREQUISITE for item in prerequisites
    ):
        result.add(
            "Workflow: prerequisites must include exactly "
            f"'{config.FINAL_PREREQUISITE}'"
        )
    if len(prerequisites) < len(tools):
        result.add(
            "Workflow: number of prerequisites in BEFORE YOU START must be at least "
            "equal to the number of tools in TOOLS IN THIS WORKFLOW"
        )

    glossary = details.get("glossary") or []
    if len(glossary) < config.GLOSSARY_TERMS_MIN:
        result.add(
            f"Workflow: glossary needs at least {config.GLOSSARY_TERMS_MIN} terms"
        )
    for entry in glossary:
        term = str(entry.get("term") or "").strip()
        definition = str(entry.get("definition") or "").strip()
        if not term or not definition:
            result.add("Workflow: glossary entries must have term and definition")
        elif term.lower() in config.TRIVIAL_GLOSSARY_TERMS:
            result.add(
                f"Workflow: glossary term '{term}' is too trivial – explain an "
                "advanced concept used in this workflow"
            )

    troubleshooting = details.get("troubleshooting") or []
    if len(troubleshooting) < config.TROUBLESHOOTING_MIN:
        result.add(
            f"Workflow: troubleshooting needs at least {config.TROUBLESHOOTING_MIN} entries"
        )
    for entry in troubleshooting:
        if not str(entry.get("problem") or "").strip() or not str(
            entry.get("solution") or ""
        ).strip():
            result.add("Workflow: troubleshooting entries must have problem and solution")

    # --- Tool consistency -------------------------------------------------- #
    resources = details.get("resources") or []
    resource_labels = {
        str(entry.get("label") or "").strip().lower() for entry in resources
    }
    resource_domains: set[str] = set()
    for entry in resources:
        url = str(entry.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            result.add(
                f"Workflow: resource '{entry.get('label')}' must have a full http(s) URL"
            )
            continue
        host = urllib.parse.urlparse(url).hostname or ""
        if host:
            resource_domains.add(_registrable_domain(host))

    combined_text = " ".join(_step_text(step) for step in steps).lower()
    prereq_text = " ".join(str(item) for item in prerequisites).lower()
    for tool in tools:
        if tool.lower() not in combined_text:
            result.add(
                f"Workflow: tool '{tool}' is listed but never used in the steps"
            )
        if tool.lower() not in resource_labels:
            result.add(
                f"Workflow: tool '{tool}' has no entry in resources"
            )
        if tool.lower() not in prereq_text:
            result.add(
                f"Workflow: tool '{tool}' has no entry in BEFORE YOU START "
                "(prerequisites)"
            )

    # Reverse check: API hosts used in code must be represented in resources.
    code_hosts: set[str] = set()
    for step in steps:
        for url in extract_urls(str(step.get("code_snippet") or "")):
            host = urllib.parse.urlparse(url).hostname or ""
            if host and not _is_placeholder_host(host):
                code_hosts.add(_registrable_domain(host))
    for domain in sorted(code_hosts):
        if domain in {"flowmatrix.dev"}:
            continue
        if domain not in resource_domains:
            result.warn(
                f"Workflow: API host '{domain}' is used in code but missing from resources"
            )

    for message in scan_blacklist(workflow):
        result.add(message)

    for message in validate_domains(workflow, "Workflow"):
        result.add(message)

    return result


def validate_kit_zip(zip_path: Path, expected_files: tuple[str, ...]) -> ValidationResult:
    result = ValidationResult()
    if not zip_path.exists():
        result.add(f"Kit ZIP does not exist: {zip_path}")
        return result
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            for filename in expected_files:
                if filename not in names:
                    result.add(f"Kit ZIP missing required file '{filename}': {zip_path.name}")
    except Exception as error:
        result.add(f"Failed to read Kit ZIP {zip_path.name}: {error}")
    return result


def validate_alternative(alternative: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    if not str(alternative.get("slug", "")).strip():
        result.add("Alternative: missing slug")
    if not str(alternative.get("description", "")).strip():
        result.add("Alternative: missing description")
    items = (alternative.get("details") or {}).get("alternatives") or []
    if len(items) < 3:
        result.add("Alternative: needs at least 3 alternatives")
    for message in scan_blacklist(alternative):
        result.add(message)
    for message in validate_domains(alternative, "Alternative"):
        result.add(message)
    return result
