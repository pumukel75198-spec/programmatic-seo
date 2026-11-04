"""The only PDF layout module – dynamic, content-driven FlowMatrix blueprint.

There is NO fixed page count and NO fixed step count. The document flows
organically over as many pages as the content needs:

    Cover -> Overview -> Setup & Glossary -> Step 1..N -> Checklist ->
    Troubleshooting & Resources

``Page X of Y`` is computed with a two-pass render (first pass counts pages,
second pass draws the real total). Every page carries the creation timestamp
and the link-validity disclaimer where required.

Requires ``reportlab`` (see requirements.txt). This is the only place that
defines PDF layout, colours, fonts and page geometry.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import guard
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas
except ImportError as error:  # pragma: no cover
    raise ImportError(
        "reportlab is required for the PDF pipeline. Run: pip install -r pipeline/requirements.txt"
    ) from error

from . import config as cfg

MARGIN = cfg.PDF_MARGIN
WIDTH = cfg.PAGE_WIDTH
HEIGHT = cfg.PAGE_HEIGHT
CONTENT = cfg.CONTENT_WIDTH
TOP = 60
BOTTOM = 70


def _hex(color: str) -> HexColor:
    return HexColor(color)


class _Doc:
    """A small top-based flow layout engine with dynamic pagination."""

    def __init__(self, c: canvas.Canvas, total_pages: int | None = None) -> None:
        self.c = c
        self.total = total_pages
        self.page = 1
        self.y = TOP
        self._background()

    # -- primitives ------------------------------------------------------- #
    def _background(self) -> None:
        self.c.setFillColor(_hex(cfg.COLORS["bg"]))
        self.c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)

    def _footer(self) -> None:
        c = self.c
        c.setStrokeColor(_hex(cfg.COLORS["border"]))
        c.setLineWidth(0.6)
        c.line(MARGIN, 52, WIDTH - MARGIN, 52)
        c.setFont("Helvetica", 8)
        c.setFillColor(_hex(cfg.COLORS["muted"]))
        c.drawString(MARGIN, 40, cfg.PDF_FOOTER)
        total = self.total if self.total else "?"
        c.drawRightString(WIDTH - MARGIN, 40, f"Page {self.page} of {total}")

    def new_page(self) -> None:
        self._footer()
        self.c.showPage()
        self.page += 1
        self.y = TOP
        self._background()

    def ensure_space(self, height: float) -> None:
        if self.y + height > HEIGHT - BOTTOM:
            self.new_page()

    def finish(self) -> int:
        self._footer()
        self.c.showPage()
        return self.page

    # -- text ------------------------------------------------------------- #
    def kicker(self, text: str) -> None:
        self.ensure_space(20)
        c = self.c
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(_hex(cfg.COLORS["brand_light"]))
        c.drawString(MARGIN, HEIGHT - self.y - 9, text.upper())
        self.y += 16

    def heading(self, text: str, size: float = 22) -> None:
        lines = simpleSplit(str(text or ""), "Helvetica-Bold", size, CONTENT)
        leading = size * 1.2
        height = len(lines) * leading
        self.ensure_space(height + 8)
        c = self.c
        c.setFont("Helvetica-Bold", size)
        c.setFillColor(_hex(cfg.COLORS["white"]))
        for index, line in enumerate(lines):
            c.drawString(MARGIN, HEIGHT - self.y - size - index * leading, line)
        self.y += height + 8

    def paragraph(
        self,
        text: str,
        size: float = 10,
        color: str = cfg.COLORS["text"],
        leading: float | None = None,
    ) -> None:
        leading = leading or size * 1.4
        lines = simpleSplit(str(text or ""), "Helvetica", size, CONTENT)
        height = len(lines) * leading
        self.ensure_space(height)
        c = self.c
        c.setFont("Helvetica", size)
        c.setFillColor(_hex(color))
        for index, line in enumerate(lines):
            c.drawString(MARGIN, HEIGHT - self.y - size - index * leading, line)
        self.y += height + 4

    def bullet(self, text: str, size: float = 9.5) -> None:
        self.paragraph(f"• {text}", size=size, color=cfg.COLORS["text"])

    def divider(self) -> None:
        self.ensure_space(20)
        c = self.c
        c.setStrokeColor(_hex(cfg.COLORS["border"]))
        c.setLineWidth(0.6)
        c.line(MARGIN, HEIGHT - self.y, WIDTH - MARGIN, HEIGHT - self.y)
        self.y += 16

    # -- blocks ----------------------------------------------------------- #
    def code_block(self, code: str, max_lines: int = 80) -> None:
        raw_lines = str(code or "").splitlines()[:max_lines]
        rendered: list[str] = []
        for line in raw_lines:
            rendered.extend(simpleSplit(line, "Courier", 7.4, CONTENT - 16) or [""])

        line_h = 9.6
        index = 0
        while index < len(rendered):
            if self.y + 14 + line_h > HEIGHT - BOTTOM:
                self.new_page()
            available = HEIGHT - BOTTOM - self.y - 14
            fit = max(1, int(available // line_h))
            chunk = rendered[index : index + fit]
            block_height = 14 + len(chunk) * line_h
            c = self.c
            c.setFillColor(_hex(cfg.COLORS["code_bg"]))
            c.roundRect(
                MARGIN,
                HEIGHT - self.y - block_height,
                CONTENT,
                block_height,
                6,
                fill=1,
                stroke=0,
            )
            c.setFont("Courier", 7.4)
            c.setFillColor(_hex(cfg.COLORS["code_text"]))
            for offset, line in enumerate(chunk):
                c.drawString(
                    MARGIN + 8,
                    HEIGHT - self.y - 12 - offset * line_h,
                    line,
                )
            self.y += block_height + 6
            index += len(chunk)
            if index < len(rendered):
                self.new_page()

    def checkbox(self, text: str) -> None:
        lines = simpleSplit(str(text or ""), "Helvetica", 9.5, CONTENT - 16)
        height = max(12, len(lines) * 12)
        self.ensure_space(height)
        c = self.c
        c.setStrokeColor(_hex(cfg.COLORS["brand_light"]))
        c.setLineWidth(0.8)
        c.rect(MARGIN, HEIGHT - self.y - 9, 8.5, 8.5, fill=0, stroke=1)
        c.setFont("Helvetica", 9.5)
        c.setFillColor(_hex(cfg.COLORS["text"]))
        for index, line in enumerate(lines):
            c.drawString(MARGIN + 16, HEIGHT - self.y - 9 - index * 12, line)
        self.y += height + 4

    def badges(self, items: list[str]) -> None:
        self.ensure_space(28)
        c = self.c
        x = MARGIN
        for badge in [item for item in items if item]:
            width = c.stringWidth(badge, "Helvetica-Bold", 8.5) + 18
            if x + width > WIDTH - MARGIN:
                x = MARGIN
                self.y += 26
                self.ensure_space(26)
            c.setFillColor(_hex(cfg.COLORS["panel_alt"]))
            c.roundRect(x, HEIGHT - self.y - 20, width, 20, 5, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(_hex(cfg.COLORS["brand_light"]))
            c.drawString(x + 9, HEIGHT - self.y - 13.5, badge)
            x += width + 8
        self.y += 28

    # -- sections --------------------------------------------------------- #
    def cover(self, workflow: dict[str, Any], timestamp: str) -> None:
        c = self.c
        c.setFillColor(_hex(cfg.COLORS["brand"]))
        c.rect(0, HEIGHT - 10, WIDTH, 10, fill=1, stroke=0)

        c.setFont("Helvetica-Bold", 30)
        c.setFillColor(_hex(cfg.COLORS["white"]))
        c.drawString(MARGIN, HEIGHT - 60 - 30, "FM")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(_hex(cfg.COLORS["brand_light"]))
        c.drawString(MARGIN, HEIGHT - 95 - 8.5, "F L O W M A T R I X . D E V")

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(_hex(cfg.COLORS["brand_light"]))
        c.drawString(MARGIN, HEIGHT - 150 - 12, "Premium Workflow")
        c.setFont("Helvetica", 11)
        c.setFillColor(_hex(cfg.COLORS["muted"]))
        c.drawString(MARGIN, HEIGHT - 175 - 11, "A practical guide – step by step")

        self.y = 230
        self.heading(workflow.get("title", "Untitled"), size=34)
        self.paragraph(
            workflow.get("description", ""),
            size=12,
            color=cfg.COLORS["muted"],
            leading=17,
        )

        details = workflow.get("details") or {}
        self.badges(
            [
                str(workflow.get("category", "")).upper(),
                str(details.get("difficulty", "")).upper(),
                str(details.get("duration", "")).upper(),
            ]
        )

        self.paragraph(
            f"Created & Verified on: {timestamp}",
            size=9.5,
            color=cfg.COLORS["brand_light"],
        )

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(_hex(cfg.COLORS["white"]))
        c.drawRightString(
            WIDTH - MARGIN,
            70,
            f"Premium Kit {cfg.price_label(details.get('difficulty'))}",
        )

    def overview(self, workflow: dict[str, Any], timestamp: str) -> None:
        details = workflow.get("details") or {}
        self.kicker("Overview")
        self.heading(workflow.get("title", "Untitled"), size=24)
        self.paragraph(
            workflow.get("description", ""),
            size=11,
            color=cfg.COLORS["text"],
            leading=16,
        )

        self.divider()
        for label, value in (
            ("Category", workflow.get("category", "—")),
            ("Difficulty", details.get("difficulty", "—")),
            ("Duration", details.get("duration", "—")),
        ):
            self.paragraph(f"{label.upper()}: {value}", size=10, color=cfg.COLORS["white"])

        self.divider()
        self.kicker("What you use it for")
        self.paragraph(details.get("useCase", "—"), size=10.5)

        self.kicker("Tools in this workflow")
        for tool in details.get("tools") or []:
            self.bullet(tool, size=10.5)

        self.divider()
        self.paragraph(
            f"Created & Verified on: {timestamp}",
            size=9.5,
            color=cfg.COLORS["brand_light"],
        )
        self.paragraph(
            cfg.LINK_DISCLAIMER.format(timestamp=timestamp),
            size=8.5,
            color=cfg.COLORS["muted"],
            leading=11,
        )

    def setup_and_glossary(self, workflow: dict[str, Any]) -> None:
        details = workflow.get("details") or {}
        self.kicker("Before you start")
        self.heading("What you need", size=22)
        for item in details.get("prerequisites") or []:
            self.bullet(item)

        self.divider()
        self.kicker("Glossary")
        self.heading("Advanced concepts", size=20)
        for entry in details.get("glossary") or []:
            self.paragraph(
                str(entry.get("term", "")),
                size=10.5,
                color=cfg.COLORS["white"],
            )
            self.paragraph(
                str(entry.get("definition", "")),
                size=9.2,
                color=cfg.COLORS["muted"],
                leading=12,
            )

    def step(self, step: dict[str, Any], number: int, total_steps: int) -> None:
        self.kicker(f"Step {number} of {total_steps}")
        self.heading(step.get("title", f"Step {number}"), size=19)

        self.kicker("Technical details")
        self.paragraph(
            step.get("technical_explanation", ""),
            size=9.2,
            color=cfg.COLORS["muted"],
            leading=12,
        )

        self.kicker("What you need to do")
        for action in step.get("actions") or []:
            self.bullet(action, size=9.2)

        self.kicker("Code snippet")
        self.code_block(step.get("code_snippet", ""))

        self.kicker("Check at the end")
        for item in step.get("checklist") or []:
            self.checkbox(item)

        self.kicker("Result")
        self.paragraph(
            step.get("expectedResult", ""),
            size=9.2,
            color=cfg.COLORS["emerald"],
            leading=12,
        )

        links = step.get("links") or []
        if links:
            self.kicker("Links")
            for link in links[:2]:
                url = str(link.get("url", ""))
                if "ref=" not in url:
                    url = f"{url}{'&' if '?' in url else '?'}ref=flowmatrix"
                self.paragraph(
                    f"{link.get('label', 'Link')}: {url}",
                    size=8.2,
                    color=cfg.COLORS["brand_light"],
                    leading=11,
                )
        self.divider()

    def checklist(self, workflow: dict[str, Any]) -> None:
        self.kicker("Printable checklist")
        self.heading("Your complete checklist", size=22)
        for index, step in enumerate(
            (workflow.get("details") or {}).get("steps") or [], start=1
        ):
            self.paragraph(
                f"{index}. {step.get('title', '')}",
                size=10,
                color=cfg.COLORS["white"],
            )
            for item in step.get("checklist") or []:
                self.checkbox(item)
            self.y += 6

    def troubleshooting_and_resources(
        self, workflow: dict[str, Any], timestamp: str
    ) -> None:
        details = workflow.get("details") or {}
        self.kicker("Troubleshooting")
        self.heading("If something goes wrong", size=22)
        for entry in details.get("troubleshooting") or []:
            self.paragraph(
                f"Problem: {entry.get('problem', '')}",
                size=10,
                color=cfg.COLORS["white"],
            )
            self.paragraph(
                f"Fix: {entry.get('solution', '')}",
                size=9.2,
                color=cfg.COLORS["emerald"],
                leading=12,
            )

        self.divider()
        self.kicker("Recommended tools & resources")
        for entry in details.get("resources") or []:
            self.paragraph(
                f"{entry.get('label', 'Resource')}: {entry.get('url', '')}",
                size=9.2,
                color=cfg.COLORS["brand_light"],
                leading=12,
            )

        self.divider()
        self.paragraph(
            cfg.LINK_DISCLAIMER.format(timestamp=timestamp),
            size=8.5,
            color=cfg.COLORS["muted"],
            leading=11,
        )


def _layout(
    workflow: dict[str, Any],
    c: canvas.Canvas,
    total_pages: int | None = None,
) -> int:
    doc = _Doc(c, total_pages)
    details = workflow.get("details") or {}
    timestamp = str(workflow.get("created_and_verified_at") or "—")

    doc.cover(workflow, timestamp)
    doc.new_page()

    doc.overview(workflow, timestamp)
    doc.new_page()

    doc.setup_and_glossary(workflow)

    steps = details.get("steps") or []
    for index, step in enumerate(steps, start=1):
        # Start every step on a fresh page so a step is never split between
        # its text and its code snippet.
        doc.new_page()
        doc.step(step, index, len(steps))

    doc.new_page()
    doc.checklist(workflow)
    doc.new_page()

    doc.troubleshooting_and_resources(workflow, timestamp)
    return doc.finish()


def render_workflow_pdf(workflow: dict[str, Any], out_path: Path) -> Path:
    """Render a workflow to a dynamic, content-driven PDF."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Pass 1: count pages (footer shows "?" for the total).
    buffer = io.BytesIO()
    counter = canvas.Canvas(buffer, pagesize=(WIDTH, HEIGHT))
    total = _layout(workflow, counter, total_pages=None)
    counter.save()

    # Pass 2: render with the real total.
    c = canvas.Canvas(str(out_path), pagesize=(WIDTH, HEIGHT))
    c.setTitle(str(workflow.get("title", "FlowMatrix Workflow")))
    c.setAuthor("FlowMatrix.dev")
    _layout(workflow, c, total_pages=total)
    c.save()
    return out_path
