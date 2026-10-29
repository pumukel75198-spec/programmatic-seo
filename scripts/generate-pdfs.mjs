#!/usr/bin/env node
/**
 * generate-pdfs.mjs
 *
 * Erzeugt für jeden Workflow aus `src/data/workflows.json` ein professionelles
 * Premium-PDF in `public/downloads/`.
 *
 * Jedes PDF enthält:
 *   1. Ein sauberes Cover mit "FlowMatrix.dev Premium Workflow"
 *   2. Eine Übersicht mit Difficulty, Dauer und Use Case
 *   3. Ausführliche Step-by-Step-Erklärungen inkl. Dokumentationslinks
 *   4. "Empfohlene Tools & Ressourcen" mit Affiliate-Links aus partner.json
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
import { dirname, join } from "node:path";
import PDFDocument from "pdfkit";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const workflowsFile = join(root, "src", "data", "workflows.json");
const partnerFile = join(root, "src", "data", "partner.json");
const monetizationFile = join(root, "src", "data", "monetization.json");
const outputDir = join(root, "public", "downloads");

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
};

const PAGE = { width: 595.28, height: 841.89, margin: 50 };

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function normalizeStep(step) {
  if (typeof step === "string") {
    return { title: step, description: "", links: [] };
  }
  return {
    title: step?.title ?? "Step",
    description: step?.description ?? "",
    links: Array.isArray(step?.links) ? step.links : [],
  };
}

function drawCover(doc, workflow, monetization) {
  const { width, height } = PAGE;

  doc.rect(0, 0, width, height).fill(COLORS.bg);

  // Accent shapes
  doc.circle(width - 60, 90, 150).fillOpacity(0.12).fill(COLORS.brand);
  doc.circle(40, height - 80, 120).fillOpacity(0.1).fill(COLORS.cyan);
  doc.fillOpacity(1);

  // Brand mark
  doc
    .roundedRect(PAGE.margin, 70, 54, 54, 14)
    .fill(COLORS.brand);
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
    .text("Premium Workflow", PAGE.margin, 190, { width: width - PAGE.margin * 2 });

  doc
    .font("Helvetica")
    .fontSize(15)
    .fillColor(COLORS.muted)
    .text("A practical, step-by-step playbook", PAGE.margin, 235);

  // Divider
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
      width: width - PAGE.margin * 2,
      lineGap: 4,
    });

  doc
    .font("Helvetica")
    .fontSize(12)
    .fillColor(COLORS.muted)
    .text(workflow.description, PAGE.margin, doc.y + 14, {
      width: width - PAGE.margin * 2,
      lineGap: 3,
    });

  // Meta pills
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
      width: width - PAGE.margin * 2,
      align: "right",
      link: monetization.checkoutUrl,
      underline: true,
    });
}

function sectionHeading(doc, text) {
  if (doc.y > PAGE.height - 140) doc.addPage();
  doc
    .font("Helvetica-Bold")
    .fontSize(18)
    .fillColor(COLORS.white)
    .text(text, PAGE.margin, doc.y, { width: PAGE.width - PAGE.margin * 2 });
  doc
    .moveTo(PAGE.margin, doc.y + 6)
    .lineTo(PAGE.width - PAGE.margin, doc.y + 6)
    .lineWidth(2)
    .strokeColor(COLORS.brand)
    .stroke();
  doc.moveDown(1.2);
}

function drawOverview(doc, workflow) {
  doc.addPage();
  doc.rect(0, 0, PAGE.width, PAGE.height).fill(COLORS.bg);
  doc.fillColor(COLORS.text);

  doc
    .font("Helvetica-Bold")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text("OVERVIEW", PAGE.margin, PAGE.margin, { characterSpacing: 1.5 });

  doc
    .font("Helvetica-Bold")
    .fontSize(24)
    .fillColor(COLORS.white)
    .text(workflow.title, PAGE.margin, doc.y + 8, {
      width: PAGE.width - PAGE.margin * 2,
    });

  doc
    .font("Helvetica")
    .fontSize(11)
    .fillColor(COLORS.muted)
    .text(workflow.description, PAGE.margin, doc.y + 12, {
      width: PAGE.width - PAGE.margin * 2,
      lineGap: 3,
    });

  doc.moveDown(1.5);

  // At a glance box
  const boxY = doc.y;
  const boxHeight = 110;
  doc
    .roundedRect(PAGE.margin, boxY, PAGE.width - PAGE.margin * 2, boxHeight, 12)
    .fill(COLORS.surface)
    .strokeColor(COLORS.border)
    .lineWidth(1)
    .stroke();

  const colWidth = (PAGE.width - PAGE.margin * 2 - 40) / 3;
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
      .text("Use case", PAGE.margin, doc.y);
    doc
      .font("Helvetica")
      .fontSize(11)
      .fillColor(COLORS.muted)
      .text(workflow.details.useCase, PAGE.margin, doc.y + 6, {
        width: PAGE.width - PAGE.margin * 2,
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
      .text("Tools used in this workflow", PAGE.margin, doc.y);
    doc
      .font("Helvetica")
      .fontSize(11)
      .fillColor(COLORS.muted)
      .text(tools.join(" · "), PAGE.margin, doc.y + 6, {
        width: PAGE.width - PAGE.margin * 2,
        lineGap: 3,
      });
  }
}

function drawSteps(doc, workflow) {
  const steps = Array.isArray(workflow.details?.steps)
    ? workflow.details.steps.map(normalizeStep)
    : [];

  doc.addPage();
  doc.rect(0, 0, PAGE.width, PAGE.height).fill(COLORS.bg);
  doc.fillColor(COLORS.text);

  doc
    .font("Helvetica-Bold")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text("STEP BY STEP", PAGE.margin, PAGE.margin, { characterSpacing: 1.5 });

  doc
    .font("Helvetica-Bold")
    .fontSize(24)
    .fillColor(COLORS.white)
    .text("How to build it", PAGE.margin, doc.y + 8);

  doc.moveDown(1.5);

  steps.forEach((step, index) => {
    if (doc.y > PAGE.height - 150) {
      doc.addPage();
      doc.rect(0, 0, PAGE.width, PAGE.height).fill(COLORS.bg);
      doc.fillColor(COLORS.text);
    }

    const startY = doc.y;

    // Number badge
    doc
      .circle(PAGE.margin + 14, startY + 14, 14)
      .fill(COLORS.brand);
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

    if (step.links.length > 0) {
      doc.moveDown(0.4);
      doc
        .font("Helvetica-Bold")
        .fontSize(8)
        .fillColor(COLORS.dim)
        .text("RESOURCES", contentX, doc.y, { characterSpacing: 1 });
      for (const link of step.links) {
        if (!isNonEmptyString(link?.url)) continue;
        doc
          .font("Helvetica")
          .fontSize(9.5)
          .fillColor(COLORS.brandLight)
          .text(`→ ${link.label ?? link.url}`, contentX, doc.y + 2, {
            width: contentWidth,
            link: link.url,
            underline: true,
          });
      }
    }

    doc.y = Math.max(doc.y, startY + 40) + 18;
  });
}

function drawTools(doc, workflow, partner, monetization) {
  const toolNames = Array.isArray(workflow.details?.tools)
    ? workflow.details.tools
    : [];

  doc.addPage();
  doc.rect(0, 0, PAGE.width, PAGE.height).fill(COLORS.bg);
  doc.fillColor(COLORS.text);

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
    .text("Empfohlene Tools & Ressourcen", PAGE.margin, doc.y + 8, {
      width: PAGE.width - PAGE.margin * 2,
    });

  doc
    .font("Helvetica")
    .fontSize(10)
    .fillColor(COLORS.muted)
    .text(
      "Alle Links sind klickbar. Einige Links sind Affiliate-Links – für dich entstehen dadurch keine Mehrkosten.",
      PAGE.margin,
      doc.y + 8,
      { width: PAGE.width - PAGE.margin * 2, lineGap: 2 }
    );

  doc.moveDown(1.5);

  for (const name of toolNames) {
    if (doc.y > PAGE.height - 110) {
      doc.addPage();
      doc.rect(0, 0, PAGE.width, PAGE.height).fill(COLORS.bg);
      doc.fillColor(COLORS.text);
    }

    const entry = partner[name] ?? {
      name,
      url: "https://flowmatrix.com",
      affiliateUrl: "https://flowmatrix.com",
      sponsored: false,
    };
    const href = entry.affiliateUrl ?? entry.url;

    const cardY = doc.y;
    doc
      .roundedRect(
        PAGE.margin,
        cardY,
        PAGE.width - PAGE.margin * 2,
        64,
        10
      )
      .fill(COLORS.surface)
      .strokeColor(COLORS.border)
      .lineWidth(1)
      .stroke();

    doc
      .font("Helvetica-Bold")
      .fontSize(12)
      .fillColor(COLORS.white)
      .text(entry.name, PAGE.margin + 16, cardY + 14, {
        width: PAGE.width - PAGE.margin * 2 - 32,
      });

    doc
      .font("Helvetica")
      .fontSize(9)
      .fillColor(COLORS.brandLight)
      .text(href, PAGE.margin + 16, cardY + 34, {
        width: PAGE.width - PAGE.margin * 2 - 32,
        link: href,
        underline: true,
      });

    if (entry.sponsored) {
      doc
        .font("Helvetica")
        .fontSize(7.5)
        .fillColor(COLORS.dim)
        .text("Affiliate-Link", PAGE.margin + 16, cardY + 48);
    }

    doc.y = cardY + 64 + 10;
  }

  // Checkout CTA
  if (doc.y > PAGE.height - 150) {
    doc.addPage();
    doc.rect(0, 0, PAGE.width, PAGE.height).fill(COLORS.bg);
    doc.fillColor(COLORS.text);
  }

  const ctaY = doc.y + 10;
  doc
    .roundedRect(PAGE.margin, ctaY, PAGE.width - PAGE.margin * 2, 92, 12)
    .fill(COLORS.surface)
    .strokeColor(COLORS.brand)
    .lineWidth(1)
    .stroke();

  doc
    .font("Helvetica-Bold")
    .fontSize(13)
    .fillColor(COLORS.white)
    .text("Vollversion als Premium-PDF", PAGE.margin + 18, ctaY + 18, {
      width: PAGE.width - PAGE.margin * 2 - 36,
    });

  doc
    .font("Helvetica")
    .fontSize(10)
    .fillColor(COLORS.muted)
    .text(
      `Alle Schritte, Tools und Ressourcen als PDF – ${monetization.price}.`,
      PAGE.margin + 18,
      ctaY + 40,
      { width: PAGE.width - PAGE.margin * 2 - 36 }
    );

  doc
    .font("Helvetica-Bold")
    .fontSize(10)
    .fillColor(COLORS.brandLight)
    .text(
      `Jetzt kaufen – ${monetization.price}`,
      PAGE.margin + 18,
      ctaY + 62,
      {
        width: PAGE.width - PAGE.margin * 2 - 36,
        link: monetization.checkoutUrl,
        underline: true,
      }
    );
}

function addFooters(doc) {
  const range = doc.bufferedPageRange();
  const total = range.count;

  for (let i = range.start; i < range.start + total; i += 1) {
    doc.switchToPage(i);
    const pageNumber = i - range.start + 1;

    if (pageNumber === 1) continue;

    doc
      .font("Helvetica")
      .fontSize(8)
      .fillColor(COLORS.dim)
      .text(
        `FlowMatrix.dev · Premium Workflow · Seite ${pageNumber} von ${total}`,
        PAGE.margin,
        PAGE.height - 35,
        { width: PAGE.width - PAGE.margin * 2, align: "center" }
      );
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
      // Fixed timestamps keep generated PDFs byte-for-byte deterministic,
      // so a rebuild does not dirty the working tree.
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

async function main() {
  for (const file of [workflowsFile, partnerFile, monetizationFile]) {
    if (!existsSync(file)) {
      console.error(`✖ Datei nicht gefunden: ${file}`);
      process.exit(1);
    }
  }

  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));
  const partner = JSON.parse(await readFile(partnerFile, "utf8"));
  const monetization = JSON.parse(await readFile(monetizationFile, "utf8"));

  if (!Array.isArray(workflows)) {
    console.error("✖ workflows.json muss ein Array sein.");
    process.exit(1);
  }

  // Environment overrides the configured checkout URL.
  monetization.checkoutUrl =
    process.env.PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL?.trim() ||
    process.env.PUBLIC_LEMON_CHECKOUT_URL?.trim() ||
    monetization.checkoutUrl;

  if (!monetization.checkoutUrl) {
    console.error("✖ Keine Lemon-Squeezy-Checkout-URL konfiguriert.");
    process.exit(1);
  }

  await mkdir(outputDir, { recursive: true });

  console.log(`▶ Generiere ${workflows.length} Premium-PDFs in ${outputDir}`);

  let totalBytes = 0;
  for (const workflow of workflows) {
    const { fileName, bytes } = await generatePdf(
      workflow,
      partner,
      monetization
    );
    totalBytes += bytes;
    console.log(
      `  ✓ ${fileName} (${(bytes / 1024).toFixed(1)} KB)`
    );
  }

  console.log(
    `✔ Fertig: ${workflows.length} PDFs, ${(totalBytes / 1024 / 1024).toFixed(2)} MB gesamt.`
  );
}

main().catch((error) => {
  console.error("✖ PDF-Generierung fehlgeschlagen:", error);
  process.exit(1);
});
