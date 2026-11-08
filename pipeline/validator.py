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
import builtins
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
from pathlib import Path
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


def _dns_resolves(host: str) -> bool:
    """Resolve a host via DNS – a lenient fallback for API endpoint domains."""
    if not host:
        return False
    try:
        socket.gethostbyname(host)
        return True
    except OSError:
        return False


def _tcp_reachable(host: str, port: int = 443, timeout: float = 5.0) -> tuple[bool, str]:
    """Bounded TCP connect with a DNS fallback for blocked ports."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "TCP reachable"
    except OSError as error:
        if _dns_resolves(host):
            return True, "DNS resolves (TCP blocked)"
        return False, f"{type(error).__name__}: {error}"


def check_domain_reachable(url: str) -> tuple[bool, str]:
    """HTTP check for one exact URL. Cached per URL (not per host)."""
    host = urllib.parse.urlparse(url).hostname or ""
    if not host:
        return False, "invalid URL"
    cache_key = url
    if cache_key in _DOMAIN_CACHE:
        return _DOMAIN_CACHE[cache_key]

    last_reason = "no response"
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url,
            method=method,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                _DOMAIN_CACHE[cache_key] = (True, f"HTTP {response.getcode()}")
                return _DOMAIN_CACHE[cache_key]
        except urllib.error.HTTPError as error:
            # 401/403/429 prove the host is alive but protected/rate-limited.
            # 404/410 and every 5xx mean the exact URL is gone or broken and
            # must trigger a hard workflow rejection + topic regeneration.
            # Any 4xx except 404/410 proves the endpoint exists; the request
            # was simply missing auth, used the wrong method or malformed data.
            if 400 <= error.code < 500 and error.code not in (404, 410):
                _DOMAIN_CACHE[cache_key] = (True, f"HTTP {error.code}")
                return _DOMAIN_CACHE[cache_key]
            last_reason = f"HTTP {error.code}"
        except Exception as error:  # noqa: BLE001 - SSL, timeout, DNS, ...
            last_reason = f"{type(error).__name__}: {error}"

    # Official API endpoint domains (e.g. api.together.xyz) often reject HEAD
    # or return 404 on the bare host while the documented path works. A
    # successful DNS resolution is therefore accepted as a valid endpoint.
    if _dns_resolves(host):
        _DOMAIN_CACHE[cache_key] = (True, "DNS resolves")
    else:
        _DOMAIN_CACHE[cache_key] = (False, last_reason)
    return _DOMAIN_CACHE[cache_key]


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


def _domain_matches(host: str, allowed: set[str]) -> bool:
    """Case-insensitive subdomain/root-domain matching."""
    host = host.lower().strip()
    for domain in allowed:
        domain = domain.lower().strip()
        if not domain:
            continue
        if host == domain or host.endswith("." + domain) or domain.endswith("." + host):
            return True
    return False


_CATALOG_CACHE: dict[str, Any] | None = None


def _catalog() -> dict[str, Any]:
    """Load the API/alternative catalogue once for grounding checks."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    apis: list[dict[str, Any]] = []
    alternatives: list[dict[str, Any]] = []
    if config.APIS_FILE.exists():
        apis = json.loads(config.APIS_FILE.read_text(encoding="utf-8"))
    if config.ALTERNATIVES_FILE.exists():
        alternatives = json.loads(
            config.ALTERNATIVES_FILE.read_text(encoding="utf-8")
        )
    _CATALOG_CACHE = {
        "apis": {str(item.get("slug")): item for item in apis},
        "apis_by_title": {str(item.get("title")): item for item in apis},
        "alternatives": {
            str(item.get("slug")): item for item in alternatives
        },
    }
    return _CATALOG_CACHE


def _api_markers(api: dict[str, Any]) -> tuple[str, ...]:
    """Strings that prove a curated API is actually called in code."""
    details = api.get("details") or {}
    markers: list[str] = []
    # Add slug and title (case-insensitive matching happens at the call site).
    for raw in (api.get("slug"), api.get("title")):
        value = str(raw or "").strip().lower()
        if value and value not in markers:
            markers.append(value)
    # Add provider.
    provider = str(details.get("provider") or "").strip().lower()
    if provider and provider not in markers:
        markers.append(provider)
    # Add hosts and their registrable/root domains from endpoint, docs, website.
    for raw in (
        details.get("endpoint"),
        details.get("docsUrl"),
        details.get("website"),
    ):
        value = str(raw or "")
        if not value or "<" in value or "{" in value:
            continue
        host = urllib.parse.urlparse(value).hostname or ""
        if not host:
            continue
        for candidate in (host, _registrable_domain(host), host.split(".")[0]):
            candidate = candidate.strip().lower()
            if candidate and candidate not in markers:
                markers.append(candidate)
    return tuple(markers) or (str(api.get("title") or "").lower(),)


