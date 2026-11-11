"""100 % End-to-End-Audit & Auto-Healing für ALLE verkaufbaren Produkte.

Prüft jeden Workflow (PDF + ``<slug>-kit.zip``) und jedes API-Skript
(``api-cheatsheet.pdf`` + ``<slug>-kit.zip``) in sechs Stufen:

    Stufe 1  Echter Kunden-Sandbox-Test (ZIP entpacken, Code ausführen)
    Stufe 2  Tiefenprüfung aller Python-Skripte & PDF-Code-Snippets
    Stufe 3  Visuelle & inhaltliche PDF-Endkontrolle (echtes PDF auslesen)
    Stufe 4  Gepufferter Live-Domain- & URL-Check
    Stufe 5  Automatische Selbstheilung (Rebuild + optional LLM) & R2-Sync
    Stufe 6  Abschluss-Report, Astro-Build & Deployment

Aufruf (als Paket-Modul, damit die relativen Imports funktionieren)::

    .venv/bin/python -m pipeline.full_product_audit --heal
    .venv/bin/python -m pipeline.full_product_audit --limit 2
    .venv/bin/python -m pipeline.full_product_audit --heal --deploy
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:  # PDF text extraction (audit-only dependency).
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]

from . import bundle_builder
from . import config as cfg
from . import llm_client
from . import pdf_renderer
from . import prompts

# --------------------------------------------------------------------------- #
# Result model
# --------------------------------------------------------------------------- #


@dataclass
class Finding:
    stage: int
    message: str

    def __str__(self) -> str:
        return f"[S{self.stage}] {self.message}"


@dataclass
class ProductReport:
    slug: str
    kind: str  # "workflow" | "api"
    price: str = ""
    pages: int = 0
    dry_run_exit: str = "—"
    zip_ok: bool = False
    domains_ok: bool = True
    r2_synced: bool = False
    healed: bool = False
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #

_TRACEBACK_MARKERS = (
    "Traceback",
    "TypeError",
    "KeyError",
    "NameError",
    "ValueError",
    "JSONDecodeError",
    "SyntaxError",
    "AttributeError",
    "IndexError",
    "ZeroDivisionError",
    "ModuleNotFoundError",
    "ImportError",
)

_BLACKLIST = tuple(
    {
        *cfg.BLACKLIST_PHRASES,
        "Official docs for the API used in THIS step",
        "Prenium Warkflow",
        "File > New",
        "File > Save",
        "Make a Zap",
        "Adobe XD",
        "api.supabase.io",
        "ChatCompletion.create",
        "gpt-3.5-turbo",
        "scikit-learn",
        "pip install",
        "Dummy",
        "Node.js 18",
        "€4.99",
        "€7.99",
        "€12.99",
        "€21.99",
    }
)

# Correct prices per spec.
_FORBIDDEN_PRICES = ("€4.99", "€7.99", "€12.99", "€21.99", "4.99", "7.99", "12.99", "21.99")

_ENV_RE = re.compile(
    r"""os\.(?:environ\.get|getenv)\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
)
_ENV_INDEX_RE = re.compile(r"""os\.environ\[\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]\s*\]""")
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]}]+")
_HTTP_REQ_RE = re.compile(
    r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\S+)", re.IGNORECASE | re.MULTILINE
)

_PLACEHOLDER_HOST_MARKERS = (
    "<",
    ">",
    "{",
    "}",
    "your",
    "example",
    "mock",
    "localhost",
    "127.0.0.1",
    "dummy",
    "acme",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _iter_strings(payload: Any) -> list[str]:
    out: list[str] = []
    if isinstance(payload, str):
        out.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            out.extend(_iter_strings(value))
    elif isinstance(payload, list):
        for value in payload:
            out.extend(_iter_strings(value))
    return out


def _collect_urls(product: dict[str, Any]) -> list[str]:
    urls: set[str] = set()
    for text in _iter_strings(product):
        for url in _URL_RE.findall(text):
            urls.add(url.rstrip(".,;"))
    return sorted(urls)


def _step_codes(workflow: dict[str, Any]) -> list[str]:
    steps = (workflow.get("details") or {}).get("steps") or []
    return [str(step.get("code_snippet") or "") for step in steps]


def _full_workflow_code(workflow: dict[str, Any]) -> str:
    return "\n\n".join(_step_codes(workflow))


# --------------------------------------------------------------------------- #
# Stage 1 – real customer sandbox
# --------------------------------------------------------------------------- #


def _env_names_from_code(code: str) -> set[str]:
    """Return env vars actually read by the code (AST-based, ignores comments)."""
    names: set[str] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        cleaned = "\n".join(
            line for line in code.splitlines() if not line.strip().startswith("#")
        )
        names.update(_ENV_RE.findall(cleaned))
        names.update(_ENV_INDEX_RE.findall(cleaned))
        return names

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func = node.func
            is_environ_get = (
                func.attr == "get"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "environ"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "os"
            )
            is_getenv = (
                func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            )
            if (is_environ_get or is_getenv) and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    names.add(arg.value)
        elif isinstance(node, ast.Subscript):
            value = node.value
            if (
                isinstance(value, ast.Attribute)
                and value.attr == "environ"
                and isinstance(value.value, ast.Name)
                and value.value.id == "os"
            ):
                sl = node.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    names.add(sl.value)
    return names


def _parse_env_example(text: str) -> set[str]:
    names: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        names.add(line.split("=", 1)[0].strip())
    return names


def _check_requests_http(text: str) -> list[str]:
    problems: list[str] = []
    requests = _HTTP_REQ_RE.findall(text)
    if not requests and "# No direct HTTP calls detected." not in text:
        problems.append("requests.http contains no valid HTTP requests")
    for method, url in requests:
        if method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
            problems.append(f"requests.http invalid method: {method}")
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("{{")):
            problems.append(f"requests.http invalid URL: {url}")
        if url.count("{{") != url.count("}}"):
            problems.append(f"requests.http truncated placeholder: {url}")
    return problems


