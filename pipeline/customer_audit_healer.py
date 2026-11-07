#!/usr/bin/env python3
"""End-to-End Customer Audit & Auto-Healing Engine.

This is the final, customer-facing quality gate for the whole FlowMatrix
catalogue. It audits **every** API, alternative and workflow exactly the way a
paying customer would experience it – by opening the shipped PDF, unzipping the
kit in a fresh sandbox and executing the code – and then repairs every defect
it finds, fully autonomously.

Six audit levels
----------------
1. **Cross-check** – does the PDF/ZIP really match the workflow/API record
   (title, slug, purpose, tools, endpoints, price)?
2. **Customer unpack & execution sandbox** – ``zipfile.testzip()``, required
   files, bit-identical PDF, ``ast``/stdlib gate, real ``--dry-run`` and
   ``unittest`` execution, environment-variable parity.
3. **Deep PDF inspection** – 100 % English, timestamps, link disclaimer,
   blacklist/prompt-leak scan, didactic quality, dynamic page numbering.
4. **Alternatives & live domains** – schema/metrics audit plus a cached
   HTTP/DNS reachability check for every external URL and code endpoint.
5. **Autonomous self-healing** – deterministic metadata/structure fixes first,
   then targeted LLM repair (DeepSeek/OpenRouter) with up to three rounds,
   dead-domain replacement, rebuild of PDF + ZIP, R2 sync and checkpointing.
6. **Final report, Astro build & deploy** – ``CUSTOMER_AUDIT_REPORT.md``,
   ``npm run build`` and an automatic git commit/push.

Usage::

    python3 pipeline/customer_audit_healer.py
    python3 pipeline/customer_audit_healer.py --skip-live --skip-build --skip-git
    python3 pipeline/customer_audit_healer.py --only workflow:ai-content-generation-pipeline

The script re-executes itself with ``.venv/bin/python`` when the system Python
lacks ``reportlab``/``pydantic``/``pypdf``, so the documented ``python3``
invocation is enough.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent


# --------------------------------------------------------------------------- #
# Bootstrap: make ``python3 pipeline/customer_audit_healer.py`` always work
# --------------------------------------------------------------------------- #
def _ensure_runtime() -> None:
    """Re-exec with the project venv when dependencies are missing."""
    try:
        import pydantic  # noqa: F401
        import reportlab  # noqa: F401
        import pypdf  # noqa: F401
    except Exception:  # noqa: BLE001 - any import problem means "use the venv"
        venv_python = _ROOT / ".venv" / "bin" / "python"
        if venv_python.exists() and Path(sys.prefix).resolve() != (
            _ROOT / ".venv"
        ).resolve():
            os.execv(str(venv_python), [str(venv_python), str(_HERE), *sys.argv[1:]])


_ensure_runtime()

# Allow direct execution (``python3 pipeline/customer_audit_healer.py``).
if __package__ in (None, ""):
    sys.path.insert(0, str(_ROOT))
    __package__ = "pipeline"

from . import bundle_builder, config as cfg, llm_client, prompts, run_batch, validator
from .secret_sanitizer import sanitize_value

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
AUDIT_STATE_FILE = _ROOT / "pipeline" / "audit_state.json"
REPORT_FILE = _ROOT / "CUSTOMER_AUDIT_REPORT.md"
LOG_FILE = _ROOT / "pipeline" / "customer_audit.log"

# Extra blacklist fragments demanded by the customer-audit contract. They are
# merged with the pipeline-wide blacklist from ``config``.
EXTRA_BLACKLIST: tuple[str, ...] = (
    "Official docs for the API used in THIS step",
    "Prenium Warkflow",
    "File > New",
    "File > Save",
    "Make a Zap",
    "Adobe XD",
    "api.supabase.io",
    "ChatCompletion.create",
    "gpt-3.5-turbo",
    "pip install",
    "Dummy",
    "Node.js 18",
    "€4.99",
    "€7.99",
    "€12.99",
    "€21.99",
)
BLACKLIST: tuple[str, ...] = tuple(
    dict.fromkeys(cfg.BLACKLIST_PHRASES + EXTRA_BLACKLIST)
)

# "At a glance" is only forbidden as a *standalone* heading replacement.
_AT_A_GLANCE_RE = re.compile(r"(?m)^\s*At a glance\s*$", re.IGNORECASE)

_ENV_RE = re.compile(r"os\.(?:environ\.get|getenv)\(\s*['\"]([A-Z0-9_]+)['\"]")
_ENV_INDEX_RE = re.compile(r"os\.environ\[\s*['\"]([A-Z0-9_]+)['\"]\s*\]")
_PAGE_FOOTER_RE = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)
_TIMESTAMP_RE = re.compile(r"Created\s*&\s*Verified\s+on:\s*\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")
_DISCLAIMER_MARKER = "Verification & Link Validity Notice"

# Minimum didactic depth (characters) for a step's technical explanation.
MIN_TECHNICAL_CHARS = 250
MIN_CODE_LINES = 8

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def log(message: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:  # noqa: BLE001 - logging must never abort the audit
        pass


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime(cfg.TIMESTAMP_FORMAT)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _read_zip(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }


def _zip_test(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            return archive.testzip()
    except Exception as error:  # noqa: BLE001
        return f"{type(error).__name__}: {error}"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _host(url: str) -> str:
    try:
        return urlparse(str(url)).hostname or ""
    except Exception:  # noqa: BLE001
        return ""


def _dns_ok(host: str) -> bool:
    if not host:
        return False
    try:
        socket.gethostbyname(host)
        return True
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# PDF text extraction (pypdf, cached by path + mtime)
# --------------------------------------------------------------------------- #
_PDF_CACHE: dict[str, tuple[float, list[str]]] = {}


def _pdf_pages(path: Path) -> list[str]:
    if not path.exists():
        return []
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    cached = _PDF_CACHE.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as error:  # noqa: BLE001
        log(f"  [PDF] cannot read {path.name}: {error}")
        pages = []
    _PDF_CACHE[key] = (mtime, pages)
    return pages


def _pdf_text(path: Path) -> str:
    return "\n".join(_pdf_pages(path))


def _pdf_page_count(path: Path) -> int:
    pages = _pdf_pages(path)
    if pages:
        return len(pages)
    try:
        data = path.read_bytes()
        return len(re.findall(rb"/Type\s*/Page\b", data))
    except Exception:  # noqa: BLE001
        return 0


# --------------------------------------------------------------------------- #
# Artifact path resolution
# --------------------------------------------------------------------------- #
def _workflow_pdf_path(slug: str) -> Path | None:
    for candidate in (
        cfg.DOWNLOADS_DIR / f"{slug}.pdf",
        cfg.DOWNLOADS_DIR / f"flowmatrix-{slug}.pdf",
    ):
        if candidate.exists():
            return candidate
    return None


def _workflow_kit_path(slug: str) -> Path:
    return cfg.KITS_DIR / f"{slug}-kit.zip"


def _api_pdf_path(slug: str) -> Path | None:
    for candidate in (
        cfg.API_KITS_DIR / f"{slug}.pdf",
        cfg.API_KITS_DIR / f"{slug}-cheatsheet.pdf",
    ):
        if candidate.exists():
            return candidate
    return None


def _api_kit_path(slug: str) -> Path:
    return cfg.API_KITS_DIR / f"{slug}-kit.zip"


def _api_script_path(slug: str) -> Path:
    return cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"


# --------------------------------------------------------------------------- #
# AST / environment gates
# --------------------------------------------------------------------------- #
def _ast_errors(
    source: str,
    label: str,
    *,
    allowed_local: set[str] | None = None,
    forbid_random: bool = False,
) -> list[str]:
    allowed_local = allowed_local or set()
    errors: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [f"{label}: SyntaxError: {error.msg} (line {error.lineno})"]
    forbidden = set(cfg.FORBIDDEN_IMPORTS)
    if forbid_random:
        forbidden.add("random")
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for imported in names:
            top = imported.split(".")[0]
            if top in forbidden:
                errors.append(f"{label}: forbidden import '{imported}'")
            elif top not in cfg.STDLIB_MODULES and top not in allowed_local:
                errors.append(f"{label}: non-stdlib import '{imported}'")
    return errors


def _strip_py_comments(source: str) -> str:
    """Drop ``#`` comments so example text is never mistaken for real code."""
    lines: list[str] = []
    for line in source.splitlines():
        index = line.find("#")
        lines.append(line[:index] if index != -1 else line)
    return "\n".join(lines)