def _api_link_domains(api: dict[str, Any]) -> set[str]:
    """Registrable documentation domains for a curated API."""
    details = api.get("details") or {}
    domains: set[str] = set()
    for raw in (details.get("docsUrl"), details.get("website")):
        host = urllib.parse.urlparse(str(raw or "")).hostname or ""
        if host:
            domains.add(_registrable_domain(host))
    return domains


def validate_domains(payload: Any, context: str) -> list[str]:
    """Reject content whose linked domains are not live/reachable."""
    if os.environ.get("FLOWMATRIX_SKIP_LIVE") == "1":
        return []
    errors: list[str] = []
    checked: dict[str, tuple[bool, str]] = {}
    for url in sorted(extract_urls(payload)):
        parsed_url = urllib.parse.urlparse(url)
        host = parsed_url.hostname or ""
        if not host:
            continue

        # A bare host such as https://rest.ably.io is an API base URL. APIs
        # routinely answer 404 on the bare host while /time or /v1 works, so
        # only a bounded TCP reachability check is meaningful here.
        if parsed_url.path in ("", "/"):
            ok, reason = _tcp_reachable(host)
            if not ok:
                errors.append(
                    f"{context}: base host not reachable: {host} ({reason})"
                )
            continue

        # Placeholder paths such as /bot{token}/sendMessage or
        # /Accounts/{os.environ.get(...)} cannot be tested directly. Only the
        # TCP reachability of the real host is meaningful.
        if "{" in url or "}" in url:
            ok, reason = _tcp_reachable(host)
            if not ok:
                errors.append(
                    f"{context}: placeholder host not reachable: {host} ({reason})"
                )
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

        if url in checked:
            continue
        ok, reason = check_domain_reachable(url)
        checked[url] = (ok, reason)
        if not ok:
            errors.append(f"{context}: URL not reachable: {url} ({reason})")
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

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            imported_modules.update(
                alias.name.split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                result.add(f"{context}: relative imports are forbidden")
                continue
            if node.module:
                names = [node.module]
                imported_modules.add(node.module.split(".")[0])

        for name in names:
            top = name.split(".")[0]
            if top in forbidden_imports:
                result.add(f"{context}: Forbidden import '{name}'")
            elif name not in config.STDLIB_MODULES and top not in config.STDLIB_MODULES:
                result.add(f"{context}: Non-standard-library import '{name}'")

    for module in sorted(config.FREQUENT_MODULES):
        if re.search(rf"\b{re.escape(module)}\.", code) and module not in imported_modules:
            result.add(
                f"{context}: module '{module}' is used but never imported – "
                f"add 'import {module}' at the top of this snippet"
            )
    return result


def _assigned_names(code: str) -> set[str]:
    """Module-level names that form the cross-step data flow.

    Local variables inside functions are implementation details and must not be
    mistaken for step output.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def _self_reassignments(code: str) -> set[str]:
    """Names reassigned from a value that references the same name.

    ``topics = refine_topics(topics)`` is a legitimate transformation;
    ``mentions = ["dummy"]`` is a forbidden overwrite.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        loaded = {
            child.id
            for child in ast.walk(node.value)
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
        }
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in loaded:
                names.add(target.id)
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
        elif isinstance(node, ast.If):
            # `if __name__ == "__main__": main()` is a valid top-level call.
            if any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id in functions
                for child in ast.walk(node)
            ):
                return True
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
        "status", "str", "sys", "text", "time", "urllib", "url", "value",
        "x", "y", "z",
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


def _fake_env_value(name: str) -> str:
    """Realistic mock environment values for the dry-run.

    URL-like variables must contain a valid absolute URL because
    ``urllib.request.Request`` parses the URL before ``urlopen`` is patched.
    Secrets stay harmless placeholders.
    """
    upper = name.upper()
    is_url = (
        upper.endswith("_URL")
        or upper.endswith("URL")
        or "BASE_URL" in upper
        or "WEBHOOK" in upper
        or upper.endswith("_ENDPOINT")
        or upper.endswith("_HOST")
    )
    if "SUPABASE" in upper:
        return "https://mock.supabase.co" if is_url else "test-value"
    if "SLACK" in upper:
        return "https://hooks.slack.com/services/mock" if is_url else "test-value"
    if "OPENAI" in upper:
        return "https://api.openai.com" if is_url else "test-value"
    if upper.startswith("X_") or "TWITTER" in upper:
        return "https://api.x.com" if is_url else "test-value"
    if is_url:
        return "https://example.com"
    return "test-value"