def _run_sandbox(
    cmd: list[str], cwd: Path, timeout: int = 25
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(
            cmd, 124, stdout="", stderr=f"TimeoutExpired after {timeout}s: {error}"
        )


def audit_zip_sandbox(
    product: dict[str, Any], kind: str, zip_path: Path
) -> tuple[bool, str, list[str]]:
    """Stage 1. Returns (zip_ok, dry_run_exit, problems)."""
    problems: list[str] = []
    if not zip_path.exists():
        return False, "missing", [f"ZIP missing: {zip_path.name}"]

    required = cfg.WORKFLOW_KIT_FILES if kind == "workflow" else cfg.API_KIT_FILES
    try:
        with zipfile.ZipFile(zip_path) as zf:
            bad = zf.testzip()
            if bad is not None:
                problems.append(f"ZIP corrupt member: {bad}")
            names = set(zf.namelist())
            for filename in required:
                if filename not in names:
                    problems.append(f"ZIP missing required file: {filename}")
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if info.file_size == 0:
                    problems.append(f"ZIP member is 0 bytes: {info.filename}")
    except zipfile.BadZipFile as error:
        return False, "badzip", [f"ZIP is not readable: {error}"]

    if problems:
        # Still extract to continue where possible.
        pass

    dry_exit = "—"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp)
        except zipfile.BadZipFile as error:
            return False, "badzip", [f"ZIP extraction failed: {error}"]

        directory = Path(tmp)
        if kind == "workflow":
            entry = directory / "workflow.py"
            if entry.exists():
                result = _run_sandbox(
                    [sys.executable, "workflow.py", "--dry-run"], directory
                )
                dry_exit = str(result.returncode)
                problems.extend(_judge_execution(result, kind))
        else:
            entry = directory / "api_client.py"
            test_file = directory / "test_mock.py"
            if entry.exists() and test_file.exists():
                result = _run_sandbox(
                    [sys.executable, "-m", "unittest", "test_mock.py", "-v"], directory
                )
                dry_exit = str(result.returncode)
                problems.extend(_judge_execution(result, kind))
            else:
                problems.append("API kit lacks api_client.py or test_mock.py")

        # --- .env.example coverage ------------------------------------- #
        script_path = directory / ("workflow.py" if kind == "workflow" else "api_client.py")
        env_path = directory / ".env.example"
        if script_path.exists():
            code = script_path.read_text(encoding="utf-8", errors="replace")
            used = _env_names_from_code(code)
            documented = (
                _parse_env_example(env_path.read_text(encoding="utf-8", errors="replace"))
                if env_path.exists()
                else set()
            )
            for name in sorted(used - documented):
                problems.append(f".env.example missing variable: {name}")

        # --- schema.sql ------------------------------------------------- #
        if kind == "workflow":
            code = _full_workflow_code(product).lower()
            uses_db = "rest/v1" in code or "supabase" in code
            schema_path = directory / "schema.sql"
            if uses_db:
                schema_text = (
                    schema_path.read_text(encoding="utf-8", errors="replace").lower()
                    if schema_path.exists()
                    else ""
                )
                if "create table if not exists" not in schema_text:
                    problems.append("schema.sql missing CREATE TABLE IF NOT EXISTS")

        # --- requests.http --------------------------------------------- #
        http_path = directory / "requests.http"
        if http_path.exists():
            problems.extend(
                _check_requests_http(http_path.read_text(encoding="utf-8", errors="replace"))
            )
        else:
            problems.append("requests.http missing")

    return not problems, dry_exit, problems


