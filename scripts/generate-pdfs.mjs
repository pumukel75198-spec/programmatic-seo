#!/usr/bin/env node
/**
 * generate-pdfs.mjs
 *
 * Erzeugt für jeden Workflow aus `src/data/workflows.json` ein einfaches,
 * gut lesbares Premium-PDF in `public/downloads/`.
 *
 * Aufbau jedes PDFs:
 *   1. Cover
 *   2. Überblick (Kategorie, Schwierigkeit, Dauer, Use Case, Tools)
 *   3. Schritt für Schritt: Ziel, "Das musst du tun", "Prüfe am Ende", Ergebnis
 *   4. Empfohlene Tools & Ressourcen
 *
 * Bewusst schlank gehalten: keine Code-Snippets und keine Konfigurations-
 * tabellen, damit die Anleitung ohne technische Fehler abarbeitbar bleibt.
 *
 * Ausführen:
 *   node scripts/generate-pdfs.mjs
 *   npm run pdf:generate
 *
 * Läuft automatisch vor `npm run build` (prebuild).
 */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import PDFDocument from "pdfkit";
import { ensurePdfQuality } from "./check-pdf-quality.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const root = join(__dirname, "..");

const isMain = process.argv[1]
  ? resolve(process.argv[1]) === resolve(__filename)
  : false;
const workflowsFile = join(root, "src", "data", "workflows.json");
const partnerFile = join(root, "src", "data", "partner.json");
const monetizationFile = join(root, "src", "data", "monetization.json");
// PDFs dürfen NICHT im öffentlichen Build landen. Sie werden nach
// `private/downloads/` geschrieben und über den Download-Gate-Worker aus R2
// ausgeliefert. `PDF_OUTPUT_DIR` erlaubt einen abweichenden Pfad (z. B. in CI).
const outputDir = process.env.PDF_OUTPUT_DIR
  ? resolve(root, process.env.PDF_OUTPUT_DIR)
  : join(root, "private", "downloads");

const COLORS = {
  bg: "#06070d",
  surface: "#0b0d16",
  border: "#1e293b",
  brand: "#6366f1",
  brandLight: "#a5b4fc",
  cyan: "#22d3ee",
  text: "#e5e7eb",
  muted: "#94a3b8",
  dim: "#64748b",
  white: "#ffffff",
  emerald: "#34d399",
};

const PAGE = { width: 595.28, height: 841.89, margin: 50 };
const CONTENT_WIDTH = PAGE.width - PAGE.margin * 2;
const BOTTOM_LIMIT = PAGE.height - PAGE.margin - 24;

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function normalizeStep(step) {
  if (typeof step === "string") {
    return {
      title: step,
      description: "",
      links: [],
      actions: [],
      checklist: [],
      expectedResult: "",
    };
  }
  return {
    title: step?.title ?? "Step",
    description: step?.description ?? "",
    links: Array.isArray(step?.links) ? step.links : [],
    actions: Array.isArray(step?.actions) ? step.actions : [],
    checklist: Array.isArray(step?.checklist) ? step.checklist : [],
    expectedResult: step?.expectedResult ?? "",
  };
}

function fillPage(doc) {
  doc.rect(0, 0, PAGE.width, PAGE.height).fill(COLORS.bg);
  doc.fillColor(COLORS.text);
}

function addPage(doc) {
  doc.addPage();
  fillPage(doc);
}

function ensureSpace(doc, needed = 60) {
  if (doc.y + needed > BOTTOM_LIMIT) {
    addPage(doc);
  }
}

