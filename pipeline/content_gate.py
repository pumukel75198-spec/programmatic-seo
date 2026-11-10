"""Recurring content gate for every stored workflow and API script.

Why this exists
---------------
``validator.py`` only runs when a record is generated or repaired. Records that
passed an older validator stay in ``src/data/*.json`` forever and are never
re-checked. When the validator gains a new rule, that drift is invisible until
someone runs the product gate – which is exactly how dozens of broken records
accumulated over weeks.

This module closes that gap: it re-validates **every stored record** on demand
and in CI. A single failure exits non-zero, so a stale record can never be
merged or deployed silently again.

Live link checks are **off by default**. The site disclaimer states that links
are only guaranteed to be reachable on the day of generation; afterwards link
rot is expected and must not block a deploy. Pass ``--live`` to opt in.

Usage::

    python -m pipeline.content_gate                 # structural checks only
    python -m pipeline.content_gate --live          # also check live domains
    python -m pipeline.content_gate --only-workflow <slug>
    python -m pipeline.content_gate --json-report pipeline/content_gate_report.json
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as cfg
from . import validator


@dataclass
class GateItem:
    slug: str
    kind: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _api_script_path(slug: str) -> Path:
    return cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"


def collect_workflows(only: list[str]) -> list[dict[str, Any]]:
    workflows = _load(cfg.WORKFLOWS_FILE)
    if only:
        wanted = set(only)
        workflows = [item for item in workflows if item.get("slug") in wanted]
    return workflows


def collect_apis(only: list[str]) -> list[dict[str, Any]]:
    apis = _load(cfg.APIS_FILE)
    if only:
        wanted = set(only)
        apis = [item for item in apis if item.get("slug") in wanted]
    return apis


def check_workflow(workflow: dict[str, Any]) -> GateItem:
    slug = str(workflow.get("slug") or "unknown")
    item = GateItem(slug=slug, kind="workflow")
    try:
        result = validator.validate_workflow(workflow)
        item.ok = result.ok
        item.errors = list(result.errors)
        item.warnings = list(result.warnings)
    except Exception as error:  # noqa: BLE001 - a crash is a hard failure
        item.ok = False
        item.errors = [f"validator crashed: {type(error).__name__}: {error}"]
    return item


def check_api(api: dict[str, Any]) -> GateItem:
    slug = str(api.get("slug") or "unknown")
    item = GateItem(slug=slug, kind="api")
    script_path = _api_script_path(slug)
    if not script_path.exists():
        item.ok = False
        item.errors = [f"API script missing: {script_path}"]
        return item
    try:
        script = script_path.read_text(encoding="utf-8")
        result = validator.validate_api_script(script)
        item.ok = result.ok
        item.errors = list(result.errors)
        item.warnings = list(result.warnings)
    except Exception as error:  # noqa: BLE001 - a crash is a hard failure
        item.ok = False
        item.errors = [f"validator crashed: {type(error).__name__}: {error}"]
    return item


def _write_markdown(items: list[GateItem], path: Path, live: bool) -> None:
    failing = [item for item in items if not item.ok]
    lines = [
        "# Content Gate Report",
        "",
        f"Records checked: {len(items)} · Passing: {len(items) - len(failing)} · "
        f"Failing: {len(failing)}",
        "",
        f"Live link checks: {'on' if live else 'off (generation-day only)'}",
        "",
        "| Slug | Kind | Status | Findings |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        findings = "<br>".join(item.errors) or "—"
        lines.append(
            f"| {item.slug} | {item.kind} | "
            f"{'PASS' if item.ok else 'FAIL'} | {findings} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(items: list[GateItem], path: Path, live: bool) -> None:
    payload = {
        "live_checks": live,
        "checked": len(items),
        "passing": sum(1 for item in items if item.ok),
        "failing": sum(1 for item in items if not item.ok),
        "items": [
            {
                "slug": item.slug,
                "kind": item.kind,
                "ok": item.ok,
                "errors": item.errors,
                "warnings": item.warnings,
            }
            for item in items
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-validate every stored workflow and API script"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Also check live domains (off by default – links only matter on generation day)",
    )
    parser.add_argument("--only-workflow", action="append", default=[])
    parser.add_argument("--only-api", action="append", default=[])
    parser.add_argument("--report", default="pipeline/CONTENT_GATE_REPORT.md")
    parser.add_argument("--json-report", default="pipeline/content_gate_report.json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not args.live:
        os.environ["FLOWMATRIX_SKIP_LIVE"] = "1"
    # Runtime/mock-shape issues are advisory here; the authoritative runtime
    # check is the kit execution in the customer audit.
    os.environ.setdefault("FLOWMATRIX_LENIENT_RUNTIME", "1")

    items: list[GateItem] = []
    for workflow in collect_workflows(args.only_workflow):
        item = check_workflow(workflow)
        items.append(item)
        if not args.quiet:
            print(f"[{'PASS' if item.ok else 'FAIL'}] workflow: {item.slug}")
            for error in item.errors:
                print(f"    - {error}")

    for api in collect_apis(args.only_api):
        item = check_api(api)
        items.append(item)
        if not args.quiet:
            print(f"[{'PASS' if item.ok else 'FAIL'}] api: {item.slug}")
            for error in item.errors:
                print(f"    - {error}")

    report_path = cfg.ROOT / args.report
    json_path = cfg.ROOT / args.json_report
    _write_markdown(items, report_path, args.live)
    _write_json(items, json_path, args.live)

    failing = [item for item in items if not item.ok]
    print(
        f"\n[CONTENT GATE] {len(items) - len(failing)}/{len(items)} records passed · "
        f"report: {report_path}"
    )
    if failing:
        print("Failing records:")
        for item in failing:
            print(f"  ✖ {item.kind}: {item.slug} ({len(item.errors)} error(s))")
    return 0 if not failing else 1


if __name__ == "__main__":
    raise SystemExit(main())