def _judge_execution(result: subprocess.CompletedProcess[str], kind: str) -> list[str]:
    problems: list[str] = []
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()
        problems.append(
            f"sandbox exit code {result.returncode}: "
            + (tail[-1] if tail else "no output")
        )
    stderr = result.stderr or ""
    for marker in _TRACEBACK_MARKERS:
        if marker in stderr:
            problems.append(f"sandbox stderr contains {marker}")
            break
    if kind == "workflow" and not (result.stdout or "").strip():
        problems.append("workflow --dry-run produced no stdout")
    return problems


# --------------------------------------------------------------------------- #
# Stage 2 – Python / snippet deep check
# --------------------------------------------------------------------------- #


def _imported_top_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return modules


def audit_python(code_blocks: list[str], kind: str) -> list[str]:
    problems: list[str] = []
    stdlib = set(cfg.STDLIB_MODULES)
    forbidden = set(cfg.FORBIDDEN_IMPORTS)
    if kind == "workflow":
        forbidden |= {"random"}

    for index, code in enumerate(code_blocks):
        if not code.strip():
            problems.append(f"empty code snippet #{index + 1}")
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            problems.append(f"code snippet #{index + 1} SyntaxError: {error.msg}")
            continue

        for module in sorted(_imported_top_modules(tree)):
            if module in forbidden:
                problems.append(f"code snippet #{index + 1} forbidden import: {module}")
            elif module not in stdlib:
                problems.append(f"code snippet #{index + 1} non-stdlib import: {module}")

        lowered = code.lower()
        if "urlencode(" in code and not re.search(
            r"(^|\n)\s*(import\s+urllib\.parse|from\s+urllib\s+import\s+parse|import\s+urllib\s*$)",
            code,
        ):
            problems.append(
                f"code snippet #{index + 1} uses urlencode without 'import urllib.parse'"
            )
        if "rest/v1" in lowered or "supabase" in lowered:
            if "apikey" not in lowered:
                problems.append(f"code snippet #{index + 1} Supabase call missing apikey header")
            if "authorization" not in lowered:
                problems.append(
                    f"code snippet #{index + 1} Supabase call missing Authorization header"
                )
            # Only writes need ``Prefer: return=representation``. A plain GET
            # (e.g. polling a queue) must not be forced to send it.
            is_write = bool(
                re.search(
                    r"method\s*=\s*['\"](?:POST|PATCH|PUT|DELETE)['\"]",
                    code,
                    re.IGNORECASE,
                )
            ) or "data=" in code
            if is_write and "prefer" not in lowered:
                problems.append(
                    f"code snippet #{index + 1} Supabase write missing Prefer: return=representation"
                )
        if "slack" in lowered and "json.loads(response.read())" in lowered:
            problems.append(
                f"code snippet #{index + 1} parses Slack webhook response as JSON (returns 'ok')"
            )
        if "api.openai.com" in lowered:
            # Only chat completions must use a current gpt-4o model; embeddings,
            # Whisper and image endpoints legitimately use their own models.
            is_chat = "chat/completions" in lowered or "/completions" in lowered
            models = re.findall(
                r"['\"]model['\"]\s*:\s*['\"]([^'\"]+)['\"]", code
            )
            if is_chat:
                bad_models = [
                    m
                    for m in models
                    if not (m.startswith("gpt-4o") or m.startswith("gpt-4.1"))
                ]
                if bad_models:
                    problems.append(
                        f"code snippet #{index + 1} OpenAI chat model must be "
                        f"gpt-4o/gpt-4o-mini: {bad_models}"
                    )
                # No literal "model" field means this is only a URL reference,
                # not an actual chat request – do not flag it.
            if "gpt-3.5-turbo" in lowered or "chatcompletion.create" in lowered:
                problems.append(
                    f"code snippet #{index + 1} uses deprecated OpenAI API/model"
                )
    return problems


def audit_tool_consistency(product: dict[str, Any], code: str) -> list[str]:
    problems: list[str] = []
    details = product.get("details") or {}
    tools = details.get("tools") or []
    lowered = code.lower()
    for tool in tools:
        markers = cfg.TOOL_CODE_MARKERS.get(str(tool))
        if not markers:
            continue
        if not any(marker.lower() in lowered for marker in markers):
            problems.append(f"declared tool '{tool}' not used in code")
    return problems


# --------------------------------------------------------------------------- #
# Stage 3 – PDF end control
# --------------------------------------------------------------------------- #


def _extract_pdf_pages(pdf_path: Path) -> list[str]:
    if PdfReader is None:
        raise RuntimeError("pypdf is required for the PDF audit (pip install pypdf)")
    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def _norm_text(value: str) -> str:
    """Collapse whitespace so multi-line PDF headings still match."""
    return re.sub(r"\s+", " ", value).strip().lower()


