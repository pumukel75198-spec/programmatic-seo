#!/usr/bin/env python3
"""Inhaltliches Qualitäts-Audit für alle Workflows (PDFs + Kits).

Dieses Audit prüft NICHT nur die technische Lauffähigkeit (das macht
``product_gate.py``), sondern die **inhaltliche Substanz** und die
**didaktische Zielführung** jedes Workflows:

* Ist die Schrittfolge vollständig und logisch aufgebaut?
* Enthält jeder Schritt echten, lauffähigen Code mit realem Datenfluss?
* Erklärt jeder Schritt Architektur, API-Vertrag und Edge-Cases?
* Führen Glossar, Troubleshooting und Checklisten wirklich zum Ziel?
* Passen Tools, Code und Ressourcen zusammen?
* Ist das gelieferte Kit lauffähig und das PDF inhaltlich vollständig?

Ergebnis: ``pipeline/CONTENT_QUALITY_REPORT.md`` (Markdown) und optional
``pipeline/content_quality_report.json`` (maschinenlesbar).

Aufruf::

    .venv/bin/python -m pipeline.content_quality_audit
    .venv/bin/python -m pipeline.content_quality_audit --only <slug>
    .venv/bin/python -m pipeline.content_quality_audit --skip-kits --skip-pdfs
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
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as cfg

try:  # PDF-Text (optional, wie in full_product_audit.py)
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Ergebnis-Modell
# --------------------------------------------------------------------------- #
SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}


@dataclass
class Finding:
    severity: str  # critical | major | minor | info
    area: str  # struktur | code | didaktik | tools | kit | pdf
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.area}: {self.message}"


@dataclass
class WorkflowReport:
    slug: str
    title: str
    difficulty: str = ""
    steps: int = 0
    code_lines: int = 0
    explanation_chars: int = 0
    kit_ok: bool | None = None
    kit_dry_run: str = "—"
    pdf_pages: int = 0
    score: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(
            finding.severity in ("critical", "major") for finding in self.findings
        )

    def add(self, severity: str, area: str, message: str) -> None:
        self.findings.append(Finding(severity, area, message))


# --------------------------------------------------------------------------- #
# Hilfsfunktionen
# --------------------------------------------------------------------------- #
_PLACEHOLDER_RE = re.compile(
    r"YOUR_[A-Z0-9_]+|<YOUR[^>]*>|example\.com|lorem ipsum|\bdummy\b|"
    r"\bplaceholder\b|TODO|FIXME|realistic fallback",
    re.IGNORECASE,
)
_API_CALL_RE = re.compile(
    r"urllib\.request\.(?:urlopen|Request)|http\.client\.HTTPSConnection|"
    r"urllib\.request\.urlopen",
)
_GENERIC_NAMES = frozenset(
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


def _non_empty_lines(code: str) -> int:
    return len([line for line in str(code or "").splitlines() if line.strip()])


def _module_level_names(code: str) -> set[str]:
    """Modul-Level-Variablen/Funktionen, die ein Step an den nächsten übergibt."""
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


def _meaningful(names: set[str]) -> set[str]:
    return {
        name
        for name in names
        if name not in _GENERIC_NAMES and not name.startswith("_")
    }


def _imported_modules(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def _tool_markers(tool: str) -> tuple[str, ...]:
    return cfg.TOOL_CODE_MARKERS.get(tool, (tool.lower(),))


def _pdf_pages(path: Path) -> list[str]:
    if PdfReader is None or not path.exists():
        return []
    try:
        reader = PdfReader(str(path))
        return [(page.extract_text() or "") for page in reader.pages]
    except Exception:  # noqa: BLE001
        return []


def _pdf_page_count_fallback(path: Path) -> int:
    try:
        return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))
    except Exception:  # noqa: BLE001
        return 0


# --------------------------------------------------------------------------- #
# Einzelne Prüfbereiche
# --------------------------------------------------------------------------- #
def audit_structure(workflow: dict[str, Any], report: WorkflowReport) -> None:
    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    report.steps = len(steps)

    if not (cfg.MIN_STEPS <= len(steps) <= cfg.MAX_STEPS):
        report.add(
            "critical",
            "struktur",
            f"{len(steps)} Steps (erwartet {cfg.MIN_STEPS}–{cfg.MAX_STEPS})",
        )

    prerequisites = details.get("prerequisites") or []
    if len(prerequisites) < cfg.PREREQUISITES_MIN:
        report.add(
            "major",
            "struktur",
            f"nur {len(prerequisites)} Prerequisites (min {cfg.PREREQUISITES_MIN})",
        )
    if not any(
        str(item).strip() == cfg.FINAL_PREREQUISITE for item in prerequisites
    ):
        report.add(
            "major",
            "struktur",
            "verbindliches Python-Prerequisite fehlt",
        )

    glossary = details.get("glossary") or []
    if len(glossary) < cfg.GLOSSARY_TERMS_MIN:
        report.add(
            "major",
            "struktur",
            f"nur {len(glossary)} Glossar-Einträge (min {cfg.GLOSSARY_TERMS_MIN})",
        )
    for entry in glossary:
        term = str(entry.get("term") or "").strip().lower()
        if term in cfg.TRIVIAL_GLOSSARY_TERMS:
            report.add("minor", "struktur", f"trivialer Glossar-Begriff: {term}")

    troubleshooting = details.get("troubleshooting") or []
    if len(troubleshooting) < cfg.TROUBLESHOOTING_MIN:
        report.add(
            "major",
            "struktur",
            f"nur {len(troubleshooting)} Troubleshooting-Einträge "
            f"(min {cfg.TROUBLESHOOTING_MIN})",
        )

    resources = details.get("resources") or []
    if not resources:
        report.add("major", "struktur", "keine Resources hinterlegt")
    for resource in resources:
        url = str(resource.get("url") or "")
        if not url.startswith(("http://", "https://")):
            report.add(
                "major",
                "struktur",
                f"Resource '{resource.get('label')}' hat keine vollständige URL",
            )

    if not str(workflow.get("created_and_verified_at") or "").strip():
        report.add("major", "struktur", "created_and_verified_at fehlt")


def audit_steps(workflow: dict[str, Any], report: WorkflowReport) -> None:
    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    tools = [str(tool) for tool in (details.get("tools") or [])]
    api_tools = [
        tool
        for tool in tools
        if tool.lower()
        not in {"python standard library", "standard library", "none", "null", ""}
    ]

    previous_assigned: set[str] = set()
    total_code_lines = 0
    total_explanation = 0

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            report.add("critical", "code", f"Step {index} ist kein Objekt")
            continue
        context = f"Step {index}"

        code = str(step.get("code_snippet") or "")
        lines = _non_empty_lines(code)
        total_code_lines += lines
        if lines < cfg.MIN_CODE_LINES:
            report.add(
                "critical",
                "code",
                f"{context}: nur {lines} Code-Zeilen (min {cfg.MIN_CODE_LINES})",
            )

        # AST + stdlib
        try:
            ast.parse(code, feature_version=(3, 10))
        except SyntaxError as error:
            report.add(
                "critical",
                "code",
                f"{context}: SyntaxError: {error.msg} (Zeile {error.lineno})",
            )
        else:
            forbidden = set(cfg.FORBIDDEN_IMPORTS) | {"random"}
            for module in sorted(_imported_modules(code)):
                if module in forbidden:
                    report.add(
                        "critical", "code", f"{context}: verbotener Import '{module}'"
                    )
                elif module not in cfg.STDLIB_MODULES:
                    report.add(
                        "major", "code", f"{context}: Nicht-stdlib Import '{module}'"
                    )

        # Platzhalter / Dummy
        if _PLACEHOLDER_RE.search(code):
            match = _PLACEHOLDER_RE.search(code)
            report.add(
                "critical",
                "code",
                f"{context}: Platzhalter/Dummy im Code ('{match.group(0)}')",
            )

        # Echter API-Aufruf, wenn der Step ein API-Tool deklariert
        step_tools = [
            str(tool)
            for tool in (step.get("tools") or [])
            if str(tool).lower()
            not in {"python standard library", "standard library", "none", "null", ""}
        ]
        if step_tools and not _API_CALL_RE.search(code):
            report.add(
                "major",
                "code",
                f"{context}: deklariert Tool(s) {step_tools}, aber kein echter "
                "HTTP-Aufruf (urllib.request/http.client) im Code",
            )

        # Didaktik
        explanation = str(step.get("technical_explanation") or "")
        total_explanation += len(explanation)
        if len(explanation) < cfg.MIN_TECHNICAL_EXPLANATION:
            report.add(
                "major",
                "didaktik",
                f"{context}: technische Erklärung zu kurz "
                f"({len(explanation)} < {cfg.MIN_TECHNICAL_EXPLANATION} Zeichen)",
            )
        actions = step.get("actions") or []
        if len(actions) < 3:
            report.add(
                "major", "didaktik", f"{context}: nur {len(actions)} Actions (min 3)"
            )
        checklist = step.get("checklist") or []
        if len(checklist) < 2:
            report.add(
                "major",
                "didaktik",
                f"{context}: nur {len(checklist)} Checklist-Punkte (min 2)",
            )
        if not str(step.get("expectedResult") or "").strip():
            report.add("major", "didaktik", f"{context}: expectedResult fehlt")
        links = step.get("links") or []
        if not links:
            report.add("major", "didaktik", f"{context}: keine Links")
        for link in links:
            url = str(link.get("url") or "")
            if not url.startswith(("http://", "https://")):
                report.add(
                    "major",
                    "didaktik",
                    f"{context}: Link '{link.get('label')}' hat keine vollständige URL",
                )

        # Datenfluss: Step > 1 muss eine sinnvolle Variable aus früheren Steps lesen
        if index > 1 and previous_assigned:
            consumed = _meaningful(_loaded_names(code)) & previous_assigned
            if not consumed:
                report.add(
                    "major",
                    "code",
                    f"{context}: konsumiert keine Variable aus früheren Steps "
                    "(Datenfluss unklar)",
                )
        previous_assigned |= _meaningful(_module_level_names(code))

    report.code_lines = total_code_lines
    report.explanation_chars = total_explanation

    # Tool-Konsistenz über den gesamten Workflow
    full_code = "\n".join(
        str(step.get("code_snippet") or "") for step in steps
    ).lower()
    full_text = json.dumps(steps, ensure_ascii=False).lower()
    resource_labels = {
        str(entry.get("label") or "").strip().lower()
        for entry in (details.get("resources") or [])
    }
    for tool in api_tools:
        markers = _tool_markers(tool)
        if not any(marker.lower() in full_text for marker in markers):
            report.add(
                "major",
                "tools",
                f"Tool '{tool}' wird in keinem Step verwendet",
            )
        if tool.lower() not in resource_labels:
            report.add(
                "major",
                "tools",
                f"Tool '{tool}' hat keinen Resource-Eintrag",
            )


def audit_kit(workflow: dict[str, Any], report: WorkflowReport) -> None:
    slug = str(workflow.get("slug") or "")
    kit_path = cfg.KITS_DIR / f"{slug}-kit.zip"
    if not kit_path.exists():
        report.add("critical", "kit", f"Kit fehlt: {kit_path.name}")
        report.kit_ok = False
        return

    try:
        with zipfile.ZipFile(kit_path) as archive:
            names = set(archive.namelist())
            bad = archive.testzip()
            if bad is not None:
                report.add("critical", "kit", f"ZIP defekt: {bad}")
            for required in cfg.WORKFLOW_KIT_FILES:
                if required not in names:
                    report.add("critical", "kit", f"Pflichtdatei fehlt: {required}")
                else:
                    info = archive.getinfo(required)
                    if info.file_size <= 100:
                        report.add(
                            "major",
                            "kit",
                            f"Datei '{required}' ist nur {info.file_size} Bytes",
                        )
    except zipfile.BadZipFile as error:
        report.add("critical", "kit", f"ZIP nicht lesbar: {error}")
        report.kit_ok = False
        return

    # Dry-Run des gelieferten workflow.py
    try:
        with tempfile.TemporaryDirectory(prefix="fm-quality-") as tmp:
            with zipfile.ZipFile(kit_path) as archive:
                archive.extractall(tmp)
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            try:
                result = subprocess.run(
                    [sys.executable, "workflow.py", "--dry-run"],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                report.add("critical", "kit", "workflow.py --dry-run Timeout (30s)")
                report.kit_ok = False
                report.kit_dry_run = "timeout"
                return
            report.kit_dry_run = str(result.returncode)
            output = f"{result.stdout}\n{result.stderr}"
            if result.returncode != 0:
                tail = output.strip().splitlines()[-1] if output.strip() else "—"
                report.add(
                    "critical",
                    "kit",
                    f"workflow.py --dry-run Exit {result.returncode}: {tail}",
                )
                report.kit_ok = False
            elif "Traceback (most recent call last)" in output:
                report.add(
                    "critical", "kit", "workflow.py --dry-run enthält Traceback"
                )
                report.kit_ok = False
            elif "Dry-run completed successfully." not in result.stdout:
                report.add(
                    "major",
                    "kit",
                    "workflow.py --dry-run meldet keinen Erfolg",
                )
                report.kit_ok = False
            else:
                report.kit_ok = True
    except Exception as error:  # noqa: BLE001
        report.add("critical", "kit", f"Kit-Dry-Run Fehler: {error}")
        report.kit_ok = False


def audit_pdf(workflow: dict[str, Any], report: WorkflowReport) -> None:
    slug = str(workflow.get("slug") or "")
    pdf_path = cfg.DOWNLOADS_DIR / f"flowmatrix-{slug}.pdf"
    if not pdf_path.exists():
        report.add("critical", "pdf", f"PDF fehlt: {pdf_path.name}")
        return

    pages = _pdf_pages(pdf_path)
    if pages:
        report.pdf_pages = len(pages)
    else:
        report.pdf_pages = _pdf_page_count_fallback(pdf_path)

    if report.pdf_pages < 2:
        report.add(
            "critical", "pdf", f"PDF hat nur {report.pdf_pages} Seite(n)"
        )
        return

    if not pages:
        report.add(
            "minor",
            "pdf",
            "PDF-Text nicht extrahierbar (pypdf fehlt) – nur Seitenzahl geprüft",
        )
        return

    full_text = "\n".join(pages)
    title = str(workflow.get("title") or "").strip()
    timestamp = str(workflow.get("created_and_verified_at") or "").strip()
    difficulty = (workflow.get("details") or {}).get("difficulty")
    price = cfg.price_label(difficulty)

    def norm(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().lower()

    if title and norm(title) not in norm(pages[0]):
        report.add("major", "pdf", "Titel fehlt auf dem Cover (Seite 1)")
    if title and len(pages) > 1 and norm(title) not in norm(pages[1]):
        report.add("major", "pdf", "Titel fehlt auf der Übersicht (Seite 2)")
    if timestamp and timestamp not in pages[0]:
        report.add("major", "pdf", "Timestamp fehlt auf dem Cover")
    if price.replace("€", "") not in pages[0]:
        report.add("major", "pdf", f"Preis {price} fehlt auf dem Cover")
    if "verification & link validity notice" not in full_text.lower():
        report.add("major", "pdf", "Link-Validitäts-Disclaimer fehlt")

    # Jeder Step-Titel sollte im PDF auftauchen
    for index, step in enumerate(
        (workflow.get("details") or {}).get("steps") or [], start=1
    ):
        step_title = str(step.get("title") or "").strip()
        if step_title and norm(step_title) not in norm(full_text):
            report.add(
                "major", "pdf", f"Step {index}-Titel fehlt im PDF: '{step_title}'"
            )

    # Seitenzahlen
    for index, page in enumerate(pages, start=1):
        match = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", page)
        if match:
            if int(match.group(1)) != index:
                report.add(
                    "minor",
                    "pdf",
                    f"Seite {index}: Footer sagt Seite {match.group(1)}",
                )
            if int(match.group(2)) != len(pages):
                report.add(
                    "minor",
                    "pdf",
                    f"Seite {index}: Footer-Total {match.group(2)} != {len(pages)}",
                )


# --------------------------------------------------------------------------- #
# Score
# --------------------------------------------------------------------------- #
def compute_score(report: WorkflowReport) -> int:
    score = 100
    for finding in report.findings:
        if finding.severity == "critical":
            score -= 15
        elif finding.severity == "major":
            score -= 6
        elif finding.severity == "minor":
            score -= 2
    return max(0, score)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def _write_markdown(reports: list[WorkflowReport], path: Path) -> None:
    total = len(reports)
    ok = sum(1 for report in reports if report.ok)
    critical = sum(
        1
        for report in reports
        if any(f.severity == "critical" for f in report.findings)
    )
    avg_score = round(sum(r.score for r in reports) / total, 1) if total else 0

    lines = [
        "# Content Quality Report – Workflows (PDFs + Kits)",
        "",
        f"**Workflows geprüft:** {total} · **Inhaltlich OK:** {ok} · "
        f"**Mit kritischen Findings:** {critical} · **Ø Score:** {avg_score}/100",
        "",
        "## Übersicht",
        "",
        "| Slug | Difficulty | Steps | Code-Zeilen | Erklärung | Kit | PDF | Score | Status |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for report in sorted(reports, key=lambda r: (r.score, r.slug)):
        kit = (
            "—"
            if report.kit_ok is None
            else ("OK" if report.kit_ok else f"FAIL({report.kit_dry_run})")
        )
        status = "PASS" if report.ok else "FAIL"
        lines.append(
            f"| {report.slug} | {report.difficulty} | {report.steps} | "
            f"{report.code_lines} | {report.explanation_chars} | {kit} | "
            f"{report.pdf_pages} | {report.score} | {status} |"
        )

    failing = [r for r in reports if r.findings]
    if failing:
        lines.extend(["", "## Findings", ""])
        for report in sorted(failing, key=lambda r: (r.score, r.slug)):
            lines.append(f"### {report.slug} ({report.score}/100)")
            for finding in sorted(
                report.findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 9)
            ):
                lines.append(f"- {finding}")
            lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(reports: list[WorkflowReport], path: Path) -> None:
    payload = [
        {
            "slug": report.slug,
            "title": report.title,
            "difficulty": report.difficulty,
            "steps": report.steps,
            "code_lines": report.code_lines,
            "explanation_chars": report.explanation_chars,
            "kit_ok": report.kit_ok,
            "kit_dry_run": report.kit_dry_run,
            "pdf_pages": report.pdf_pages,
            "score": report.score,
            "ok": report.ok,
            "findings": [
                {
                    "severity": finding.severity,
                    "area": finding.area,
                    "message": finding.message,
                }
                for finding in report.findings
            ],
        }
        for report in reports
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inhaltliches Qualitäts-Audit für Workflows (PDFs + Kits)"
    )
    parser.add_argument("--only", action="append", default=[], help="Slug (wiederholbar)")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-kits", action="store_true")
    parser.add_argument("--skip-pdfs", action="store_true")
    parser.add_argument(
        "--report", default="pipeline/CONTENT_QUALITY_REPORT.md"
    )
    parser.add_argument("--json-report", default="pipeline/content_quality_report.json")
    args = parser.parse_args(argv)

    workflows = json.loads(cfg.WORKFLOWS_FILE.read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only)
        workflows = [w for w in workflows if w.get("slug") in wanted]
    if args.limit and args.limit > 0:
        workflows = workflows[: args.limit]

    reports: list[WorkflowReport] = []
    for index, workflow in enumerate(workflows, start=1):
        slug = str(workflow.get("slug") or "unknown")
        print(f"[{index}/{len(workflows)}] {slug}")
        report = WorkflowReport(
            slug=slug,
            title=str(workflow.get("title") or ""),
            difficulty=str((workflow.get("details") or {}).get("difficulty") or ""),
        )
        try:
            audit_structure(workflow, report)
            audit_steps(workflow, report)
            if not args.skip_kits:
                audit_kit(workflow, report)
            if not args.skip_pdfs:
                audit_pdf(workflow, report)
        except Exception as error:  # noqa: BLE001 - Audit darf nie abbrechen
            report.add("critical", "struktur", f"Audit-Fehler: {error}")
        report.score = compute_score(report)
        reports.append(report)
        status = "PASS" if report.ok else "FAIL"
        print(f"  -> {status} ({report.score}/100, {len(report.findings)} Findings)")

    report_path = cfg.ROOT / args.report
    json_path = cfg.ROOT / args.json_report
    _write_markdown(reports, report_path)
    _write_json(reports, json_path)

    ok = sum(1 for report in reports if report.ok)
    print(
        f"\n[QUALITY] {ok}/{len(reports)} inhaltlich OK · "
        f"Report: {report_path}"
    )
    return 0 if ok == len(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