function drawCover(doc, workflow, monetization) {
  const { width, height } = PAGE;

  doc.rect(0, 0, width, height).fill(COLORS.bg);

  // Dezente Akzentflächen
  doc.circle(width - 60, 90, 150).fillOpacity(0.12).fill(COLORS.brand);
  doc.circle(40, height - 80, 120).fillOpacity(0.1).fill(COLORS.cyan);
  doc.fillOpacity(1);

  // Markenzeichen
  doc.roundedRect(PAGE.margin, 70, 54, 54, 14).fill(COLORS.brand);
  doc
    .font("Helvetica-Bold")
    .fontSize(20)
    .fillColor(COLORS.white)
    .text("FM", PAGE.margin, 88, { width: 54, align: "center" });

  doc
    .font("Helvetica-Bold")
    .fontSize(11)
    .fillColor(COLORS.brandLight)
    .text("FLOWMATRIX.DEV", PAGE.margin, 145, { characterSpacing: 2 });

  doc
    .font("Helvetica-Bold")
    .fontSize(34)
    .fillColor(COLORS.white)
    .text("Premium Workflow", PAGE.margin, 190, { width: CONTENT_WIDTH });

  doc
    .font("Helvetica")
    .fontSize(15)
    .fillColor(COLORS.muted)
    .text("A practical guide – step by step", PAGE.margin, 235);

  doc
    .moveTo(PAGE.margin, 285)
    .lineTo(width - PAGE.margin, 285)
    .lineWidth(1)
    .strokeColor(COLORS.border)
    .stroke();

  doc
    .font("Helvetica-Bold")
    .fontSize(26)
    .fillColor(COLORS.white)
    .text(workflow.title, PAGE.margin, 320, {
      width: CONTENT_WIDTH,
      lineGap: 4,
    });

  doc
    .font("Helvetica")
    .fontSize(12)
    .fillColor(COLORS.muted)
    .text(workflow.description, PAGE.margin, doc.y + 14, {
      width: CONTENT_WIDTH,
      lineGap: 3,
    });

  const meta = [
    workflow.category,
    workflow.details?.difficulty,
    workflow.details?.duration,
  ].filter(isNonEmptyString);

  let x = PAGE.margin;
  const y = height - 150;
  doc.font("Helvetica-Bold").fontSize(9);
  for (const item of meta) {
    const textWidth = doc.widthOfString(item.toUpperCase());
    const pillWidth = textWidth + 24;
    doc
      .roundedRect(x, y, pillWidth, 26, 13)
      .fillOpacity(0.12)
      .fill(COLORS.brand);
    doc
      .fillOpacity(1)
      .fillColor(COLORS.brandLight)
      .text(item.toUpperCase(), x + 12, y + 8, { characterSpacing: 0.5 });
    x += pillWidth + 10;
  }

  doc
    .font("Helvetica")
    .fontSize(10)
    .fillColor(COLORS.dim)
    .text("flowmatrix.dev", PAGE.margin, height - 70);

  doc
    .font("Helvetica")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text(`Premium PDF · ${monetization.price}`, PAGE.margin, height - 70, {
      width: CONTENT_WIDTH,
      align: "right",
      link: monetization.checkoutUrl,
      underline: true,
    });
}

function sectionHeading(doc, text) {
  ensureSpace(doc, 70);
  doc
    .font("Helvetica-Bold")
    .fontSize(18)
    .fillColor(COLORS.white)
    .text(text, PAGE.margin, doc.y, { width: CONTENT_WIDTH });
  doc
    .moveTo(PAGE.margin, doc.y + 6)
    .lineTo(PAGE.width - PAGE.margin, doc.y + 6)
    .lineWidth(2)
    .strokeColor(COLORS.brand)
    .stroke();
  doc.moveDown(1.2);
}

function drawOverview(doc, workflow) {
  addPage(doc);

  doc
    .font("Helvetica-Bold")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text("OVERVIEW", PAGE.margin, PAGE.margin, { characterSpacing: 1.5 });

  doc
    .font("Helvetica-Bold")
    .fontSize(24)
    .fillColor(COLORS.white)
    .text(workflow.title, PAGE.margin, doc.y + 8, { width: CONTENT_WIDTH });

  doc
    .font("Helvetica")
    .fontSize(11)
    .fillColor(COLORS.muted)
    .text(workflow.description, PAGE.margin, doc.y + 12, {
      width: CONTENT_WIDTH,
      lineGap: 3,
    });

  doc.moveDown(1.5);

  // Auf-einen-Blick-Box
  const boxY = doc.y;
  const boxHeight = 110;
  doc
    .roundedRect(PAGE.margin, boxY, CONTENT_WIDTH, boxHeight, 12)
    .fill(COLORS.surface)
    .strokeColor(COLORS.border)
    .lineWidth(1)
    .stroke();

  const colWidth = (CONTENT_WIDTH - 40) / 3;
  const items = [
    ["Category", workflow.category],
    ["Difficulty", workflow.details?.difficulty ?? "—"],
    ["Duration", workflow.details?.duration ?? "—"],
  ];

  items.forEach(([label, value], index) => {
    const colX = PAGE.margin + 20 + index * colWidth;
    doc
      .font("Helvetica")
      .fontSize(8)
      .fillColor(COLORS.dim)
      .text(label.toUpperCase(), colX, boxY + 22, { characterSpacing: 1 });
    doc
      .font("Helvetica-Bold")
      .fontSize(12)
      .fillColor(COLORS.white)
      .text(value, colX, boxY + 40, { width: colWidth - 10 });
  });

  doc.y = boxY + boxHeight + 24;

  if (isNonEmptyString(workflow.details?.useCase)) {
    doc
      .font("Helvetica-Bold")
      .fontSize(12)
      .fillColor(COLORS.white)
      .text("What you use it for", PAGE.margin, doc.y);
    doc
      .font("Helvetica")
      .fontSize(11)
      .fillColor(COLORS.muted)
      .text(workflow.details.useCase, PAGE.margin, doc.y + 6, {
        width: CONTENT_WIDTH,
        lineGap: 3,
      });
    doc.moveDown(1.5);
  }

  const tools = Array.isArray(workflow.details?.tools)
    ? workflow.details.tools
    : [];
  if (tools.length > 0) {
    doc
      .font("Helvetica-Bold")
      .fontSize(12)
      .fillColor(COLORS.white)
      .text("Tools in this workflow", PAGE.margin, doc.y);
    doc
      .font("Helvetica")
      .fontSize(11)
      .fillColor(COLORS.muted)
      .text(tools.join(" · "), PAGE.margin, doc.y + 6, {
        width: CONTENT_WIDTH,
        lineGap: 3,
      });
  }
}