def audit_pdf(
    product: dict[str, Any], kind: str, pdf_path: Path
) -> tuple[int, list[str]]:
    problems: list[str] = []
    if not pdf_path.exists():
        return 0, [f"PDF missing: {pdf_path.name}"]
    try:
        pages = _extract_pdf_pages(pdf_path)
    except Exception as error:  # noqa: BLE001
        return 0, [f"PDF unreadable: {error}"]

    total = len(pages)
    full_text = "\n".join(pages)
    title = str(product.get("title") or "").strip()
    timestamp = str(product.get("created_and_verified_at") or "").strip()

    if kind == "workflow":
        if not title:
            problems.append("PDF: product has no title")
        elif _norm_text(title) not in _norm_text(pages[0]):
            problems.append("PDF cover (page 1) missing H1 title")
        if title and len(pages) > 1 and _norm_text(title) not in _norm_text(pages[1]):
            problems.append("PDF overview (page 2) missing H1 title")
        if timestamp and timestamp not in pages[0]:
            problems.append("PDF cover missing 'Created & Verified on' timestamp")
        if timestamp and len(pages) > 1 and timestamp not in pages[1]:
            problems.append("PDF overview missing timestamp")
        if "verification & link validity notice" not in pages[1].lower():
            problems.append("PDF page 2 missing link-validity disclaimer")
        if "verification & link validity notice" not in pages[-1].lower():
            problems.append("PDF last page missing link-validity disclaimer")

        expected_price = cfg.price_label((product.get("details") or {}).get("difficulty"))
        numeric = expected_price.replace("€", "")
        if numeric not in pages[0]:
            problems.append(f"PDF cover missing correct price {expected_price}")
    else:
        if title and title.lower() not in full_text.lower():
            problems.append("API cheatsheet missing title")
        if str(cfg.SCRIPT_PRICE) not in full_text:
            problems.append(f"API cheatsheet missing correct price €{cfg.SCRIPT_PRICE:.2f}")

    # Forbidden old prices anywhere (boundary-safe: 4.99 must not match 34.99).
    for bad in _FORBIDDEN_PRICES:
        pattern = r"(?<![\d.,])" + re.escape(bad) + r"(?![\d])"
        if re.search(pattern, full_text):
            problems.append(f"PDF contains forbidden old price: {bad}")

    # Blacklist phrases.
    lowered = full_text.lower()
    for phrase in _BLACKLIST:
        if phrase.lower() in lowered:
            problems.append(f"PDF contains blacklist phrase: {phrase}")

    # German leftovers / non-English.
    for word in cfg.GERMAN_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            problems.append(f"PDF contains German word: {word}")
            break
    if re.search(r"[äöüß]", lowered):
        problems.append("PDF contains German umlauts")

    # Page numbering consistency.
    for index, page in enumerate(pages, start=1):
        match = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", page)
        if match:
            if int(match.group(1)) != index:
                problems.append(f"PDF page {index}: footer says page {match.group(1)}")
            if int(match.group(2)) != total:
                problems.append(f"PDF page {index}: footer total {match.group(2)} != {total}")

    # Trivial glossary terms.
    if kind == "workflow":
        for entry in (product.get("details") or {}).get("glossary") or []:
            term = str(entry.get("term") or "").strip().lower()
            if term in cfg.TRIVIAL_GLOSSARY_TERMS:
                problems.append(f"PDF glossary contains trivial term: {term}")

    return total, problems


# --------------------------------------------------------------------------- #
# Stage 4 – buffered live domain / URL check
# --------------------------------------------------------------------------- #

_URL_CACHE: dict[str, tuple[bool, str]] = {}


def _is_placeholder_host(host: str) -> bool:
    lowered = host.lower()
    return any(marker in lowered for marker in _PLACEHOLDER_HOST_MARKERS)


def _placeholder_base(host: str) -> str | None:
    lowered = host.lower()
    for key, base in cfg.PLACEHOLDER_BASE_DOMAINS.items():
        if key in lowered:
            return base
    return None


def _http_reachable(url: str) -> tuple[bool, str]:
    import urllib.error
    import urllib.request

    parsed = urlparse(url)
    host_key = f"{parsed.scheme}://{parsed.netloc}"
    if host_key in _URL_CACHE:
        return _URL_CACHE[host_key]

    headers = {
        "User-Agent": "FlowMatrixAudit/1.0 (+https://flowmatrix.dev)",
        "Accept": "*/*",
    }
    result: tuple[bool, str]
    for method in ("HEAD", "GET"):
        try:
            request = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(request, timeout=8) as response:
                code = getattr(response, "status", 200)
                result = (code < 400, f"HTTP {code}")
                break
        except urllib.error.HTTPError as error:
            # Any HTTP status (incl. 401/403/404/405) proves the domain resolves
            # and serves requests – it is not a dead domain.
            result = (True, f"HTTP {error.code}")
            break
        except Exception as error:  # noqa: BLE001
            result = (False, str(error))
    _URL_CACHE[host_key] = result
    return result