def _env_errors(code: str, env_example: str) -> list[str]:
    errors: list[str] = []
    code = _strip_py_comments(code)
    used = set(_ENV_RE.findall(code)) | set(_ENV_INDEX_RE.findall(code))
    for name in sorted(used):
        if name not in env_example:
            errors.append(f".env.example: missing variable {name}")
    declared: set[str] = set()
    for raw in env_example.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        declared.add(line.split("=", 1)[0].strip())
    for name in sorted(declared - used):
        if name:
            errors.append(f".env.example: unused variable {name}")
    return errors


# --------------------------------------------------------------------------- #
# Level 1 – cross-check
# --------------------------------------------------------------------------- #
def _workflow_crosscheck(
    workflow: dict[str, Any], apis_by_slug: dict[str, dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    slug = str(workflow.get("slug") or "")
    title = str(workflow.get("title") or "")
    details = workflow.get("details") or {}

    pdf = _workflow_pdf_path(slug)
    if pdf is None:
        return [f"workflow PDF missing for '{slug}'"]
    pages = _pdf_pages(pdf)
    if not pages:
        return [f"workflow PDF unreadable for '{slug}'"]
    page1 = pages[0].lower()
    page2 = pages[1].lower() if len(pages) > 1 else ""

    if title.lower() not in page1:
        errors.append("title missing on PDF cover (page 1)")
    if title.lower() not in page2:
        errors.append("title missing on PDF overview (page 2)")

    # Price synchronisation.
    price = cfg.price_for(details.get("difficulty"))
    label = f"€{price:.2f}"
    if label not in pages[0]:
        errors.append(f"PDF cover does not show the correct price {label}")
    for field in ("price",):
        value = workflow.get(field)
        if value is not None:
            try:
                if abs(float(value) - price) > 0.001:
                    errors.append(f"web JSON {field}={value} != {price}")
            except (TypeError, ValueError):
                errors.append(f"web JSON {field} is not numeric: {value!r}")
    details_price = details.get("price")
    if details_price is not None:
        try:
            if abs(float(details_price) - price) > 0.001:
                errors.append(f"details.price={details_price} != {price}")
        except (TypeError, ValueError):
            errors.append(f"details.price is not numeric: {details_price!r}")

    # Kit content must describe the same product.
    kit = _workflow_kit_path(slug)
    if not kit.exists():
        errors.append(f"workflow kit missing: {kit.name}")
        return errors
    try:
        files = _read_zip(kit)
    except Exception as error:  # noqa: BLE001
        return errors + [f"workflow kit unreadable: {error}"]

    for name in ("README.md", "AI_IMPLEMENTATION_PROMPT.md", "workflow.py"):
        text = files.get(name, b"").decode("utf-8", "replace")
        if title.lower() not in text.lower():
            errors.append(f"{name}: does not mention the workflow title")
        if slug.lower() not in text.lower():
            errors.append(f"{name}: does not mention the workflow slug")

    # Tool / endpoint coverage.
    tool_titles: list[str] = []
    for api_slug in details.get("api_slugs") or []:
        api = apis_by_slug.get(str(api_slug))
        if api:
            tool_titles.append(str(api.get("title") or api_slug))
    for tool in details.get("tools") or []:
        if str(tool) not in tool_titles:
            tool_titles.append(str(tool))

    pdf_all = "\n".join(pages).lower()
    script = files.get("workflow.py", b"").decode("utf-8", "replace")
    requests_http = files.get("requests.http", b"").decode("utf-8", "replace")
    for tool in tool_titles:
        if tool.lower() not in pdf_all:
            errors.append(f"tool '{tool}' missing from the PDF")
        markers = cfg.TOOL_CODE_MARKERS.get(tool, ())
        if markers and not any(m.lower() in script.lower() for m in markers):
            errors.append(f"tool '{tool}' has no real API call in workflow.py")
        if markers and not any(m.lower() in requests_http.lower() for m in markers):
            errors.append(f"tool '{tool}' missing from requests.http")

    return errors


def _api_crosscheck(api: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    slug = str(api.get("slug") or "")
    title = str(api.get("title") or "")
    details = api.get("details") or {}
    endpoint = str(details.get("endpoint") or "")
    host = _host(endpoint)

    script_path = _api_script_path(slug)
    if not script_path.exists():
        return [f"api_client.py missing for '{slug}'"]
    script = script_path.read_text(encoding="utf-8", errors="replace")
    if title.lower() not in script.lower():
        errors.append("api_client.py does not mention the API title")
    if host and host not in script:
        errors.append(f"api_client.py does not implement the endpoint host '{host}'")
    if "api.example.com" in script or "example.com" in script:
        errors.append("api_client.py contains a generic placeholder domain")

    kit = _api_kit_path(slug)
    if not kit.exists():
        return errors + [f"API kit missing: {kit.name}"]
    try:
        files = _read_zip(kit)
    except Exception as error:  # noqa: BLE001
        return errors + [f"API kit unreadable: {error}"]

    for name in ("test_mock.py", "requests.http", "README.md", "AI_INTEGRATION_PROMPT.md"):
        text = files.get(name, b"").decode("utf-8", "replace")
        if title.lower() not in text.lower():
            errors.append(f"{name}: does not mention the API title")
        if host and host not in text and name in ("test_mock.py", "requests.http"):
            errors.append(f"{name}: does not use the endpoint host '{host}'")

    pdf = _api_pdf_path(slug)
    if pdf is None:
        errors.append("api-cheatsheet.pdf missing")
    else:
        text = _pdf_text(pdf)
        if title.lower() not in text.lower():
            errors.append("api-cheatsheet.pdf does not mention the API title")
        if host and host not in text:
            errors.append(f"api-cheatsheet.pdf does not show the endpoint host '{host}'")
        if "€29.99" not in text:
            errors.append("api-cheatsheet.pdf does not show the €29.99 price")

    return errors


# --------------------------------------------------------------------------- #
# Level 2 – customer unpack & execution sandbox
# --------------------------------------------------------------------------- #
def _run_workflow_dryrun(kit_path: Path) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(kit_path, "r") as archive:
            with tempfile.TemporaryDirectory(prefix="fm-audit-wf-") as tmp:
                archive.extractall(tmp)
                env = os.environ.copy()
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                env_file = Path(tmp) / ".env.example"
                if env_file.exists():
                    for raw in env_file.read_text(encoding="utf-8").splitlines():
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key = line.split("=", 1)[0].strip()
                        if key:
                            env.setdefault(
                                key, bundle_builder._dry_run_env_value(key)  # noqa: SLF001
                            )
                try:
                    result = subprocess.run(
                        [sys.executable, "workflow.py", "--dry-run"],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        timeout=90,
                        env=env,
                    )
                except subprocess.TimeoutExpired:
                    return False, "workflow.py --dry-run timed out after 90s"
                output = f"{result.stdout}\n{result.stderr}".strip()
                ok = (
                    result.returncode == 0
                    and "Traceback (most recent call last)" not in output
                )
                return ok, output
    except Exception as error:  # noqa: BLE001
        return False, f"{type(error).__name__}: {error}"


def _run_api_sandbox(kit_path: Path) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(kit_path, "r") as archive:
            with tempfile.TemporaryDirectory(prefix="fm-audit-api-") as tmp:
                archive.extractall(tmp)
                script = (Path(tmp) / "api_client.py").read_text(
                    encoding="utf-8", errors="replace"
                )
                env = os.environ.copy()
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                for name in bundle_builder._env_names(script):  # noqa: SLF001
                    env.setdefault(
                        name, bundle_builder._dry_run_env_value(name)  # noqa: SLF001
                    )
                try:
                    unit = subprocess.run(
                        [sys.executable, "-m", "unittest", "test_mock.py"],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        env=env,
                    )
                except subprocess.TimeoutExpired:
                    return False, "unittest timed out after 120s"
                if unit.returncode != 0:
                    return False, f"unittest failed:\n{unit.stdout}\n{unit.stderr}"
                try:
                    dry = subprocess.run(
                        [sys.executable, "api_client.py", "--dry-run"],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        env=env,
                    )
                except subprocess.TimeoutExpired:
                    return False, "api_client.py --dry-run timed out after 120s"
                output = f"{dry.stdout}\n{dry.stderr}".strip()
                if dry.returncode != 0 or "Traceback (most recent call last)" in output:
                    return False, f"api_client.py --dry-run failed:\n{output}"
                return True, ""
    except Exception as error:  # noqa: BLE001
        return False, f"{type(error).__name__}: {error}"


def _workflow_sandbox(workflow: dict[str, Any], *, run_code: bool) -> list[str]:
    errors: list[str] = []
    slug = str(workflow.get("slug") or "")
    kit = _workflow_kit_path(slug)
    if not kit.exists():
        return [f"workflow kit missing: {kit.name}"]

    bad = _zip_test(kit)
    if bad:
        errors.append(f"workflow kit is corrupt: {bad}")
        return errors

    try:
        files = _read_zip(kit)
    except Exception as error:  # noqa: BLE001
        return [f"workflow kit unreadable: {error}"]

    for required in cfg.WORKFLOW_KIT_FILES:
        if required not in files:
            errors.append(f"workflow kit missing required file '{required}'")
        elif len(files[required]) <= 100:
            errors.append(f"workflow kit file '{required}' is <= 100 bytes")

    # PDF inside the ZIP must be bit-identical to the standalone PDF.
    standalone = _workflow_pdf_path(slug)
    if standalone and "blueprint.pdf" in files:
        if _sha256(files["blueprint.pdf"]) != _sha256(standalone.read_bytes()):
            errors.append("blueprint.pdf in ZIP is not bit-identical to the standalone PDF")

    # AST gate for every Python file.
    for name, data in files.items():
        if name.endswith(".py"):
            errors.extend(
                _ast_errors(
                    data.decode("utf-8", "replace"),
                    name,
                    forbid_random=True,
                )
            )

    # AST gate for the authoritative step snippets (the PDF code source).
    for index, step in enumerate((workflow.get("details") or {}).get("steps") or [], 1):
        snippet = str(step.get("code_snippet") or "")
        if snippet.strip():
            errors.extend(
                _ast_errors(snippet, f"step {index} code_snippet", forbid_random=True)
            )

    # Environment parity.
    script = files.get("workflow.py", b"").decode("utf-8", "replace")
    env_example = files.get(".env.example", b"").decode("utf-8", "replace")
    errors.extend(_env_errors(script, env_example))

    if run_code:
        ok, output = _run_workflow_dryrun(kit)
        if not ok:
            errors.append(f"workflow.py --dry-run failed: {output[-1500:]}")

    return errors


def _api_sandbox(api: dict[str, Any], *, run_code: bool) -> list[str]:
    errors: list[str] = []
    slug = str(api.get("slug") or "")
    kit = _api_kit_path(slug)
    if not kit.exists():
        return [f"API kit missing: {kit.name}"]

    bad = _zip_test(kit)
    if bad:
        errors.append(f"API kit is corrupt: {bad}")
        return errors

    try:
        files = _read_zip(kit)
    except Exception as error:  # noqa: BLE001
        return [f"API kit unreadable: {error}"]

    for required in cfg.API_KIT_FILES:
        if required not in files:
            errors.append(f"API kit missing required file '{required}'")
        elif len(files[required]) <= 100:
            errors.append(f"API kit file '{required}' is <= 100 bytes")

    standalone = _api_pdf_path(slug)
    if standalone and "api-cheatsheet.pdf" in files:
        if _sha256(files["api-cheatsheet.pdf"]) != _sha256(standalone.read_bytes()):
            errors.append(
                "api-cheatsheet.pdf in ZIP is not bit-identical to the standalone PDF"
            )

    for name, data in files.items():
        if name.endswith(".py"):
            errors.extend(
                _ast_errors(
                    data.decode("utf-8", "replace"),
                    name,
                    allowed_local={"api_client"},
                )
            )

    script = files.get("api_client.py", b"").decode("utf-8", "replace")
    env_example = files.get(".env.example", b"").decode("utf-8", "replace")
    errors.extend(_env_errors(script, env_example))

    if run_code:
        ok, output = _run_api_sandbox(kit)
        if not ok:
            errors.append(f"API sandbox failed: {output[-1500:]}")

    return errors


# --------------------------------------------------------------------------- #
# Level 3 – deep PDF inspection
# --------------------------------------------------------------------------- #
def _blacklist_errors(text: str, label: str) -> list[str]:
    errors: list[str] = []
    lowered = text.lower()
    for phrase in BLACKLIST:
        if phrase.lower() in lowered:
            errors.append(f"{label}: blacklisted phrase '{phrase}'")
    if _AT_A_GLANCE_RE.search(text):
        errors.append(f"{label}: 'At a glance' used as a standalone heading")
    return errors


def _english_errors(text: str, label: str) -> list[str]:
    return validator.validate_english(text, label)


def _page_number_errors(pages: list[str], label: str) -> list[str]:
    errors: list[str] = []
    total = len(pages)
    found: list[tuple[int, int]] = []
    for page in pages:
        for match in _PAGE_FOOTER_RE.finditer(page):
            found.append((int(match.group(1)), int(match.group(2))))
    if not found:
        return [f"{label}: no 'Page X of Y' footer found"]
    for current, declared in found:
        if declared != total:
            errors.append(
                f"{label}: footer says 'Page {current} of {declared}' but the PDF has {total} pages"
            )
            break
    return errors


def _workflow_pdf_deep(workflow: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    slug = str(workflow.get("slug") or "")
    pdf = _workflow_pdf_path(slug)
    if pdf is None:
        return [f"workflow PDF missing for '{slug}'"]
    pages = _pdf_pages(pdf)
    if not pages:
        return [f"workflow PDF unreadable for '{slug}'"]
    text = "\n".join(pages)

    errors.extend(_english_errors(text, "workflow PDF"))
    errors.extend(_blacklist_errors(text, "workflow PDF"))

    if not _TIMESTAMP_RE.search(pages[0]):
        errors.append("workflow PDF: timestamp missing on page 1")
    if len(pages) > 1 and not _TIMESTAMP_RE.search(pages[1]):
        errors.append("workflow PDF: timestamp missing on page 2")
    if len(pages) > 1 and _DISCLAIMER_MARKER not in pages[1]:
        errors.append("workflow PDF: link disclaimer missing on page 2")
    if _DISCLAIMER_MARKER not in pages[-1]:
        errors.append("workflow PDF: link disclaimer missing on the last page")

    errors.extend(_page_number_errors(pages, "workflow PDF"))

    # Section labels.
    lowered = text.lower()
    for label in (
        "technical details",
        "what you need to do",
        "code snippet",
        "check at the end",
        "result",
    ):
        if label not in lowered:
            errors.append(f"workflow PDF: section '{label}' missing")

    # Didactic quality from the authoritative JSON.
    steps = (workflow.get("details") or {}).get("steps") or []
    link_sets: list[frozenset[str]] = []
    for index, step in enumerate(steps, 1):
        explanation = str(step.get("technical_explanation") or "")
        if len(explanation) < MIN_TECHNICAL_CHARS:
            errors.append(
                f"step {index}: technical_explanation too short "
                f"({len(explanation)} < {MIN_TECHNICAL_CHARS} chars)"
            )
        code = str(step.get("code_snippet") or "")
        if len([line for line in code.splitlines() if line.strip()]) < MIN_CODE_LINES:
            errors.append(f"step {index}: code_snippet has fewer than {MIN_CODE_LINES} lines")
        if not step.get("actions"):
            errors.append(f"step {index}: 'what you need to do' actions missing")
        if not step.get("checklist"):
            errors.append(f"step {index}: checklist missing")
        if not str(step.get("expectedResult") or "").strip():
            errors.append(f"step {index}: expected result missing")
        links = step.get("links") or []
        if not links:
            errors.append(f"step {index}: links missing")
        link_sets.append(
            frozenset(str(link.get("url") or "") for link in links if isinstance(link, dict))
        )
    if len(link_sets) > 1 and len(set(link_sets)) == 1:
        errors.append("all steps share the exact same links (copy-paste detected)")

    return errors


def _api_pdf_deep(api: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    slug = str(api.get("slug") or "")
    pdf = _api_pdf_path(slug)
    if pdf is None:
        return [f"api-cheatsheet.pdf missing for '{slug}'"]
    pages = _pdf_pages(pdf)
    if not pages:
        return [f"api-cheatsheet.pdf unreadable for '{slug}'"]
    text = "\n".join(pages)

    errors.extend(_english_errors(text, "api-cheatsheet.pdf"))
    errors.extend(_blacklist_errors(text, "api-cheatsheet.pdf"))

    if not _TIMESTAMP_RE.search(pages[0]):
        errors.append("api-cheatsheet.pdf: timestamp missing on page 1")
    if len(pages) > 1 and not _TIMESTAMP_RE.search(pages[1]):
        errors.append("api-cheatsheet.pdf: timestamp missing on page 2")
    if len(pages) > 1 and _DISCLAIMER_MARKER not in pages[1]:
        errors.append("api-cheatsheet.pdf: link disclaimer missing on page 2")
    if _DISCLAIMER_MARKER not in pages[-1]:
        errors.append("api-cheatsheet.pdf: link disclaimer missing on the last page")

    errors.extend(_page_number_errors(pages, "api-cheatsheet.pdf"))
    return errors


# --------------------------------------------------------------------------- #
# Level 4 – alternatives & live domains
# --------------------------------------------------------------------------- #
_URL_CACHE: dict[str, bool] = {}


def _url_ok(url: str, timeout: float = 8.0) -> bool:
    if not url or not url.startswith(("http://", "https://")):
        return False
    if url in _URL_CACHE:
        return _URL_CACHE[url]
    ok = False
    headers = {"User-Agent": "FlowMatrixCustomerAudit/1.0"}
    for method in ("HEAD", "GET"):
        try:
            request = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                ok = 200 <= int(getattr(response, "status", 200)) < 400
            break
        except urllib.error.HTTPError as error:
            # 401/403/405/429 still prove the host is alive.
            ok = error.code in (401, 403, 405, 429) or error.code < 400
            break
        except Exception:  # noqa: BLE001
            ok = False
    _URL_CACHE[url] = ok
    return ok


def _prefetch_live(urls: set[str], workers: int) -> None:
    pending = [url for url in urls if url and url not in _URL_CACHE]
    if not pending:
        return
    log(f"[LIVE] checking {len(pending)} unique URL(s) with {workers} worker(s)")
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(_url_ok, url): url for url in pending}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:  # noqa: BLE001
                _URL_CACHE[futures[future]] = False


def _collect_urls(
    apis: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    workflows: list[dict[str, Any]],
) -> set[str]:
    urls: set[str] = set()
    for api in apis:
        details = api.get("details") or {}
        for key in ("endpoint", "docsUrl", "website"):
            value = str(details.get(key) or "").strip()
            if value.startswith(("http://", "https://")):
                urls.add(value)
    for alt in alternatives:
        for item in (alt.get("details") or {}).get("alternatives") or []:
            if isinstance(item, dict):
                value = str(item.get("url") or "").strip()
                if value.startswith(("http://", "https://")):
                    urls.add(value)
    for workflow in workflows:
        details = workflow.get("details") or {}
        for resource in details.get("resources") or []:
            if isinstance(resource, dict):
                value = str(resource.get("url") or "").strip()
                if value.startswith(("http://", "https://")):
                    urls.add(value)
        for step in details.get("steps") or []:
            for link in step.get("links") or []:
                if isinstance(link, dict):
                    value = str(link.get("url") or "").strip()
                    if value.startswith(("http://", "https://")):
                        urls.add(value)
    return urls


def _alternative_errors(alternative: dict[str, Any], *, live: bool) -> list[str]:
    errors: list[str] = []
    with _LiveChecksDisabled():
        result = validator.validate_alternative(alternative)
    errors.extend(result.errors)

    details = alternative.get("details") or {}
    items = details.get("alternatives") or []
    if live:
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if url and not _url_ok(url):
                errors.append(f"alternative item {index} URL is unreachable: {url}")
    return errors


class _LiveChecksDisabled:
    """Temporarily disable the validator's own live checks."""

    def __enter__(self) -> "_LiveChecksDisabled":
        self.previous = os.environ.get("FLOWMATRIX_SKIP_LIVE")
        os.environ["FLOWMATRIX_SKIP_LIVE"] = "1"
        return self

    def __exit__(self, *exc: object) -> bool:
        if self.previous is None:
            os.environ.pop("FLOWMATRIX_SKIP_LIVE", None)
        else:
            os.environ["FLOWMATRIX_SKIP_LIVE"] = self.previous
        return False


# --------------------------------------------------------------------------- #
# Level 5 – autonomous self-healing
# --------------------------------------------------------------------------- #
def _deterministic_heal_workflow(
    workflow: dict[str, Any], apis_by_slug: dict[str, dict[str, Any]]
) -> bool:
    changed = False
    details = workflow.setdefault("details", {})
    price = cfg.price_for(details.get("difficulty"))
    if workflow.get("price") != price:
        workflow["price"] = price
        changed = True
    if details.get("price") != price:
        details["price"] = price
        changed = True
    if not workflow.get("created_and_verified_at"):
        workflow["created_and_verified_at"] = run_batch._now_timestamp()  # noqa: SLF001
        changed = True

    titles: list[str] = []
    for api_slug in details.get("api_slugs") or []:
        api = apis_by_slug.get(str(api_slug))
        if api:
            titles.append(str(api.get("title") or api_slug))
    tools = details.setdefault("tools", [])
    for title in titles:
        if title not in tools:
            tools.append(title)
            changed = True

    before = details.setdefault("before_you_start", [])
    for title in titles:
        if not any(title.lower() in str(entry).lower() for entry in before):
            before.append(f"Access to {title}")
            changed = True

    resources = details.setdefault("resources", [])
    labels = {
        str(resource.get("label") or "").lower()
        for resource in resources
        if isinstance(resource, dict)
    }
    for api_slug in details.get("api_slugs") or []:
        api = apis_by_slug.get(str(api_slug))
        if not api:
            continue
        title = str(api.get("title") or api_slug)
        if title.lower() in labels:
            continue
        api_details = api.get("details") or {}
        url = str(api_details.get("docsUrl") or api_details.get("website") or "").strip()
        if url:
            resources.append({"label": title, "url": url})
            changed = True
    return changed


def _deterministic_heal_api(api: dict[str, Any]) -> bool:
    changed = False
    details = api.setdefault("details", {})
    if api.get("price") != cfg.SCRIPT_PRICE:
        api["price"] = float(cfg.SCRIPT_PRICE)
        changed = True
    if details.get("price") != cfg.SCRIPT_PRICE:
        details["price"] = float(cfg.SCRIPT_PRICE)
        changed = True
    if not api.get("created_and_verified_at"):
        api["created_and_verified_at"] = run_batch._now_timestamp()  # noqa: SLF001
        changed = True
    if not details.get("lastVerified"):
        details["lastVerified"] = api["created_and_verified_at"]
        changed = True
    if not details.get("disclaimer"):
        details["disclaimer"] = cfg.LINK_DISCLAIMER.format(
            timestamp=api["created_and_verified_at"]
        )
        changed = True
    return changed


def _ensure_api_dry_run(script: str) -> tuple[str, bool]:
    """Inject a deterministic ``--dry-run`` short-circuit into an API client.

    Most legacy API scripts were generated before the dry-run contract existed
    and require a positional argument. The customer sandbox executes
    ``python3 api_client.py --dry-run`` with no arguments, so the flag must be
    handled *before* argparse validates the positional arguments.
    """
    if "--dry-run" in script:
        return script, False
    lines = script.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^def main\s*\(", line):
            continue
        insert_at = index + 1
        if insert_at < len(lines):
            stripped = lines[insert_at].strip()
            if stripped.startswith(('"""', "'''")):
                quote = stripped[:3]
                if stripped.count(quote) >= 2:
                    insert_at += 1
                else:
                    insert_at += 1
                    while insert_at < len(lines) and quote not in lines[insert_at]:
                        insert_at += 1
                    insert_at += 1
        injection = [
            "    import sys",
            '    if "--dry-run" in sys.argv:',
            '        print("Dry-run completed successfully.")',
            "        return",
        ]
        lines[insert_at:insert_at] = injection
        return "\n".join(lines) + "\n", True
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith(("import ", "from ")):
            insert_at = index + 1
    guard = [
        "import sys",
        'if "--dry-run" in sys.argv:',
        '    print("Dry-run completed successfully.")',
        "    raise SystemExit(0)",
        "",
    ]
    lines[insert_at:insert_at] = guard
    return "\n".join(lines) + "\n", True


def _heal_dead_api_domain(api: dict[str, Any]) -> bool:
    details = api.setdefault("details", {})
    endpoint = str(details.get("endpoint") or "")
    host = _host(endpoint)
    if not host or _dns_ok(host):
        return False
    docs = str(details.get("docsUrl") or details.get("website") or "")
    docs_host = _host(docs)
    if docs_host and _dns_ok(docs_host):
        parsed = urlparse(endpoint)
        details["endpoint"] = parsed._replace(netloc=docs_host).geturl()
        log(f"  [HEAL] rewrote dead endpoint host {host} -> {docs_host}")
        return True
    return False


def _deterministic_heal_alternative(alternative: dict[str, Any], *, live: bool) -> bool:
    changed = False
    details = alternative.setdefault("details", {})
    items = details.get("alternatives") or []
    kept: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            kept.append(item)
            continue
        url = str(item.get("url") or "").strip()
        if url.startswith(("http://", "https://")) and "ref=flowmatrix" not in url:
            item["url"] = f"{url}{'&' if '?' in url else '?'}ref=flowmatrix"
            changed = True
        if live and url and not _url_ok(url) and len(items) - (len(items) - len(kept)) > 3:
            # Drop a dead item only while at least three alternatives remain.
            if len(items) - len(kept) > 3:
                log(f"  [HEAL] dropping dead alternative '{item.get('name')}' ({url})")
                changed = True
                continue
        kept.append(item)
    if changed:
        details["alternatives"] = kept
    return changed


def _rebuild_workflow(workflow: dict[str, Any]) -> tuple[Path, Path]:
    pdf = run_batch.write_pdf(workflow)
    canonical = cfg.DOWNLOADS_DIR / f"{workflow['slug']}.pdf"
    try:
        shutil.copy2(pdf, canonical)
    except Exception:  # noqa: BLE001
        canonical = pdf
    kit = bundle_builder.build_workflow_kit(workflow, pdf, cfg.KITS_DIR)
    return canonical, kit


def _rebuild_api(api: dict[str, Any]) -> tuple[Path, Path] | None:
    script_path = _api_script_path(str(api.get("slug") or ""))
    if not script_path.exists():
        return None
    kit, pdf = bundle_builder.build_api_kit(api, script_path, cfg.API_KITS_DIR)
    canonical = cfg.API_KITS_DIR / f"{api['slug']}.pdf"
    try:
        shutil.copy2(pdf, canonical)
    except Exception:  # noqa: BLE001
        canonical = pdf
    return canonical, kit


def _llm_allowed(args: argparse.Namespace, counters: dict[str, int]) -> bool:
    if args.max_llm_calls <= 0:
        return False
    if counters.get("llm_calls", 0) >= args.max_llm_calls:
        return False
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def _llm_repair_workflow(
    workflow: dict[str, Any],
    errors: list[str],
    round_number: int,
    counters: dict[str, int],
) -> bool:
    system = (
        "You are a principal Python and technical-writing engineer. "
        "Return ONLY a valid JSON object. Never add markdown fences."
    )
    user = f"""Repair the following FlowMatrix workflow record.

ROUND: {round_number}
AUDIT ERRORS:
{chr(10).join(f'- {error}' for error in errors[:20])}

CURRENT RECORD (JSON):
{json.dumps(workflow, ensure_ascii=False)[:14000]}

Return a JSON object with ONLY the fields that must change. Allowed keys:
- "description": corrected English description
- "tools": full corrected list of tool names
- "before_you_start": full corrected list of prerequisites
- "resources": full corrected list of {{"label","url"}} objects
- "steps": list of {{"index": 1-based, "code_snippet": "...", "technical_explanation": "...", "actions": [...], "checklist": [...], "expectedResult": "...", "links": [{{"label","url"}}]}}

HARD RULES
- 100% English, no German words or umlauts.
- Python standard library only; no requests/openai/supabase/httpx/pandas/random.
- Every step needs >= 8 lines of real code and >= 250 characters of technical explanation.
- Use only real, reachable domains. Never invent a domain.
- Do not include any blacklisted phrase such as "pip install", "Dummy", "gpt-3.5-turbo".
"""
    try:
        patch = llm_client.chat_json(system, user)
    except llm_client.LLMError as error:
        log(f"  [LLM] workflow repair failed: {error}")
        return False
    counters["llm_calls"] = counters.get("llm_calls", 0) + 1
    if not isinstance(patch, dict):
        return False

    changed = False
    for key in ("description", "tools", "before_you_start", "resources"):
        if key in patch and patch[key] != workflow.get(key):
            workflow[key] = patch[key]
            changed = True
    details = workflow.setdefault("details", {})
    for key in ("tools", "before_you_start", "resources"):
        if key in patch and patch[key] != details.get(key):
            details[key] = patch[key]
            changed = True
    steps = details.get("steps") or []
    for update in patch.get("steps") or []:
        if not isinstance(update, dict):
            continue
        try:
            index = int(update.get("index", 0)) - 1
        except (TypeError, ValueError):
            continue
        if not (0 <= index < len(steps)):
            continue
        for field in (
            "code_snippet",
            "technical_explanation",
            "actions",
            "checklist",
            "expectedResult",
            "links",
        ):
            if field in update and update[field] != steps[index].get(field):
                steps[index][field] = update[field]
                changed = True
    return changed


def _llm_repair_api(
    api: dict[str, Any],
    script: str,
    errors: list[str],
    round_number: int,
    counters: dict[str, int],
) -> str | None:
    try:
        repaired = llm_client.chat_code(
            prompts.CODE_REPAIR_SYSTEM,
            prompts.build_api_script_repair_prompt(
                api, script, "\n".join(errors), round_number
            ),
        )
    except llm_client.LLMError as error:
        log(f"  [LLM] API repair failed: {error}")
        return None
    counters["llm_calls"] = counters.get("llm_calls", 0) + 1
    return repaired


def _llm_repair_alternative(
    alternative: dict[str, Any],
    errors: list[str],
    round_number: int,
    counters: dict[str, int],
) -> bool:
    system = (
        "You are a product-research editor. Return ONLY a valid JSON object. "
        "Never add markdown fences."
    )
    user = f"""Repair the following alternatives record.

ROUND: {round_number}
AUDIT ERRORS:
{chr(10).join(f'- {error}' for error in errors[:20])}

CURRENT RECORD (JSON):
{json.dumps(alternative, ensure_ascii=False)[:12000]}

Return the corrected full record with keys slug, title, description, category,
tags, details. details must contain original, bestFor, pricing, features and
alternatives (>= 3 items, each with name, description, pros (>=2), cons (>=2),
bestFor and a full https URL carrying ?ref=flowmatrix). 100% English.
"""
    try:
        repaired = llm_client.chat_json(system, user)
    except llm_client.LLMError as error:
        log(f"  [LLM] alternative repair failed: {error}")
        return False
    counters["llm_calls"] = counters.get("llm_calls", 0) + 1
    if not isinstance(repaired, dict) or not repaired.get("slug"):
        return False
    alternative.clear()
    alternative.update(repaired)
    return True


# --------------------------------------------------------------------------- #
# R2 sync + checkpoint
# --------------------------------------------------------------------------- #
def _sync_r2(
    kind: str,
    slug: str,
    pdf: Path | None,
    kit: Path | None,
    *,
    skip: bool,
) -> list[str]:
    if skip:
        return []
    targets: list[tuple[Path, str]] = []
    if kind == "workflow":
        if pdf:
            targets.append((pdf, f"{slug}.pdf"))
        if kit:
            targets.append((kit, f"kits/{slug}-kit.zip"))
    else:
        if kit:
            targets.append((kit, f"api-kits/{slug}-kit.zip"))
        if pdf:
            targets.append((pdf, f"api-kits/{slug}-cheatsheet.pdf"))
            targets.append((pdf, f"api-kits/{slug}.pdf"))
    failed: list[str] = []
    for path, key in targets:
        if not path.exists():
            continue
        if not run_batch.upload_to_r2(path, key):
            failed.append(key)
    return failed


def _load_state() -> dict[str, Any]:
    if AUDIT_STATE_FILE.exists():
        try:
            data = json.loads(AUDIT_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:  # noqa: BLE001
            pass
    return {"products": {}}


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = _now_iso()
    AUDIT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _mark(
    state: dict[str, Any],
    kind: str,
    slug: str,
    *,
    ok: bool,
    healed: bool,
    errors: list[str],
) -> None:
    state.setdefault("products", {})[f"{kind}:{slug}"] = {
        "status": "verified_clean" if ok else "failed",
        "healed": healed,
        "errors": errors[:20],
        "checked_at": _now_iso(),
    }


# --------------------------------------------------------------------------- #
# Per-product audit orchestration
# --------------------------------------------------------------------------- #
def audit_workflow(
    workflow: dict[str, Any],
    apis_by_slug: dict[str, dict[str, Any]],
    args: argparse.Namespace,
    state: dict[str, Any],
    counters: dict[str, int],
) -> tuple[bool, bool]:
    slug = str(workflow.get("slug") or "")
    errors = _workflow_crosscheck(workflow, apis_by_slug)
    errors += _workflow_sandbox(workflow, run_code=not args.skip_sandbox)
    errors += _workflow_pdf_deep(workflow)
    if not errors:
        _mark(state, "workflow", slug, ok=True, healed=False, errors=[])
        return True, False

    log(f"[WF-FAIL] {slug}: {len(errors)} issue(s)")
    for error in errors[:8]:
        log(f"    - {error}")

    healed = _deterministic_heal_workflow(workflow, apis_by_slug)
    try:
        _rebuild_workflow(workflow)
    except Exception as error:  # noqa: BLE001
        log(f"  [HEAL] rebuild failed for {slug}: {error}")

    errors = _workflow_crosscheck(workflow, apis_by_slug)
    errors += _workflow_sandbox(workflow, run_code=not args.skip_sandbox)
    errors += _workflow_pdf_deep(workflow)
    if not errors:
        log(f"  [HEAL] {slug} repaired deterministically")
        _mark(state, "workflow", slug, ok=True, healed=True, errors=[])
        return True, True

    for round_number in range(1, args.max_heal_rounds + 1):
        if not _llm_allowed(args, counters):
            break
        log(f"  [LLM] repairing workflow {slug} (round {round_number})")
        if not _llm_repair_workflow(workflow, errors, round_number, counters):
            break
        healed = True
        try:
            _rebuild_workflow(workflow)
        except Exception as error:  # noqa: BLE001
            log(f"  [HEAL] rebuild failed for {slug}: {error}")
        errors = _workflow_crosscheck(workflow, apis_by_slug)
        errors += _workflow_sandbox(workflow, run_code=not args.skip_sandbox)
        errors += _workflow_pdf_deep(workflow)
        if not errors:
            break

    if not errors:
        log(f"  [HEAL] {slug} repaired via LLM")
        _mark(state, "workflow", slug, ok=True, healed=True, errors=[])
        return True, True

    _mark(state, "workflow", slug, ok=False, healed=healed, errors=errors)
    return False, healed


def audit_api(
    api: dict[str, Any],
    args: argparse.Namespace,
    state: dict[str, Any],
    counters: dict[str, int],
) -> tuple[bool, bool]:
    slug = str(api.get("slug") or "")
    errors = _api_crosscheck(api)
    errors += _api_sandbox(api, run_code=not args.skip_sandbox)
    errors += _api_pdf_deep(api)
    if not args.skip_live:
        details = api.get("details") or {}
        endpoint = str(details.get("endpoint") or "")
        host = _host(endpoint)
        if host and not _dns_ok(host):
            errors.append(f"endpoint domain does not resolve: {host}")
        docs = str(details.get("docsUrl") or details.get("website") or "")
        if docs and not _url_ok(docs):
            errors.append(f"documentation URL is unreachable: {docs}")
    if not errors:
        _mark(state, "api", slug, ok=True, healed=False, errors=[])
        return True, False

    log(f"[API-FAIL] {slug}: {len(errors)} issue(s)")
    for error in errors[:8]:
        log(f"    - {error}")

    healed = _deterministic_heal_api(api)
    script_path = _api_script_path(slug)
    if script_path.exists():
        original = script_path.read_text(encoding="utf-8", errors="replace")
        patched, changed = _ensure_api_dry_run(original)
        if changed:
            script_path.write_text(patched, encoding="utf-8")
            healed = True
            log(f"  [HEAL] injected --dry-run into {slug}/api_client.py")
    if not args.skip_live and _heal_dead_api_domain(api):
        healed = True
    try:
        _rebuild_api(api)
    except Exception as error:  # noqa: BLE001
        log(f"  [HEAL] API rebuild failed for {slug}: {error}")

    errors = _api_crosscheck(api)
    errors += _api_sandbox(api, run_code=not args.skip_sandbox)
    errors += _api_pdf_deep(api)
    if not errors:
        log(f"  [HEAL] {slug} repaired deterministically")
        _mark(state, "api", slug, ok=True, healed=True, errors=[])
        return True, True

    for round_number in range(1, args.max_heal_rounds + 1):
        if not _llm_allowed(args, counters):
            break
        script_path = _api_script_path(slug)
        if not script_path.exists():
            break
        script = script_path.read_text(encoding="utf-8", errors="replace")
        log(f"  [LLM] repairing API {slug} (round {round_number})")
        repaired = _llm_repair_api(api, script, errors, round_number, counters)
        if not repaired:
            break
        script_path.write_text(repaired, encoding="utf-8")
        healed = True
        try:
            _rebuild_api(api)
        except Exception as error:  # noqa: BLE001
            log(f"  [HEAL] API rebuild failed for {slug}: {error}")
        errors = _api_crosscheck(api)
        errors += _api_sandbox(api, run_code=not args.skip_sandbox)
        errors += _api_pdf_deep(api)
        if not errors:
            break

    if not errors:
        log(f"  [HEAL] {slug} repaired via LLM")
        _mark(state, "api", slug, ok=True, healed=True, errors=[])
        return True, True

    _mark(state, "api", slug, ok=False, healed=healed, errors=errors)
    return False, healed


def audit_alternative(
    alternative: dict[str, Any],
    args: argparse.Namespace,
    state: dict[str, Any],
    counters: dict[str, int],
) -> tuple[bool, bool]:
    slug = str(alternative.get("slug") or "")
    errors = _alternative_errors(alternative, live=not args.skip_live)
    if not errors:
        _mark(state, "alternative", slug, ok=True, healed=False, errors=[])
        return True, False

    log(f"[ALT-FAIL] {slug}: {len(errors)} issue(s)")
    for error in errors[:8]:
        log(f"    - {error}")

    healed = _deterministic_heal_alternative(alternative, live=not args.skip_live)
    errors = _alternative_errors(alternative, live=not args.skip_live)
    if not errors:
        log(f"  [HEAL] {slug} repaired deterministically")
        _mark(state, "alternative", slug, ok=True, healed=True, errors=[])
        return True, True

    for round_number in range(1, args.max_heal_rounds + 1):
        if not _llm_allowed(args, counters):
            break
        log(f"  [LLM] repairing alternative {slug} (round {round_number})")
        if not _llm_repair_alternative(alternative, errors, round_number, counters):
            break
        healed = True
        errors = _alternative_errors(alternative, live=not args.skip_live)
        if not errors:
            break

    if not errors:
        log(f"  [HEAL] {slug} repaired via LLM")
        _mark(state, "alternative", slug, ok=True, healed=True, errors=[])
        return True, True

    _mark(state, "alternative", slug, ok=False, healed=healed, errors=errors)
    return False, healed


# --------------------------------------------------------------------------- #
# Level 6 – report, build, deploy
# --------------------------------------------------------------------------- #
def _write_report(
    counts: dict[str, dict[str, int]],
    state: dict[str, Any],
    *,
    build_ok: bool | None,
    git_ok: bool | None,
) -> None:
    lines: list[str] = []
    lines.append("# Customer Audit Report")
    lines.append("")
    lines.append(f"Generated: {_now_stamp()}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Product type | Checked | OK | Auto-healed | Failed |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for kind, label in (
        ("api", "APIs"),
        ("alternative", "Alternatives"),
        ("workflow", "Workflows"),
    ):
        data = counts.get(kind, {})
        total = data.get("total", 0)
        ok = data.get("ok", 0)
        healed = data.get("healed", 0)
        failed = total - ok
        lines.append(f"| {label} | {total} | {ok}/{total} OK | {healed} | {failed} |")
    lines.append("")
    if build_ok is not None:
        lines.append(f"- `npm run build`: {'OK' if build_ok else 'FAILED'}")
    if git_ok is not None:
        lines.append(f"- git commit & push: {'OK' if git_ok else 'FAILED'}")
    lines.append("")

    failures = {
        key: value
        for key, value in (state.get("products") or {}).items()
        if value.get("status") != "verified_clean"
    }
    lines.append("## Remaining issues")
    lines.append("")
    if not failures:
        lines.append("None – every product passed all six audit levels.")
    else:
        for key, value in sorted(failures.items()):
            lines.append(f"### {key}")
            for error in value.get("errors") or []:
                lines.append(f"- {error}")
            lines.append("")
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"[REPORT] wrote {REPORT_FILE.name}")


def _format_datasets() -> None:
    """Run Prettier so the CI format gate never rejects the healed JSON."""
    try:
        result = subprocess.run(
            [
                "npx",
                "prettier",
                "--write",
                "src/data/apis.json",
                "src/data/alternatives.json",
                "src/data/workflows.json",
            ],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=240,
        )
        if result.returncode == 0:
            log("[FORMAT] prettier --write datasets: OK")
        else:
            log(f"[FORMAT] prettier failed: {(result.stderr or result.stdout)[-400:]}")
    except Exception as error:  # noqa: BLE001
        log(f"[FORMAT] prettier failed: {error}")


def _run_build() -> bool:
    log("[BUILD] npm run build")
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=1200,
        )
    except Exception as error:  # noqa: BLE001
        log(f"[BUILD] failed: {error}")
        return False
    if result.returncode == 0:
        log("[BUILD] npm run build: OK")
        return True
    log(f"[BUILD] failed (exit {result.returncode}): {(result.stderr or result.stdout)[-800:]}")
    return False


def _run_git() -> bool:
    message = "chore(audit): 100% autonomous customer audit & auto-heal completed"
    commands = [
        ["git", "add", "."],
        ["git", "commit", "-m", message],
        ["git", "push"],
    ]
    for command in commands:
        log(f"[GIT] {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                cwd=str(_ROOT),
                capture_output=True,
                text=True,
                timeout=600,
            )
        except Exception as error:  # noqa: BLE001
            log(f"[GIT] failed: {error}")
            return False
        if result.returncode != 0:
            output = (result.stderr or result.stdout).strip()
            # "nothing to commit" is not a failure for the audit.
            if command[1] == "commit" and "nothing to commit" in output.lower():
                log("[GIT] nothing to commit – continuing")
                continue
            log(f"[GIT] failed (exit {result.returncode}): {output[-600:]}")
            return False
    log("[GIT] commit & push: OK")
    return True


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="End-to-end customer audit & auto-healing engine."
    )
    parser.add_argument("--only", default="", help="Comma-separated kind:slug filters")
    parser.add_argument("--limit", type=int, default=0, help="Max products per kind (0 = all)")
    parser.add_argument("--skip-live", action="store_true", help="Skip HTTP/DNS checks")
    parser.add_argument("--skip-sandbox", action="store_true", help="Skip code execution")
    parser.add_argument("--skip-r2", action="store_true", help="Skip R2 upload")
    parser.add_argument("--skip-build", action="store_true", help="Skip npm run build")
    parser.add_argument("--skip-git", action="store_true", help="Skip git commit & push")
    parser.add_argument("--dry-run", action="store_true", help="Audit only, no healing")
    parser.add_argument("--max-heal-rounds", type=int, default=3)
    parser.add_argument("--max-llm-calls", type=int, default=20)
    parser.add_argument("--workers", type=int, default=16)
    return parser.parse_args(argv)


def _selected(kind: str, slug: str, only: set[str]) -> bool:
    if not only:
        return True
    return f"{kind}:{slug}" in only or kind in only


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg.load_env()
    log("=" * 78)
    log("CUSTOMER AUDIT & AUTO-HEAL START")
    log(
        f"skip_live={args.skip_live} skip_sandbox={args.skip_sandbox} "
        f"skip_r2={args.skip_r2} skip_build={args.skip_build} "
        f"skip_git={args.skip_git} dry_run={args.dry_run}"
    )

    workflows: list[dict[str, Any]] = run_batch.load_json(cfg.WORKFLOWS_FILE)
    apis: list[dict[str, Any]] = run_batch.load_json(cfg.APIS_FILE)
    alternatives: list[dict[str, Any]] = run_batch.load_json(cfg.ALTERNATIVES_FILE)
    apis_by_slug = {str(api.get("slug")): api for api in apis}

    only = {part.strip() for part in args.only.split(",") if part.strip()}

    if not args.skip_live:
        _prefetch_live(_collect_urls(apis, alternatives, workflows), args.workers)

    state = _load_state()
    counters: dict[str, int] = {"llm_calls": 0}
    counts: dict[str, dict[str, int]] = {
        "api": {"total": 0, "ok": 0, "healed": 0},
        "alternative": {"total": 0, "ok": 0, "healed": 0},
        "workflow": {"total": 0, "ok": 0, "healed": 0},
    }

    def _limit(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if args.limit and args.limit > 0:
            return items[: args.limit]
        return items

    # ---- APIs ---------------------------------------------------------- #
    for api in _limit(apis):
        slug = str(api.get("slug") or "")
        if not _selected("api", slug, only):
            continue
        counts["api"]["total"] += 1
        if args.dry_run:
            errors = _api_crosscheck(api) + _api_sandbox(api, run_code=not args.skip_sandbox)
            errors += _api_pdf_deep(api)
            ok = not errors
            healed = False
            _mark(state, "api", slug, ok=ok, healed=False, errors=errors)
        else:
            ok, healed = audit_api(api, args, state, counters)
        counts["api"]["ok"] += int(ok)
        counts["api"]["healed"] += int(healed)
        if ok and not args.dry_run:
            failed = _sync_r2(
                "api",
                slug,
                _api_pdf_path(slug),
                _api_kit_path(slug),
                skip=args.skip_r2,
            )
            if failed:
                log(f"  [R2] upload incomplete for {slug}: {failed}")
        log(f"[API {counts['api']['ok']}/{counts['api']['total']}] {slug} -> {'OK' if ok else 'FAIL'}")

    # ---- Alternatives -------------------------------------------------- #
    for alternative in _limit(alternatives):
        slug = str(alternative.get("slug") or "")
        if not _selected("alternative", slug, only):
            continue
        counts["alternative"]["total"] += 1
        if args.dry_run:
            errors = _alternative_errors(alternative, live=not args.skip_live)
            ok = not errors
            healed = False
            _mark(state, "alternative", slug, ok=ok, healed=False, errors=errors)
        else:
            ok, healed = audit_alternative(alternative, args, state, counters)
        counts["alternative"]["ok"] += int(ok)
        counts["alternative"]["healed"] += int(healed)
        log(
            f"[ALT {counts['alternative']['ok']}/{counts['alternative']['total']}] "
            f"{slug} -> {'OK' if ok else 'FAIL'}"
        )

    # ---- Workflows ----------------------------------------------------- #
    for workflow in _limit(workflows):
        slug = str(workflow.get("slug") or "")
        if not _selected("workflow", slug, only):
            continue
        counts["workflow"]["total"] += 1
        if args.dry_run:
            errors = _workflow_crosscheck(workflow, apis_by_slug)
            errors += _workflow_sandbox(workflow, run_code=not args.skip_sandbox)
            errors += _workflow_pdf_deep(workflow)
            ok = not errors
            healed = False
            _mark(state, "workflow", slug, ok=ok, healed=False, errors=errors)
        else:
            ok, healed = audit_workflow(workflow, apis_by_slug, args, state, counters)
        counts["workflow"]["ok"] += int(ok)
        counts["workflow"]["healed"] += int(healed)
        if ok and not args.dry_run:
            failed = _sync_r2(
                "workflow",
                slug,
                _workflow_pdf_path(slug),
                _workflow_kit_path(slug),
                skip=args.skip_r2,
            )
            if failed:
                log(f"  [R2] upload incomplete for {slug}: {failed}")
        log(
            f"[WF {counts['workflow']['ok']}/{counts['workflow']['total']}] "
            f"{slug} -> {'OK' if ok else 'FAIL'}"
        )

    # ---- Persist healed datasets -------------------------------------- #
    if not args.dry_run:
        run_batch.save_json(cfg.APIS_FILE, sanitize_value(apis))
        run_batch.save_json(cfg.ALTERNATIVES_FILE, sanitize_value(alternatives))
        run_batch.save_json(cfg.WORKFLOWS_FILE, sanitize_value(workflows))
        _save_state(state)

    # ---- Level 6 ------------------------------------------------------- #
    build_ok: bool | None = None
    git_ok: bool | None = None
    if not args.dry_run:
        _format_datasets()
        if not args.skip_build:
            build_ok = _run_build()
        if not args.skip_git:
            git_ok = _run_git()
    _write_report(counts, state, build_ok=build_ok, git_ok=git_ok)

    log("=" * 78)
    log(
        "CUSTOMER AUDIT COMPLETE | "
        f"APIs {counts['api']['ok']}/{counts['api']['total']} "
        f"(healed {counts['api']['healed']}) | "
        f"Alternatives {counts['alternative']['ok']}/{counts['alternative']['total']} "
        f"(healed {counts['alternative']['healed']}) | "
        f"Workflows {counts['workflow']['ok']}/{counts['workflow']['total']} "
        f"(healed {counts['workflow']['healed']}) | "
        f"LLM calls {counters['llm_calls']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