def mock_run(script: str) -> ValidationResult:
    """Execute a generated API script with urlopen patched.

    Catches the failure classes that indicate broken generated code
    (NameError, TypeError, KeyError, AttributeError). Other exceptions are
    downgraded to warnings so intentional domain errors do not block.
    """
    result = ValidationResult()
    payload = json.dumps(
        {
            "ok": True,
            "data": [{"id": "1", "text": "sample", "value": 0.5}],
            "items": [{"id": "1", "name": "sample"}],
            "results": [{"id": "1", "name": "sample"}],
            "choices": [{"message": {"content": "0.8"}}],
            "content": "0.8",
            "value": 0.5,
            "status": "ok",
        }
    ).encode("utf-8")

    env_names = set(
        re.findall(r"os\.environ\.get\(\s*['\"]([A-Z0-9_]+)['\"]", script)
    )
    env_names |= set(
        re.findall(r"os\.getenv\(\s*['\"]([A-Z0-9_]+)['\"]", script)
    )
    fake_env = {name: _fake_env_value(name) for name in env_names}
    fake_env.setdefault("API_KEY", "test-value")

    def _urlopen(*args: object, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(payload)

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": "generated_api_script.py",
    }
    original_loads = json.loads

    def _smart_loads(*args: Any, **kwargs: Any) -> Any:
        return _wrap_mock(original_loads(*args, **kwargs))

    original_load = json.load

    def _smart_load(*args: Any, **kwargs: Any) -> Any:
        return _wrap_mock(original_load(*args, **kwargs))

    try:
        with mock.patch("sys.argv", ["generated_api_script.py"]):
            with mock.patch("urllib.request.urlopen", side_effect=_urlopen):
                with mock.patch("json.loads", side_effect=_smart_loads):
                    with mock.patch("json.load", side_effect=_smart_load):
                        with mock.patch.dict(os.environ, fake_env, clear=False):
                            exec(
                                compile(script, "generated_api_script.py", "exec"),
                                namespace,
                            )
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


class UniversalMockValue(dict):
    """A permissive stand-in for ANY missing API field during dry-runs.

    Generated code frequently assumes a key exists (``data['cohorts']``,
    ``data['assets']``, ``data['id']``). A plain dict raises ``KeyError`` and
    the whole workflow is rejected. ``UniversalMockValue`` behaves like a
    dict, a list, a string and a number at the same time, so the dry-run can
    continue and the validator only fails on real contract violations.
    """

    def __getitem__(self, key: Any) -> "UniversalMockValue":
        return UniversalMockValue()

    def get(self, key: Any, default: Any = None) -> Any:
        return default if default is not None else UniversalMockValue()

    def __iter__(self):
        return iter([UniversalMockValue()])

    def __len__(self) -> int:
        return 1

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
        return "sample"

    def __repr__(self) -> str:
        return "UniversalMockValue()"

    def __float__(self) -> float:
        return 0.5

    def __int__(self) -> int:
        return 1

    def __index__(self) -> int:
        return 0

    def __hash__(self) -> int:
        return 0

    def __truediv__(self, other: Any) -> float:
        return 0.5

    def __rtruediv__(self, other: Any) -> float:
        return 0.5

    def __add__(self, other: Any) -> float:
        return 0.5

    def __radd__(self, other: Any) -> float:
        return 0.5

    def __sub__(self, other: Any) -> float:
        return 0.5

    def __rsub__(self, other: Any) -> float:
        return 0.5

    def __mul__(self, other: Any) -> float:
        return 0.5

    def __rmul__(self, other: Any) -> float:
        return 0.5

    def __lt__(self, other: Any) -> bool:
        return False

    def __le__(self, other: Any) -> bool:
        return True

    def __gt__(self, other: Any) -> bool:
        return False

    def __ge__(self, other: Any) -> bool:
        return True


class UniversalMockList(list):
    """A list that never raises ``IndexError`` during dry-runs."""

    def __getitem__(self, index: Any) -> Any:
        try:
            return super().__getitem__(index)
        except (IndexError, TypeError):
            return UniversalMockValue()


class UniversalMockDict(dict):
    """A dict that returns a valid dummy value for ANY missing key.

    This is the fehlertolerante replacement for ``SmartMockDict``. It is used
    for every mocked ``urllib.request.urlopen`` response so that generated
    code such as ``data['id']``, ``data['cohorts']`` or ``data['assets']``
    never raises ``KeyError`` in the dry-run.
    """

    _DEFAULT: dict[str, Any] = {
        "id": "1",
        "text": "sample",
        "value": 0.5,
        "name": "sample",
        "content": "0.8",
        "score": 0.8,
        "sentiment": 0.8,
        "count": 1,
        "valid": True,
        "status": "ok",
        "ok": True,
        "data": [],
        "items": [],
        "results": [],
        "records": [],
        "messages": [],
        "choices": [{"message": {"content": "0.8"}}],
    }

    def __getitem__(self, key: Any) -> Any:
        if key in self:
            return super().__getitem__(key)
        if key in self._DEFAULT:
            return _wrap_mock(self._DEFAULT[key])
        return UniversalMockValue()

    def get(self, key: Any, default: Any = None) -> Any:
        if key in self:
            return super().get(key, default)
        if key in self._DEFAULT:
            return _wrap_mock(self._DEFAULT[key])
        return default if default is not None else UniversalMockValue()

    def __hash__(self) -> int:
        return id(self)