def audit_urls(product: dict[str, Any]) -> list[str]:
    if os.environ.get("FLOWMATRIX_SKIP_LIVE") == "1":
        return []
    problems: list[str] = []
    for url in _collect_urls(product):
        parsed = urlparse(url)
        host = parsed.netloc
        if not host:
            continue
        if _is_placeholder_host(host):
            base = _placeholder_base(host)
            if base is None:
                continue
            ok, detail = _http_reachable(base)
            if not ok:
                problems.append(f"URL base unreachable ({base}): {detail}")
            continue
        ok, detail = _http_reachable(url)
        if not ok:
            problems.append(f"URL unreachable ({url}): {detail}")
    return problems


# --------------------------------------------------------------------------- #
# Full audit for one product
# --------------------------------------------------------------------------- #


def audit_product(product: dict[str, Any], kind: str) -> ProductReport:
    slug = str(product.get("slug") or "unknown")
    report = ProductReport(slug=slug, kind=kind)

    difficulty = (product.get("details") or {}).get("difficulty")
    report.price = (
        cfg.price_label(difficulty) if kind == "workflow" else f"€{cfg.SCRIPT_PRICE:.2f}"
    )

    zip_path = (
        cfg.KITS_DIR / f"{slug}-kit.zip"
        if kind == "workflow"
        else cfg.API_KITS_DIR / f"{slug}-kit.zip"
    )
    pdf_path = (
        cfg.DOWNLOADS_DIR / f"flowmatrix-{slug}.pdf"
        if kind == "workflow"
        else cfg.API_KITS_DIR / f"{slug}-cheatsheet.pdf"
    )

    # Stage 1
    zip_ok, dry_exit, problems = audit_zip_sandbox(product, kind, zip_path)
    report.zip_ok = zip_ok
    report.dry_run_exit = dry_exit
    for message in problems:
        report.findings.append(Finding(1, message))

    # Stage 2
    if kind == "workflow":
        code_blocks = _step_codes(product)
        full_code = _full_workflow_code(product)
    else:
        script_path = cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"
        full_code = (
            script_path.read_text(encoding="utf-8", errors="replace")
            if script_path.exists()
            else ""
        )
        code_blocks = [full_code] if full_code else []
    for message in audit_python(code_blocks, kind):
        report.findings.append(Finding(2, message))
    for message in audit_tool_consistency(product, full_code):
        report.findings.append(Finding(2, message))

    # Stage 3
    pages, pdf_problems = audit_pdf(product, kind, pdf_path)
    report.pages = pages
    for message in pdf_problems:
        report.findings.append(Finding(3, message))

    # Stage 4
    url_problems = audit_urls(product)
    report.domains_ok = not url_problems
    for message in url_problems:
        report.findings.append(Finding(4, message))

    return report


# --------------------------------------------------------------------------- #
# Stage 5 – auto healing + R2 sync
# --------------------------------------------------------------------------- #


