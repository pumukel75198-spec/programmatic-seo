"""Strict, autonomous product gate for every generated PDF and kit.

The gate reuses the deep ``full_product_audit`` stages:

* Stage 1 – ZIP structure, required files, non-empty members, sandbox dry-run
  (``workflow.py --dry-run`` / ``test_mock.py``), .env coverage, schema, HTTP
* Stage 2 – Python AST/imports/placeholders + tool consistency
* Stage 3 – PDF content, title/timestamp/price/page numbering/disclaimers
* Stage 4 – live domain reachability (skippable with ``--skip-live``)

A single finding is a hard failure. ``run_batch`` imports ``audit_one`` and
refuses to upload a product to R2 unless the report is completely clean.

Usage:
    .venv/bin/python -m pipeline.product_gate --skip-live
    .venv/bin/python -m pipeline.product_gate --kind workflow --only <slug>
    .venv/bin/python -m pipeline.product_gate --skip-live --sync-r2
    .venv/bin/python -m pipeline.product_gate --watch --interval 120
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from . import config as cfg
from . import full_product_audit


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_one(
    product: dict[str, Any],
    kind: str,
    *,
    skip_live: bool = False,
) -> full_product_audit.ProductReport:
    """Run every audit stage for one product. Never raises on findings."""
    if skip_live:
        os.environ["FLOWMATRIX_SKIP_LIVE"] = "1"
    return full_product_audit.audit_product(product, kind)


def collect_products(
    kind: str | None = None,
    only: list[str] | None = None,
    limit: int = 0,
) -> list[tuple[dict[str, Any], str]]:
    products: list[tuple[dict[str, Any], str]] = []
    workflows = _load(cfg.WORKFLOWS_FILE)
    apis = _load(cfg.APIS_FILE)
    if kind != "api":
        products.extend((item, "workflow") for item in workflows)
    if kind != "workflow":
        products.extend((item, "api") for item in apis)

    if only:
        wanted = set(only)
        products = [(item, item_kind) for item, item_kind in products if item.get("slug") in wanted]
    if limit and limit > 0:
        products = products[:limit]
    return products


def _write_markdown(reports: list[full_product_audit.ProductReport], path: Path) -> None:
    lines = [
        "# Product Gate Report",
        "",
        f"Products checked: {len(reports)} · "
        f"Passing: {sum(1 for report in reports if report.ok)} · "
        f"Failing: {sum(1 for report in reports if not report.ok)}",
        "",
        "| Slug | Type | Pages | Dry-Run | ZIP | Status | Findings |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for report in reports:
        findings = "<br>".join(str(item) for item in report.findings) or "—"
        lines.append(
            f"| {report.slug} | {report.kind} | {report.pages} | "
            f"{report.dry_run_exit} | {'yes' if report.zip_ok else 'no'} | "
            f"{'PASS' if report.ok else 'FAIL'} | {findings} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(reports: list[full_product_audit.ProductReport], path: Path) -> None:
    payload = [
        {
            "slug": report.slug,
            "kind": report.kind,
            "pages": report.pages,
            "dry_run_exit": report.dry_run_exit,
            "zip_ok": report.zip_ok,
            "domains_ok": report.domains_ok,
            "r2_synced": report.r2_synced,
            "ok": report.ok,
            "findings": [str(item) for item in report.findings],
        }
        for report in reports
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_once(
    products: list[tuple[dict[str, Any], str]],
    *,
    skip_live: bool,
    sync_r2: bool,
    report_path: Path,
    json_path: Path | None,
) -> int:
    reports: list[full_product_audit.ProductReport] = []
    for index, (product, kind) in enumerate(products, start=1):
        slug = str(product.get("slug"))
        print(f"[{index}/{len(products)}] {kind}: {slug}")
        try:
            report = audit_one(product, kind, skip_live=skip_live)
        except Exception as error:  # noqa: BLE001 - report and continue
            report = full_product_audit.ProductReport(slug=slug, kind=kind)
            report.findings.append(full_product_audit.Finding(0, f"gate crashed: {error}"))

        if sync_r2 and report.ok:
            report.r2_synced = full_product_audit.sync_product_to_r2(product, kind)

        reports.append(report)
        if report.ok:
            print("  -> PASS")
        else:
            print(f"  -> FAIL ({len(report.findings)} finding(s))")
            for finding in report.findings:
                print(f"     {finding}")

    _write_markdown(reports, report_path)
    if json_path is not None:
        _write_json(reports, json_path)

    passing = sum(1 for report in reports if report.ok)
    print(
        f"\n[GATE] {passing}/{len(reports)} products passed · "
        f"report: {report_path}"
    )
    return 0 if passing == len(reports) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strict product gate for PDFs and kits")
    parser.add_argument("--kind", choices=["workflow", "api"])
    parser.add_argument("--only", action="append", default=[], help="Slug (repeatable)")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-live", action="store_true", help="Skip live URL checks")
    parser.add_argument("--sync-r2", action="store_true", help="Upload passing products to R2")
    parser.add_argument("--watch", action="store_true", help="Re-run the gate periodically")
    parser.add_argument("--interval", type=int, default=120)
    parser.add_argument(
        "--report",
        default="pipeline/PRODUCT_GATE_REPORT.md",
        help="Markdown report path",
    )
    parser.add_argument("--json-report", help="Optional JSON report path")
    args = parser.parse_args(argv)

    report_path = cfg.ROOT / args.report
    json_path = cfg.ROOT / args.json_report if args.json_report else None

    while True:
        products = collect_products(args.kind, args.only, args.limit)
        code = run_once(
            products,
            skip_live=args.skip_live,
            sync_r2=args.sync_r2,
            report_path=report_path,
            json_path=json_path,
        )
        if not args.watch:
            return code
        print(f"[GATE] watching – next run in {args.interval}s")
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