def _wrap_mock(value: Any) -> Any:
    """Recursively wrap dicts/lists so missing keys/indices never raise."""
    if isinstance(value, dict):
        return UniversalMockDict(
            {key: _wrap_mock(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return UniversalMockList([_wrap_mock(item) for item in value])
    return value


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
        "openai.com": {
            "choices": [{"message": {"content": "0.8"}}],
            "content": "0.8",
            "text": "sample",
            "valid": True,
            "score": 0.8,
        },
        "anthropic.com": {"content": "Sample content"},
        "supabase": [],
        "slack.com": "ok",
    }


def execute_workflow_dry_run(
    steps_code: list[str],
    mock_responses: dict[str, Any] | None = None,
    step_mocks: list[dict[str, Any] | None] | None = None,
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
                "records": [{"id": "1", "name": "sample"}],
                "messages": [],
                "choices": [{"message": {"content": "0.8"}}],
                "topics": [],
                "drafts": [],
                "approved_drafts": [],
                "mentions": ["sample"],
                "lead": {"id": "1", "email": "test@example.com", "valid": True},
                "email": "test@example.com",
                "keyword": "sample",
                "id": "1",
                "text": "sample",
                "content": "0.8",
                "value": 0.5,
                "score": 0.8,
                "sentiment": 0.8,
                "z_score": 0.5,
                "count": 1,
                "valid": True,
                "is_valid": True,
                "status": "ok",
                "ok": True,
            }
        ).encode("utf-8")

    def _urlopen(request: Any, *args: object, **kwargs: object) -> _Resp:
        if "headers" in kwargs:
            raise TypeError(
                "urlopen() got an unexpected keyword argument 'headers' – "
                "use urllib.request.Request(url, headers=...)"
            )
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
    fake_env = {name: _fake_env_value(name) for name in env_names}
    fake_env.setdefault("API_KEY", "test-value")

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": "workflow.py",
    }

    _real_open = builtins.open

    def _safe_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        """Return deterministic mock content for missing input files.

        Generated workflows often read local inputs such as
        ``content_briefs.json`` that are not part of the dry-run sandbox. The
        kit builder creates those files for ``workflow.py --dry-run``; the
        validator must do the same so a missing input is not reported as a
        runtime warning.
        """
        if "r" in mode and "b" not in mode:
            try:
                missing = not os.path.exists(file)
            except (TypeError, ValueError):
                missing = False
            if missing:
                name = str(file)
                if name.endswith(".json"):
                    return io.StringIO(
                        json.dumps(
                            [
                                {
                                    "id": "1",
                                    "title": "Sample",
                                    "content": "Sample content",
                                    "text": "sample text",
                                    "value": 0.5,
                                    "name": "sample",
                                    "prompt": "sample prompt",
                                    "keyword": "sample",
                                    "query": "sample",
                                    "url": "https://example.com",
                                    "status": "ok",
                                }
                            ]
                        )
                    )
                if name.endswith(".csv"):
                    return io.StringIO("id,name,value\n1,sample,0.5\n")
                return io.StringIO("sample\n")
        return _real_open(file, mode, *args, **kwargs)

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
        ), contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch("sys.argv", ["workflow.py"]))
            original_loads = json.loads

            def _smart_loads(*args: Any, **kwargs: Any) -> Any:
                return _wrap_mock(original_loads(*args, **kwargs))

            stack.enter_context(mock.patch("json.loads", side_effect=_smart_loads))
            original_load = json.load

            def _smart_load(*args: Any, **kwargs: Any) -> Any:
                return _wrap_mock(original_load(*args, **kwargs))

            stack.enter_context(mock.patch("json.load", side_effect=_smart_load))
            stack.enter_context(
                mock.patch("builtins.open", side_effect=_safe_open)
            )
            stack.enter_context(
                mock.patch("urllib.request.urlopen", side_effect=_urlopen)
            )
            stack.enter_context(
                mock.patch("http.client.HTTPSConnection", _FakeHTTPSConnection)
            )
            stack.enter_context(mock.patch("time.sleep", return_value=None))
            stack.enter_context(mock.patch("builtins.input", return_value="yes"))
            # Generated snippets must never execute real shell commands during
            # the dry-run (e.g. npm/astro/git). Mock them deterministically.
            stack.enter_context(
                mock.patch(
                    "subprocess.run",
                    return_value=mock.Mock(returncode=0, stdout=b"", stderr=b""),
                )
            )
            stack.enter_context(
                mock.patch("subprocess.check_output", return_value=b"")
            )
            stack.enter_context(mock.patch("os.system", return_value=0))
            stack.enter_context(
                mock.patch.dict(os.environ, fake_env, clear=False)
            )
            exec(compile(code, "workflow.py", "exec"), namespace)
    except _DryRunTimeout:
        result.add(
            "Workflow dry-run timed out after 10s – remove infinite loops or "
            "blocking waits from the step code"
        )
    except SystemExit:
        pass
    except (TypeError, KeyError, ValueError, NameError, ArithmeticError) as error:
        # Hard gate: these are real runtime contract violations (e.g.
        # statistics.mean() on strings). The exact traceback is returned to the
        # self-healing loop so the LLM can repair the responsible step.
        hint = ""
        if isinstance(error, ZeroDivisionError):
            hint = (
                " Hint: guard against zero variance before dividing, "
                "e.g. `if len(sentiments) < 2 or stdev == 0: return`."
            )
        result.add(
            "Workflow dry-run failed: "
            f"{type(error).__name__}: {error}\n"
            f"{traceback.format_exc()}{hint}"
        )
    except AttributeError as error:
        # Attribute mismatches are often caused by an intentionally different
        # mock payload; keep them actionable but non-blocking.
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