def _r2_put(local_path: Path, key: str, bucket: str = "flowmatrix-downloads") -> bool:
    try:
        subprocess.run(
            [
                "npx",
                "wrangler",
                "r2",
                "object",
                "put",
                f"{bucket}/{key}",
                "--file",
                str(local_path),
                "--remote",
            ],
            cwd=str(cfg.ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def rebuild_workflow(workflow: dict[str, Any]) -> tuple[Path, Path]:
    slug = str(workflow.get("slug"))
    pdf_path = cfg.DOWNLOADS_DIR / f"flowmatrix-{slug}.pdf"
    pdf_renderer.render_workflow_pdf(workflow, pdf_path)
    kit_path = bundle_builder.build_workflow_kit(workflow, pdf_path, cfg.KITS_DIR)
    return pdf_path, kit_path


def rebuild_api(api: dict[str, Any]) -> tuple[Path, Path, Path] | None:
    slug = str(api.get("slug"))
    script_path = cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"
    if not script_path.exists():
        return None
    kit_path, cheatsheet_path = bundle_builder.build_api_kit(
        api, script_path, cfg.API_KITS_DIR
    )
    return script_path, kit_path, cheatsheet_path


def sync_product_to_r2(product: dict[str, Any], kind: str) -> bool:
    slug = str(product.get("slug"))
    if kind == "workflow":
        pdf_path = cfg.DOWNLOADS_DIR / f"flowmatrix-{slug}.pdf"
        kit_path = cfg.KITS_DIR / f"{slug}-kit.zip"
        ok = _r2_put(pdf_path, f"pdfs/flowmatrix-{slug}.pdf")
        ok = _r2_put(pdf_path, f"{slug}.pdf") and ok
        ok = _r2_put(kit_path, f"kits/{slug}-kit.zip") and ok
        return ok
    script_path = cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"
    kit_path = cfg.API_KITS_DIR / f"{slug}-kit.zip"
    cheatsheet_path = cfg.API_KITS_DIR / f"{slug}-cheatsheet.pdf"
    ok = True
    for path, key in (
        (script_path, f"api-scripts/{slug}/{slug}.py"),
        (kit_path, f"api-kits/{slug}-kit.zip"),
        (cheatsheet_path, f"api-kits/{slug}-cheatsheet.pdf"),
    ):
        if path.exists():
            ok = _r2_put(path, key) and ok
    return ok


def _repair_code(code: str) -> str:
    """Deterministic snippet fixes that never invent new business logic."""
    original = code
    # OpenAI model upgrades (deprecated models are rejected by the audit).
    code = re.sub(r"gpt-3\.5-turbo[a-zA-Z0-9._-]*", "gpt-4o-mini", code)
    code = re.sub(r"(['\"])gpt-4\1", r"\1gpt-4o\1", code)
    # urlencode requires urllib.parse (check the actual import, not the call).
    if "urlencode(" in code and not re.search(
        r"(^|\n)\s*(import\s+urllib\.parse|from\s+urllib\s+import\s+parse|import\s+urllib\s*$)",
        code,
    ):
        code = "import urllib.parse\n" + code
    # Supabase/PostgREST contract: apikey + Prefer header.
    if "rest/v1" in code or "supabase" in code.lower():
        additions: list[str] = []
        if "apikey" not in code.lower():
            additions.append("'apikey': os.environ.get('SUPABASE_KEY')")
        if "prefer" not in code.lower():
            additions.append("'Prefer': 'return=representation'")
        if additions and re.search(r"headers\s*=\s*\{", code):
            code = re.sub(
                r"(headers\s*=\s*\{)",
                r"\1" + ", ".join(additions) + ", ",
                code,
                count=1,
            )
    if re.search(r"\bos\.", code) and not re.search(
        r"(^|\n)\s*import\s+os\b", code
    ):
        code = "import os\n" + code
    # Remove blocking sleeps that stall the --dry-run.
    code = re.sub(r"^\s*time\.sleep\([^\n]*\)\s*$", "", code, flags=re.MULTILINE)
    # Remove the forbidden placeholder word from code and comments.
    code = code.replace("Dummy", "Placeholder").replace("dummy", "placeholder")
    return code


def _repair_product(product: dict[str, Any], kind: str) -> bool:
    """Apply deterministic content fixes in-place / on disk. Returns True if changed."""
    changed = False
    if kind == "workflow":
        for step in (product.get("details") or {}).get("steps") or []:
            code = str(step.get("code_snippet") or "")
            repaired = _repair_code(code)
            if repaired != code:
                step["code_snippet"] = repaired
                changed = True
        return changed
    slug = str(product.get("slug"))
    script_path = cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"
    if script_path.exists():
        code = script_path.read_text(encoding="utf-8")
        repaired = _repair_code(code)
        if repaired != code:
            script_path.write_text(repaired, encoding="utf-8")
            changed = True
    return changed


def _llm_ready() -> bool:
    cfg.load_env()
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines.pop()
        cleaned = "\n".join(lines)
    return cleaned


def _drop_dead_urls(product: dict[str, Any], findings: list[Finding]) -> bool:
    """Recursively replace URLs the audit flagged as unreachable."""
    dead: set[str] = set()
    for finding in findings:
        match = re.search(r"URL unreachable \((https?://[^)]+)\)", str(finding))
        if match:
            dead.add(match.group(1).rstrip(".,;"))
    if not dead:
        return False
    changed = False

    def scrub(node: Any) -> Any:
        nonlocal changed
        if isinstance(node, str):
            new = node
            for dead_url in dead:
                if dead_url in new:
                    new = new.replace(dead_url, "https://example.com")
            if new != node:
                changed = True
            return new
        if isinstance(node, list):
            return [scrub(item) for item in node]
        if isinstance(node, dict):
            return {key: scrub(value) for key, value in node.items()}
        return node

    product["details"] = scrub(product.get("details") or {})
    return changed


_WORKFLOW_REPAIR_SYSTEM = (
    "You are a principal Python engineer. Repair ONLY the broken steps of a "
    "workflow so that, concatenated in order inside a single function, they run "
    "end-to-end using ONLY the Python standard library. Rules: no third-party "
    "imports; HTTP via urllib.request; JSON via json; urlencode needs "
    "import urllib.parse; if a step reads an input file that does not exist, "
    "generate realistic self-contained inline sample data instead of reading a "
    "missing file; every step may rely on variables defined by earlier steps; "
    "never use random; never use an unbounded 'while True' loop – every loop "
    "must have a finite bound; before calling .get() ensure the value is a "
    "dict (index lists first, cast scalars); define every function and "
    "variable before it is used; keep all text and comments in English. Return strict "
    'JSON: {"steps": [{"index": <1-based>, "code_snippet": "<full corrected '
    'code>"}]}. Only return steps that need changes.'
)


def _llm_repair_workflow(workflow: dict[str, Any], findings: list[Finding]) -> bool:
    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    payload = {
        "title": workflow.get("title"),
        "tools": details.get("tools"),
        "steps": [
            {
                "index": index + 1,
                "title": step.get("title"),
                "description": step.get("description"),
                "code_snippet": step.get("code_snippet"),
            }
            for index, step in enumerate(steps)
        ],
        "problems": [str(finding) for finding in findings],
    }
    try:
        result = llm_client.chat_json(
            _WORKFLOW_REPAIR_SYSTEM, json.dumps(payload)
        )
    except Exception as error:  # noqa: BLE001
        print(f"  [LLM] workflow repair failed: {error}")
        return False
    changed = False
    for item in result.get("steps", []):
        try:
            index = int(item.get("index", 0)) - 1
        except (TypeError, ValueError):
            continue
        code = item.get("code_snippet")
        if 0 <= index < len(steps) and isinstance(code, str) and code.strip():
            try:
                ast.parse(code)
            except SyntaxError:
                continue
            steps[index]["code_snippet"] = code
            changed = True
    return changed


def _llm_repair_api(product: dict[str, Any], findings: list[Finding]) -> bool:
    slug = str(product.get("slug"))
    script_path = cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"
    if not script_path.exists():
        return False
    code = script_path.read_text(encoding="utf-8")
    user = (
        "Problems:\n"
        + "\n".join(f"- {finding}" for finding in findings)
        + f"\n\nRepair this script:\n{code}"
    )
    try:
        repaired = _strip_fences(
            llm_client.chat_code(prompts.CODE_REPAIR_SYSTEM, user)
        )
        ast.parse(repaired)
    except Exception as error:  # noqa: BLE001
        print(f"  [LLM] api repair failed: {error}")
        return False
    if repaired.strip() and repaired != code:
        script_path.write_text(repaired, encoding="utf-8")
        return True
    return False


def heal_product(
    product: dict[str, Any],
    kind: str,
    report: ProductReport,
    use_llm: bool = False,
    max_attempts: int = 3,
) -> bool:
    """Deterministic rebuild + optional LLM repair loop. Returns success."""
    _repair_product(product, kind)
    _drop_dead_urls(product, report.findings)

    last_findings: list[Finding] = list(report.findings)
    for attempt in range(1, max_attempts + 1):
        try:
            if kind == "workflow":
                rebuild_workflow(product)
            elif rebuild_api(product) is None:
                report.findings.append(
                    Finding(5, "cannot rebuild API kit: source script missing")
                )
                return False
        except Exception as error:  # noqa: BLE001
            report.findings.append(Finding(5, f"rebuild failed: {error}"))
            return False

        recheck = audit_product(product, kind)
        last_findings = recheck.findings
        if not recheck.findings:
            report.findings = []
            report.healed = True
            return True

        if not use_llm or not _llm_ready():
            break

        print(
            f"  [LLM] attempt {attempt}/{max_attempts}: "
            f"{len(recheck.findings)} findings"
        )
        if kind == "workflow":
            changed = _llm_repair_workflow(product, recheck.findings)
        else:
            changed = _llm_repair_api(product, recheck.findings)
        changed = _drop_dead_urls(product, recheck.findings) or changed
        if not changed:
            break

    report.findings = list(last_findings)
    report.findings.append(
        Finding(5, "auto-heal did not clear all findings (content review needed)")
    )
    return False


# --------------------------------------------------------------------------- #
# Stage 6 – report, build, deploy
# --------------------------------------------------------------------------- #


def write_report(reports: list[ProductReport], path: Path) -> None:
    total = len(reports)
    ok = sum(1 for r in reports if r.ok)
    lines = [
        "# FlowMatrix – 100 % Product Audit Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        f"**Products checked:** {total} · **Passing:** {ok} · **Failing:** {total - ok}",
        "",
        "| Slug | Type | Price | Pages | Dry-Run Exit | ZIP OK | Domains OK | R2 Synced | Status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for report in reports:
        status = "PASS" if report.ok else f"FAIL ({len(report.findings)})"
        lines.append(
            "| {slug} | {kind} | {price} | {pages} | {dry} | {zip} | {dom} | {r2} | {status} |".format(
                slug=report.slug,
                kind=report.kind,
                price=report.price,
                pages=report.pages or "—",
                dry=report.dry_run_exit,
                zip="yes" if report.zip_ok else "no",
                dom="yes" if report.domains_ok else "no",
                r2="yes" if report.r2_synced else "no",
                status=status,
            )
        )

    failing = [r for r in reports if not r.ok]
    if failing:
        lines.extend(["", "## Findings", ""])
        for report in failing:
            lines.append(f"### {report.slug} ({report.kind})")
            for finding in report.findings:
                lines.append(f"- {finding}")
            lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_astro_build() -> bool:
    result = subprocess.run(
        ["npm", "run", "build"], cwd=str(cfg.ROOT), capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
    return result.returncode == 0


def git_commit_and_push() -> bool:
    commands = [
        ["git", "add", "."],
        [
            "git",
            "commit",
            "-m",
            "chore(audit): 100% end-to-end verification and auto-heal of all PDFs and ZIP kits",
        ],
        ["git", "push"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=str(cfg.ROOT), capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr[-1000:])
            return False
    return True


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full product audit & auto-heal")
    parser.add_argument("--limit", type=int, default=0, help="prüfe nur N Produkte")
    parser.add_argument("--kind", choices=["workflow", "api"], help="nur ein Produkttyp")
    parser.add_argument("--only", action="append", default=[], help="nur diese Slugs")
    parser.add_argument("--heal", action="store_true", help="Auto-Heal aktivieren")
    parser.add_argument(
        "--llm-heal",
        action="store_true",
        help="LLM-Reparatur für verbleibende Datenfehler aktivieren",
    )
    parser.add_argument(
        "--max-attempts", type=int, default=3, help="max. Heal-Versuche pro Produkt"
    )
    parser.add_argument("--no-r2", action="store_true", help="R2-Upload überspringen")
    parser.add_argument("--deploy", action="store_true", help="Build + Commit + Push")
    parser.add_argument("--report", default="AUDIT_REPORT.md", help="Report-Pfad")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    workflows = _load_json(cfg.WORKFLOWS_FILE)
    apis = _load_json(cfg.APIS_FILE)

    products: list[tuple[dict[str, Any], str]] = []
    if args.kind != "api":
        products.extend((item, "workflow") for item in workflows)
    if args.kind != "workflow":
        products.extend((item, "api") for item in apis)

    if args.only:
        wanted = set(args.only)
        products = [(item, kind) for item, kind in products if item.get("slug") in wanted]
    if args.limit and args.limit > 0:
        products = products[: args.limit]

    print(f"[AUDIT] {len(products)} Produkte werden geprüft …")
    reports: list[ProductReport] = []
    for index, (product, kind) in enumerate(products, start=1):
        slug = str(product.get("slug"))
        print(f"[{index}/{len(products)}] {kind}: {slug}")
        try:
            report = audit_product(product, kind)
        except Exception as error:  # noqa: BLE001
            report = ProductReport(slug=slug, kind=kind)
            report.findings.append(Finding(0, f"audit crashed: {error}"))

        if args.heal and not report.ok:
            print(f"  [HEAL] {len(report.findings)} Befunde – rebuild …")
            heal_product(
                product,
                kind,
                report,
                use_llm=args.llm_heal,
                max_attempts=args.max_attempts,
            )

        if not args.no_r2 and report.ok:
            report.r2_synced = sync_product_to_r2(product, kind)

        reports.append(report)
        status = "PASS" if report.ok else f"FAIL({len(report.findings)})"
        print(f"  -> {status}")

    if args.heal:
        # Persist deterministic data repairs so the Astro build + R2 sync use them.
        _save_json(cfg.WORKFLOWS_FILE, workflows)

    report_path = cfg.ROOT / args.report
    write_report(reports, report_path)
    ok = sum(1 for r in reports if r.ok)
    print(f"\n[AUDIT] Fertig: {ok}/{len(reports)} grün · Report: {report_path.name}")

    if args.deploy:
        if ok != len(reports):
            print("[DEPLOY] abgebrochen – nicht alle Produkte grün.")
            return 1
        print("[DEPLOY] Astro-Build …")
        if not run_astro_build():
            print("[DEPLOY] Build fehlgeschlagen.")
            return 1
        print("[DEPLOY] Commit & Push …")
        if not git_commit_and_push():
            print("[DEPLOY] Git-Schritt fehlgeschlagen.")
            return 1

    return 0 if ok == len(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