function subHeading(doc, text, x, width) {
  ensureSpace(doc, 40);
  doc
    .font("Helvetica-Bold")
    .fontSize(8.5)
    .fillColor(COLORS.brandLight)
    .text(text, x, doc.y + 6, { width, characterSpacing: 1 });
}

function drawSteps(doc, workflow) {
  const steps = Array.isArray(workflow.details?.steps)
    ? workflow.details.steps.map(normalizeStep)
    : [];

  addPage(doc);

  doc
    .font("Helvetica-Bold")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text("STEP BY STEP", PAGE.margin, PAGE.margin, {
      characterSpacing: 1.5,
    });

  doc
    .font("Helvetica-Bold")
    .fontSize(24)
    .fillColor(COLORS.white)
    .text("How to implement it", PAGE.margin, doc.y + 8);

  doc.moveDown(1.5);

  steps.forEach((step, index) => {
    ensureSpace(doc, 110);

    const startY = doc.y;

    // Nummern-Badge
    doc.circle(PAGE.margin + 14, startY + 14, 14).fill(COLORS.brand);
    doc
      .font("Helvetica-Bold")
      .fontSize(11)
      .fillColor(COLORS.white)
      .text(String(index + 1), PAGE.margin + 4, startY + 8, {
        width: 20,
        align: "center",
      });

    const contentX = PAGE.margin + 42;
    const contentWidth = PAGE.width - contentX - PAGE.margin;

    doc
      .font("Helvetica-Bold")
      .fontSize(13)
      .fillColor(COLORS.white)
      .text(step.title, contentX, startY, { width: contentWidth });

    if (isNonEmptyString(step.description)) {
      doc
        .font("Helvetica")
        .fontSize(10.5)
        .fillColor(COLORS.muted)
        .text(step.description, contentX, doc.y + 4, {
          width: contentWidth,
          lineGap: 2.5,
        });
    }

    // Konkrete Handlungsschritte
    if (step.actions.length > 0) {
      subHeading(doc, "WHAT YOU NEED TO DO", contentX, contentWidth);
      step.actions.forEach((action, actionIndex) => {
        ensureSpace(doc, 30);
        doc
          .font("Helvetica")
          .fontSize(9.5)
          .fillColor(COLORS.text)
          .text(`${actionIndex + 1}. ${action}`, contentX, doc.y + 2, {
            width: contentWidth,
            lineGap: 2,
          });
      });
    }

    // Prüfliste
    if (step.checklist.length > 0) {
      subHeading(doc, "CHECK AT THE END", contentX, contentWidth);
      for (const item of step.checklist) {
        ensureSpace(doc, 24);
        doc
          .font("Helvetica")
          .fontSize(9.5)
          .fillColor(COLORS.text)
          .text(`[ ] ${item}`, contentX, doc.y + 2, {
            width: contentWidth,
            lineGap: 2,
          });
      }
    }

    // Erwartetes Ergebnis
    if (isNonEmptyString(step.expectedResult)) {
      subHeading(doc, "RESULT", contentX, contentWidth);
      doc
        .font("Helvetica")
        .fontSize(9.5)
        .fillColor(COLORS.emerald)
        .text(step.expectedResult, contentX, doc.y + 2, {
          width: contentWidth,
          lineGap: 2,
        });
    }

    // Ressourcen-Links gehören ausschließlich ins PDF.
    if (step.links.length > 0) {
      subHeading(doc, "LINKS", contentX, contentWidth);
      step.links.forEach((link) => {
        if (!isNonEmptyString(link?.url)) return;
        ensureSpace(doc, 30);
        const label = isNonEmptyString(link.label) ? link.label : link.url;
        doc
          .font("Helvetica")
          .fontSize(9.5)
          .fillColor(COLORS.brandLight)
          .text(`${label}: ${link.url}`, contentX, doc.y + 2, {
            width: contentWidth,
            lineGap: 2,
            link: link.url,
            underline: true,
          });
      });
    }

    doc.y = Math.max(doc.y, startY + 40) + 18;
  });
}