def validate_english(payload: Any, context: str) -> list[str]:
    """Reject German characters/words in generated English content."""
    serialized = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, ensure_ascii=False)
    )
    errors: list[str] = []
    if re.search(r"[äöüÄÖÜß]", serialized):
        errors.append(
            f"{context}: German characters found – all generated content must "
            "be 100 % English"
        )
    lowered = serialized.lower()
    found = sorted(
        {
            word
            for word in config.GERMAN_WORDS
            if re.search(rf"\b{re.escape(word)}\b", lowered)
        }
    )
    if found:
        errors.append(
            f"{context}: German words found ({', '.join(found[:8])}) – all "
            "generated content must be 100 % English"
        )
    return errors


def validate_api_script(script: str) -> ValidationResult:
    result = check_python_ast(script, "API script")

    if "if __name__" not in script:
        result.add('API script: missing executable `if __name__ == "__main__"` block')
    if "os.environ" not in script:
        result.add("API script: configuration must use os.environ")
    if "--dry-run" not in script:
        result.add(
            "API script: missing mandatory `--dry-run` argparse mode "
            "(the sandbox executes `python3 api_client.py --dry-run`)"
        )
    if "argparse" not in script:
        result.add("API script: --dry-run mode must use argparse")
    if "def request_json(" not in script:
        result.add(
            "API script: missing the mandatory top-level `request_json(...)` helper"
        )

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
    for message in validate_english(script, "API script"):
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


_NON_API_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "python standard library",
        "standard library",
        "python",
        "bash",
        "terminal",
        "none",
        "null",
        "",
    }
)


def _normalise_tool_name(raw: str, api_titles: list[str]) -> str | None:
    """Map a free-form tool name to a curated API title (flexible match)."""
    value = str(raw or "").strip()
    if not value:
        return None
    lowered = value.lower()
    if lowered in _NON_API_TOOL_NAMES:
        return None
    normalised = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
    for title in api_titles:
        title_lower = title.lower()
        title_norm = re.sub(r"[^a-z0-9]+", " ", title_lower).strip()
        if (
            lowered == title_lower
            or normalised == title_norm
            or normalised in title_norm
            or title_norm in normalised
        ):
            return title
    return None


def enrich_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    """Enrich a workflow with missing tools, resources and prerequisites.

    The LLM sometimes omits a curated API from the tool list, the resources or
    the prerequisites. Instead of rejecting the whole workflow, we inject the
    missing entries from the curated API catalogue. This keeps the hard
    grounding checks intact while making the pipeline more robust.
    """
    details = workflow.get("details") or {}
    api_slugs = [
        str(slug).strip()
        for slug in (details.get("api_slugs") or [])
        if str(slug).strip()
    ]
    if not api_slugs:
        return workflow
    catalog = _catalog()
    api_titles: list[str] = []
    for slug in api_slugs:
        api = catalog["apis"].get(slug)
        if api and str(api.get("title") or "").strip():
            api_titles.append(str(api.get("title")).strip())

    tools = [
        str(tool).strip()
        for tool in (details.get("tools") or [])
        if str(tool).strip()
    ]
    # Normalise free-form tool names to the curated API titles. Unknown tools
    # are dropped because only curated APIs are allowed.
    normalised_tools: list[str] = []
    for tool in tools:
        matched = _normalise_tool_name(tool, api_titles)
        if matched:
            if matched not in normalised_tools:
                normalised_tools.append(matched)
        elif tool.lower() in _NON_API_TOOL_NAMES:
            if tool not in normalised_tools:
                normalised_tools.append(tool)
    tools = normalised_tools

    resources = list(details.get("resources") or [])
    prerequisites = list(details.get("prerequisites") or [])

    for slug in api_slugs:
        api = catalog["apis"].get(slug)
        if not api:
            continue
        title = str(api.get("title") or "").strip()
        if not title:
            continue
        if title not in tools:
            tools.append(title)
        if not any(
            str(entry.get("label") or "").strip().lower() == title.lower()
            for entry in resources
        ):
            details_api = api.get("details") or {}
            docs_url = str(
                details_api.get("docsUrl") or details_api.get("website") or ""
            )
            if docs_url:
                resources.append({"label": title, "url": docs_url})
        if not any(title.lower() in str(item).lower() for item in prerequisites):
            insert_at = len(prerequisites)
            for position, item in enumerate(prerequisites):
                if str(item).strip() == config.FINAL_PREREQUISITE:
                    insert_at = position
                    break
            prerequisites.insert(insert_at, f"A {title} account and API key")

    # Normalise the tools declared on each step so a step never references a
    # tool that is missing from the workflow tool list. Unknown tools are
    # dropped because only curated APIs are allowed.
    for step in details.get("steps") or []:
        step_tools: list[str] = []
        for raw in step.get("tools") or []:
            value = str(raw).strip()
            if not value:
                continue
            matched = _normalise_tool_name(value, api_titles)
            if matched:
                if matched not in step_tools:
                    step_tools.append(matched)
            elif value.lower() in _NON_API_TOOL_NAMES:
                if value not in step_tools:
                    step_tools.append(value)
        step["tools"] = step_tools

    details["tools"] = tools
    details["resources"] = resources
    details["prerequisites"] = prerequisites
    details["before_you_start"] = prerequisites
    workflow["details"] = details
    return workflow


def validate_workflow(workflow: dict[str, Any]) -> ValidationResult:
    workflow = enrich_workflow(workflow)
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

    # --- Curated grounding ------------------------------------------------- #
    catalog = _catalog()
    api_slugs = [
        str(slug).strip()
        for slug in (details.get("api_slugs") or [])
        if str(slug).strip()
    ]
    alternative_slugs = [
        str(slug).strip()
        for slug in (details.get("alternative_slugs") or [])
        if str(slug).strip()
    ]
    for slug in api_slugs:
        if slug not in catalog["apis"]:
            result.add(f"Workflow: unknown curated API slug '{slug}'")
    for slug in alternative_slugs:
        if slug not in catalog["alternatives"]:
            result.add(f"Workflow: unknown curated alternative slug '{slug}'")
    grounded_apis = [
        catalog["apis"][slug] for slug in api_slugs if slug in catalog["apis"]
    ]
    grounded_titles = {str(api.get("title")) for api in grounded_apis}
    if api_slugs:
        for tool in tools:
            if tool.lower() in _NON_API_TOOL_NAMES:
                continue
            if tool not in grounded_titles:
                result.add(
                    f"Workflow: tool '{tool}' is not one of the curated APIs "
                    f"({', '.join(sorted(grounded_titles))})"
                )
        for api in grounded_apis:
            if str(api.get("title")) not in tools:
                result.add(
                    f"Workflow: curated API '{api.get('title')}' is missing "
                    "from the tool list"
                )

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
            if re.search(r"urlopen\([^)]*headers\s*=", code):
                result.add(
                    f"{context}: urlopen() does not accept headers=; build "
                    "urllib.request.Request(url, headers=...) instead"
                )
            if (
                "api.openai.com" in code
                and "float(" in code
                and "Respond ONLY with a float" not in code
            ):
                result.add(
                    f"{context}: OpenAI numeric output requires the literal "
                    "instruction 'Respond ONLY with a float between -1.0 and 1.0'"
                )
            if re.search(r"['\"]gpt-4['\"]", code):
                result.add(
                    f"{context}: outdated model 'gpt-4' – use 'gpt-4o-mini' "
                    "or 'gpt-4o'"
                )
            if "tweets/search" in code and (
                "urlencode" not in code or "query" not in code
            ):
                result.add(
                    f"{context}: X/Twitter search requires real query parameters "
                    "via urllib.parse.urlencode({'query': ...})"
                )
            alert_calls = re.findall(r"send_alert\((.*?)\)", code)
            if alert_calls and not any(
                re.search(r"text|mention|record", call, re.IGNORECASE)
                for call in alert_calls
            ):
                result.add(
                    f"{context}: send_alert must receive the mention text, "
                    "not only the sentiment float"
                )
            if "supabase" in code.lower() and "SUPABASE_URL" not in code:
                result.add(
                    f"{context}: Supabase URL must come from "
                    "os.environ.get('SUPABASE_URL') – never hardcode the instance URL"
                )
            if re.search(r"your[-_]table|your[-_]supabase", code, re.IGNORECASE):
                result.add(
                    f"{context}: replace Supabase placeholders "
                    "(your_table / your-supabase-instance) with concrete values"
                )

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
            step_assigned = _meaningful(_assigned_names(code))
            if index > 1:
                overwritten = (
                    step_assigned & previous_assigned
                ) - _self_reassignments(code)
                if overwritten:
                    # Warning only: the runtime dry-run below is the real gate
                    # for broken data flow. Reassigning a name can be a valid
                    # transformation and must not block the whole workflow.
                    result.warn(
                        f"{context}: reassigns variable(s) from previous steps "
                        f"({', '.join(sorted(overwritten))}) – verify the data flow"
                    )
            previous_assigned |= step_assigned
            combined_code.append(code)

            # A snippet that defines functions must call one at top level,
            # otherwise the step silently never executes.
            try:
                step_tree = ast.parse(code, feature_version=(3, 10))
            except SyntaxError:
                step_tree = None
            if step_tree is not None:
                defined = {
                    node.name
                    for node in step_tree.body
                    if isinstance(node, ast.FunctionDef)
                }
                called: set[str] = set()
                for node in step_tree.body:
                    value = None
                    if isinstance(node, ast.Assign):
                        value = node.value
                    elif isinstance(node, ast.Expr):
                        value = node.value
                    elif isinstance(node, ast.If):
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call) and isinstance(
                                child.func, ast.Name
                            ):
                                called.add(child.func.id)
                    if isinstance(value, ast.Call) and isinstance(
                        value.func, ast.Name
                    ):
                        called.add(value.func.id)
                if defined and not (defined & called):
                    result.add(
                        f"{context}: defines function(s) "
                        f"{', '.join(sorted(defined))} but never calls one at "
                        "top level – the step would not execute"
                    )

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

        if not (step.get("links") or []):
            result.add(
                f"{context}: links is empty – add the official documentation URL "
                "(use the Python stdlib docs for a pure Python step)"
            )

        # Link labels must be real documentation names, not prompt leaks.
        for link in step.get("links") or []:
            label = str(link.get("label") or "")
            if "official docs for the api used in this step" in label.lower():
                result.add(
                    f"{context}: link label is a prompt leak – use the real "
                    "documentation name (e.g. 'X API Search Docs')"
                )

        # Context-specific links: a single-tool step must link to that tool's
        # official documentation, not to an unrelated service.
        step_tools = [
            str(tool).strip()
            for tool in (step.get("tools") or [])
            if str(tool).strip()
        ]
        step_link_urls = [
            str(link.get("url") or "") for link in (step.get("links") or [])
        ]
        if len(step_tools) == 1:
            tool_name = step_tools[0]
            api = catalog["apis_by_title"].get(tool_name)
            if api is not None:
                allowed_domains = _api_link_domains(api)
                link_domains = {
                    _registrable_domain(
                        urllib.parse.urlparse(url).hostname or ""
                    )
                    for url in step_link_urls
                }
                if allowed_domains and not (allowed_domains & link_domains):
                    result.add(
                        f"{context}: link does not match the curated API "
                        f"'{tool_name}' (expected docs domain: "
                        f"{', '.join(sorted(allowed_domains))})"
                    )
            else:
                markers = config.TOOL_LINK_MARKERS.get(tool_name)
                if markers and not any(
                    any(marker.lower() in url.lower() for marker in markers)
                    for url in step_link_urls
                ):
                    result.add(
                        f"{context}: link does not match the tool '{tool_name}' "
                        f"(expected one of: {', '.join(markers)})"
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
            # catches type errors that ast.parse cannot see. It is skipped only
            # for the fast structural audit; the real pipeline always runs it.
            if os.environ.get("FLOWMATRIX_SKIP_DRYRUN") != "1":
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
    api_tool_count = len(
        [tool for tool in tools if tool.lower() not in _NON_API_TOOL_NAMES]
    )
    if len(prerequisites) < api_tool_count:
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

    full_code = "\n".join(
        str(step.get("code_snippet") or "") for step in steps
    ).lower()
    full_text = "\n".join(_step_text(step) for step in steps).lower()
    for tool in tools:
        if tool.lower() in _NON_API_TOOL_NAMES:
            continue
        api = catalog["apis_by_title"].get(tool)
        markers = (
            _api_markers(api)
            if api is not None
            else config.TOOL_CODE_MARKERS.get(tool) or (tool.lower(),)
        )
        if not any(marker.lower() in full_text for marker in markers):
            # Downgraded to a warning: the curated API is still injected into
            # the tool list/resources by enrich_workflow, and the runtime
            # dry-run is the real gate for broken data flow.
            result.warn(
                f"Workflow: tool '{tool}' is listed but not used in any step "
                f"code or text (expected one of: {', '.join(markers)})"
            )
        if tool.lower() not in resource_labels:
            result.add(
                f"Workflow: tool '{tool}' has no entry in resources"
            )
        # Every tool needs its OWN dedicated bullet in BEFORE YOU START, not
        # just an incidental mention inside another prerequisite.
        if not any(tool.lower() in str(item).lower() for item in prerequisites):
            result.add(
                f"Workflow: tool '{tool}' has no dedicated entry in "
                "BEFORE YOU START (prerequisites)"
            )

    # Every curated API must expose its official docs URL in resources.
    for api in grounded_apis:
        details_api = api.get("details") or {}
        docs_url = str(
            details_api.get("docsUrl") or details_api.get("website") or ""
        )
        host = urllib.parse.urlparse(docs_url).hostname or ""
        if host and _registrable_domain(host) not in resource_domains:
            result.add(
                f"Workflow: curated API '{api.get('title')}' docs URL is "
                "missing from resources"
            )

    # Domains that belong to the curated APIs (endpoint or docs). They are
    # legitimate code targets even when only the docs URL is listed in
    # resources, so they are exempt from the reverse resource check.
    allowed_domains: set[str] = set()
    for api in grounded_apis:
        details_api = api.get("details") or {}
        for raw in (
            details_api.get("endpoint"),
            details_api.get("docsUrl"),
            details_api.get("website"),
        ):
            value = str(raw or "")
            if not value or "<" in value or "{" in value:
                continue
            host = urllib.parse.urlparse(value).hostname or ""
            if host:
                allowed_domains.add(_registrable_domain(host))

    # Reverse check: API hosts used in code must be represented in resources,
    # but documentation links, curated API endpoints and already-referenced
    # hosts are exempt.
    reference_hosts: set[str] = set()
    for step in steps:
        for link in step.get("links") or []:
            host = (
                urllib.parse.urlparse(str(link.get("url") or "")).hostname
                or ""
            )
            if host:
                reference_hosts.add(_registrable_domain(host))
    reference_hosts |= resource_domains
    reference_hosts |= allowed_domains
    code_hosts: set[str] = set()
    for step in steps:
        for url in extract_urls(str(step.get("code_snippet") or "")):
            host = urllib.parse.urlparse(url).hostname or ""
            if host and not _is_placeholder_host(host):
                code_hosts.add(_registrable_domain(host))
    for domain in sorted(code_hosts):
        if domain in {"flowmatrix.dev"} or _domain_matches(domain, reference_hosts):
            continue
        if not _domain_matches(domain, resource_domains):
            if _dns_resolves(domain):
                result.warn(
                    f"Workflow: API host '{domain}' resolves via DNS but is "
                    "missing from resources"
                )
                continue
            result.add(
                f"Workflow: API host '{domain}' is used in code but missing from resources"
            )

    # Hard grounding: when curated API slugs are present, every host used in
    # code must belong to one of those APIs (endpoint or docs domain).
    if grounded_apis:
        for domain in sorted(code_hosts):
            if domain in {"flowmatrix.dev"} or _domain_matches(domain, allowed_domains):
                continue
            if _dns_resolves(domain):
                # Official endpoint domains (e.g. api.together.xyz or
                # sheets.googleapis.com) may differ from the docs domain in
                # resources. A DNS-resolvable host is accepted as a real API
                # endpoint instead of aborting the workflow.
                result.warn(
                    f"Workflow: API host '{domain}' resolves via DNS but is not "
                    "listed in the curated API endpoints"
                )
                continue
            result.add(
                f"Workflow: API host '{domain}' is not part of the curated "
                "APIs – ungrounded API call"
            )

    for message in scan_blacklist(workflow):
        result.add(message)

    for message in validate_english(workflow, "Workflow"):
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

    details = alternative.get("details") or {}
    for key in ("original", "bestFor", "pricing"):
        if not str(details.get(key) or "").strip():
            result.add(f"Alternative: details.{key} is missing")
    features = details.get("features") or []
    if len(features) < 3:
        result.add(
            f"Alternative: details.features needs at least 3 entries, "
            f"found {len(features)}"
        )

    items = details.get("alternatives") or []
    if len(items) < 3:
        result.add("Alternative: needs at least 3 alternatives")
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            result.add(
                f"Alternative: item {index} must be an object with name, "
                "description, pros, cons, bestFor and url"
            )
            continue
        if not isinstance(item, dict):
            result.add(f"Alternative: item {index} is not an object")
            continue
        for key in ("name", "description", "bestFor"):
            if not str(item.get(key) or "").strip():
                result.add(f"Alternative: item {index} is missing {key}")
        pros = item.get("pros") or []
        cons = item.get("cons") or []
        if len(pros) < 2:
            result.add(f"Alternative: item {index} needs at least 2 pros")
        if len(cons) < 2:
            result.add(f"Alternative: item {index} needs at least 2 cons")
        url = str(item.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            result.add(f"Alternative: item {index} needs a full http(s) URL")
        elif "ref=flowmatrix" not in url:
            result.add(
                f"Alternative: item {index} URL must carry the affiliate "
                "parameter `?ref=flowmatrix`"
            )

    for message in scan_blacklist(alternative):
        result.add(message)
    for message in validate_english(alternative, "Alternative"):
        result.add(message)
    for message in validate_domains(alternative, "Alternative"):
        result.add(message)
    return result