function drawTools(doc, workflow, partner, monetization) {
  const toolNames = Array.isArray(workflow.details?.tools)
    ? workflow.details.tools
    : [];

  addPage(doc);

  doc
    .font("Helvetica-Bold")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text("RECOMMENDED TOOLS & RESOURCES", PAGE.margin, PAGE.margin, {
      characterSpacing: 1.5,
    });

  doc
    .font("Helvetica-Bold")
    .fontSize(24)
    .fillColor(COLORS.white)
    .text("Recommended Tools & Resources", PAGE.margin, doc.y + 8, {
      width: CONTENT_WIDTH,
    });

  doc
    .font("Helvetica")
    .fontSize(10)
    .fillColor(COLORS.muted)
    .text(
      "All tools in this workflow with their official website.",
      PAGE.margin,
      doc.y + 8,
      { width: CONTENT_WIDTH, lineGap: 2 }
    );

  doc.moveDown(1.5);

  for (const name of toolNames) {
    ensureSpace(doc, 90);

    const entry = partner[name] ?? {
      name,
      url: "https://flowmatrix.dev",
      affiliateUrl: "https://flowmatrix.dev",
      sponsored: false,
    };
    const href = entry.affiliateUrl ?? entry.url;

    const cardY = doc.y;
    doc
      .roundedRect(PAGE.margin, cardY, CONTENT_WIDTH, 64, 10)
      .fill(COLORS.surface)
      .strokeColor(COLORS.border)
      .lineWidth(1)
      .stroke();

    doc
      .font("Helvetica-Bold")
      .fontSize(12)
      .fillColor(COLORS.white)
      .text(entry.name, PAGE.margin + 16, cardY + 14, {
        width: CONTENT_WIDTH - 32,
      });

    doc
      .font("Helvetica")
      .fontSize(9)
      .fillColor(COLORS.brandLight)
      .text(href, PAGE.margin + 16, cardY + 34, {
        width: CONTENT_WIDTH - 32,
      });

    if (entry.sponsored) {
      doc
        .font("Helvetica")
        .fontSize(7.5)
        .fillColor(COLORS.dim)
        .text("Official URL", PAGE.margin + 16, cardY + 48);
    }

    doc.y = cardY + 64 + 10;
  }

  // Kauf-CTA
  ensureSpace(doc, 120);

  const ctaY = doc.y + 10;
  doc
    .roundedRect(PAGE.margin, ctaY, CONTENT_WIDTH, 92, 12)
    .fill(COLORS.surface)
    .strokeColor(COLORS.brand)
    .lineWidth(1)
    .stroke();

  doc
    .font("Helvetica-Bold")
    .fontSize(13)
    .fillColor(COLORS.white)
    .text("Full version as Premium PDF", PAGE.margin + 18, ctaY + 18, {
      width: CONTENT_WIDTH - 36,
    });

  doc
    .font("Helvetica")
    .fontSize(10)
    .fillColor(COLORS.muted)
    .text(
      `All steps, tools and resources as a PDF – ${monetization.price}.`,
      PAGE.margin + 18,
      ctaY + 40,
      { width: CONTENT_WIDTH - 36 }
    );

  doc
    .font("Helvetica-Bold")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text(`Buy now – ${monetization.price}`, PAGE.margin + 18, ctaY + 62, {
      width: CONTENT_WIDTH - 36,
      link: monetization.checkoutUrl,
      underline: true,
    });
}

function addFooters(doc) {
  const range = doc.bufferedPageRange();
  const total = range.count;

  for (let i = range.start; i < range.start + total; i += 1) {
    doc.switchToPage(i);
    const pageNumber = i - range.start + 1;

    if (pageNumber === 1) continue;

    // Fußzeile liegt unterhalb des normalen Seitenrands. Ohne das Setzen der
    // unteren Margin auf 0 würde PDFKit eine neue (leere) Seite anlegen.
    const oldBottom = doc.page.margins.bottom;
    doc.page.margins.bottom = 0;
    doc
      .font("Helvetica")
      .fontSize(8)
      .fillColor(COLORS.dim)
      .text(
        `FlowMatrix.dev · Premium Workflow · Page ${pageNumber} of ${total}`,
        PAGE.margin,
        PAGE.height - 30,
        { width: CONTENT_WIDTH, align: "center", lineBreak: false }
      );
    doc.page.margins.bottom = oldBottom;
  }
}

async function generatePdf(workflow, partner, monetization) {
  const fileName = `flowmatrix-${workflow.slug}.pdf`;
  const outputPath = join(outputDir, fileName);

  const doc = new PDFDocument({
    size: "A4",
    margin: PAGE.margin,
    bufferPages: true,
    info: {
      Title: `${workflow.title} – FlowMatrix.dev Premium Workflow`,
      Author: "FlowMatrix.dev",
      Subject: workflow.description,
      Keywords: [workflow.category, ...(workflow.tags ?? [])].join(", "),
      Creator: "FlowMatrix.dev PDF Generator",
      // Feste Zeitstempel halten die PDFs byte-genau deterministisch.
      CreationDate: new Date("2026-01-01T00:00:00.000Z"),
      ModDate: new Date("2026-01-01T00:00:00.000Z"),
    },
  });

  const chunks = [];
  doc.on("data", (chunk) => chunks.push(chunk));

  const done = new Promise((resolve, reject) => {
    doc.on("end", () => resolve(Buffer.concat(chunks)));
    doc.on("error", reject);
  });

  drawCover(doc, workflow, monetization);
  drawOverview(doc, workflow);
  drawSteps(doc, workflow);
  drawTools(doc, workflow, partner, monetization);
  addFooters(doc);

  doc.end();
  const buffer = await done;
  await writeFile(outputPath, buffer);

  return { fileName, bytes: buffer.length };
}

export async function loadInputs() {
  for (const file of [workflowsFile, partnerFile, monetizationFile]) {
    if (!existsSync(file)) {
      throw new Error(`Datei nicht gefunden: ${file}`);
    }
  }

  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));
  const partner = JSON.parse(await readFile(partnerFile, "utf8"));
  const monetization = JSON.parse(await readFile(monetizationFile, "utf8"));

  if (!Array.isArray(workflows)) {
    throw new Error("workflows.json muss ein Array sein.");
  }

  // Environment überschreibt die konfigurierte Checkout-URL.
  monetization.checkoutUrl =
    process.env.PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL?.trim() ||
    process.env.PUBLIC_LEMON_CHECKOUT_URL?.trim() ||
    monetization.checkoutUrl;

  if (!monetization.checkoutUrl) {
    throw new Error("Keine Lemon-Squeezy-Checkout-URL konfiguriert.");
  }

  return { workflows, partner, monetization };
}

export async function generateAllPdfs({
  workflows,
  partner,
  monetization,
  quiet = false,
}) {
  await mkdir(outputDir, { recursive: true });

  if (!quiet) {
    console.log(`▶ Generating ${workflows.length} premium PDFs in ${outputDir}`);
  }

  let totalBytes = 0;
  for (const workflow of workflows) {
    const { fileName, bytes } = await generatePdf(
      workflow,
      partner,
      monetization
    );
    totalBytes += bytes;
    if (!quiet) {
      console.log(`  ✓ ${fileName} (${(bytes / 1024).toFixed(1)} KB)`);
    }
  }

  if (!quiet) {
    console.log(
      `✔ Fertig: ${workflows.length} PDFs, ${(totalBytes / 1024 / 1024).toFixed(2)} MB gesamt.`
    );
  }

  return { count: workflows.length, totalBytes };
}

async function main() {
  const inputs = await loadInputs();
  await generateAllPdfs(inputs);

  if (process.env.PDF_SKIP_QUALITY_GATE === "1") return;

  const result = await ensurePdfQuality({
    loadData: loadInputs,
    regenerate: (data) => generateAllPdfs({ ...data, quiet: true }),
  });

  if (!result.ok) {
    process.exit(1);
  }
}

if (isMain) {
  main().catch((error) => {
    console.error("✖ PDF-Generierung fehlgeschlagen:", error);
    process.exit(1);
  });
}
