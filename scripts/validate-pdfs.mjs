#!/usr/bin/env node
/**
 * validate-pdfs.mjs
 *
 * Qualitäts-Gatekeeper für alle generierten Workflow-PDFs.
 *
 * Prüft für jedes PDF in `public/downloads/`:
 *   1. Inhaltlicher Abgleich mit `src/data/workflows.json`
 *      (Titel, Beschreibung, Kategorie, Difficulty, Dauer, Use Case, Steps)
 *   2. Junk-/Halluzinations-Check (Lorem Ipsum, TODO, Platzhalter,
 *      undefined, NaN, kaputte JSON-Fragmente)
 *   3. Struktur (mind. 3 Steps, nicht-leere Titel/Beschreibungen,
 *      vollständige Sätze, vorhandene Abschnitte)
 *   4. Link-Integrität (Affiliate-Links aus partner.json + Lemon-Squeezy-
 *      Checkout-Link + Preis €4.99)
 *
 * Läuft automatisch im `prebuild`-Schritt. Bei einem Fehler bricht das
 * Skript mit Exit-Code 1 ab und blockiert damit den Build.
 *
 * Ausführen:
 *   node scripts/validate-pdfs.mjs
 *   npm run pdf:validate
 */

import { readFile, access } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { PDFParse } from "pdf-parse";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const workflowsFile = join(root, "src", "data", "workflows.json");
const partnerFile = join(root, "src", "data", "partner.json");
const monetizationFile = join(root, "src", "data", "monetization.json");
const pdfDir = process.env.PDF_OUTPUT_DIR
  ? resolve(root, process.env.PDF_OUTPUT_DIR)
  : join(root, "private", "downloads");

const MIN_STEPS = 3;
const MIN_STEP_DESCRIPTION_LENGTH = 20;

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

const normalize = (value) =>
  String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();

const lower = (value) => normalize(value).toLowerCase();

/**
 * Normalisierung für den Textabgleich: PDF-Textumbrüche können nach einem
 * Bindestrich ein Leerzeichen einfügen ("CRM- System"). Für den inhaltlichen
 * Vergleich werden solche Artefakte entfernt.
 */
const matchNormalize = (value) =>
  normalize(value)
    .replace(/-\s+/g, "-")
    .replace(/\/\s+/g, "/")
    .replace(/\s+([.,;:!?])/g, "$1")
    .toLowerCase();

const compact = (value) =>
  String(value ?? "")
    .replace(/\s+/g, "")
    .toLowerCase();

const truncate = (value, max = 90) => {
  const text = normalize(value);
  return text.length > max ? `${text.slice(0, max)}…` : text;
};

const JUNK_PATTERNS = [
  ["Lorem Ipsum", /lorem\s+ipsum/i],
  ["TODO", /\bTODO\b|\bT\s+O\s+D\s+O\b/i],
  ["Platzhalter [Hier einfügen]", /\[hier\s+einfügen\]/i],
  ["Platzhalter [insert …]", /\[insert[^\]]*\]/i],
  ["TBD", /\bT\s*B\s*D\b/i],
  ["undefined", /\bundefined\b/i],
  ["NaN", /\bNaN\b/],
  ["veralteter OpenAI-Endpoint /v1/engines", /api\.openai\.com\/v1\/engines\//i],
  ["veralteter OpenAI-Completions-Endpoint", /api\.openai\.com\/v1\/completions/i],
  ["veraltetes Modell text-davinci", /text-davinci/i],
  ["veraltetes Modell gpt-3.5-turbo", /gpt-3\.5-turbo/i],
  ["veralteter Befehl npm init astro", /npm init astro/i],
  ["Template-Platzhalter", /\{\{/],
];

const COMPACT_JUNK = [
  ["Lorem Ipsum", "loremipsum"],
  ["Platzhalter [Hier einfügen]", "[hiereinfügen]"],
];

function checkContains(text, needle, label, errors) {
  if (!needle) return;
  if (!matchNormalize(text).includes(matchNormalize(needle))) {
    errors.push(`${label} fehlt im PDF-Text: "${truncate(needle)}"`);
  }
}

function checkJunk(text, errors) {
  for (const [label, pattern] of JUNK_PATTERNS) {
    if (pattern.test(text)) {
      errors.push(`Junk/Halluzination gefunden: ${label}`);
    }
  }

  const compactText = compact(text);
  for (const [label, needle] of COMPACT_JUNK) {
    if (compactText.includes(needle)) {
      errors.push(`Junk/Halluzination gefunden: ${label}`);
    }
  }
}

function checkStructure(workflow, text, errors) {
  const steps = Array.isArray(workflow.details?.steps)
    ? workflow.details.steps
    : [];

  if (steps.length < MIN_STEPS) {
    errors.push(
      `Zu wenige Steps: ${steps.length} (mindestens ${MIN_STEPS} erwartet)`
    );
  }

  steps.forEach((step, index) => {
    const title = typeof step === "string" ? step : step?.title;
    const description =
      typeof step === "string" ? "" : step?.description ?? "";

    if (!normalize(title)) {
      errors.push(`Step ${index + 1}: Titel ist leer`);
    }
    if (!normalize(description)) {
      errors.push(`Step ${index + 1}: Beschreibung ist leer`);
    } else {
      if (normalize(description).length < MIN_STEP_DESCRIPTION_LENGTH) {
        errors.push(
          `Step ${index + 1}: Beschreibung ist zu kurz (${normalize(description).length} Zeichen)`
        );
      }
      if (!/[.!?)]$/.test(normalize(description))) {
        errors.push(
          `Step ${index + 1}: Beschreibung endet nicht mit einem vollständigen Satz`
        );
      }
    }

    if (typeof step === "string") {
      errors.push(`Step ${index + 1}: keine strukturierten Detailfelder`);
      return;
    }

    // Master-Anleitung: konkrete Actions, Checkliste und Ergebnis
    if (!Array.isArray(step.actions) || step.actions.length < 3) {
      errors.push(
        `Step ${index + 1}: mindestens 3 konkrete Actions erwartet`
      );
    } else {
      step.actions.forEach((action, actionIndex) => {
        checkContains(
          text,
          action,
          `Step ${index + 1} Action ${actionIndex + 1}`,
          errors
        );
      });
    }

    if (!Array.isArray(step.checklist) || step.checklist.length < 2) {
      errors.push(
        `Step ${index + 1}: mindestens 2 Checklisten-Punkte erwartet`
      );
    } else {
      step.checklist.forEach((item, itemIndex) => {
        checkContains(
          text,
          item,
          `Step ${index + 1} Checkliste ${itemIndex + 1}`,
          errors
        );
      });
    }

    if (!normalize(step.expectedResult)) {
      errors.push(`Step ${index + 1}: expectedResult fehlt`);
    } else {
      checkContains(
        text,
        step.expectedResult,
        `Step ${index + 1} Ergebnis`,
        errors
      );
    }

  });

  const compactText = compact(text);
  if (!compactText.includes("stepbystep")) {
    errors.push('Abschnitt "STEP BY STEP" fehlt');
  }
  if (!compactText.includes("overview")) {
    errors.push('Abschnitt "OVERVIEW" fehlt');
  }
  if (!lower(text).includes("how to implement it")) {
    errors.push('Abschnitt "How to implement it" fehlt');
  }
  if (!compactText.includes("whatyouneedtodo")) {
    errors.push('Abschnitt "WHAT YOU NEED TO DO" fehlt');
  }
  if (!compactText.includes("checkattheend")) {
    errors.push('Abschnitt "CHECK AT THE END" fehlt');
  }
  if (!compactText.includes("result")) {
    errors.push('Abschnitt "RESULT" fehlt');
  }
}

function checkLinks(workflow, text, raw, partner, monetization, errors) {
  const uriMatches = [...raw.matchAll(/\/URI\s*\(([^)]*)\)/g)].map(
    (match) => match[1]
  );

  if (uriMatches.length === 0) {
    errors.push("Keine klickbaren URLs (/URI) im PDF gefunden");
  }

  const expectedLink =
    monetization.checkoutUrl ||
    `https://flowmatrix.dev/en/workflows/${workflow.slug}`;
  if (!uriMatches.includes(expectedLink) && !raw.includes(expectedLink)) {
    errors.push(`Checkout-/Workflow-Link fehlt im PDF: ${expectedLink}`);
  }

  if (!lower(text).includes(lower(monetization.price))) {
    errors.push(`Preis "${monetization.price}" fehlt im PDF-Text`);
  }

  const premiumText = lower(text).replace(/[-\s]+/g, " ");
  if (
    !premiumText.includes("premium pdf") &&
    !premiumText.includes("premium workflow")
  ) {
    errors.push('Hinweis "Premium-PDF"/"Premium-Workflow" fehlt');
  }
}

async function extractText(buffer) {
  const parser = new PDFParse({ data: buffer });
  try {
    const result = await parser.getText();
    return result.text ?? "";
  } finally {
    await parser.destroy();
  }
}

async function validateWorkflow(workflow, partner, monetization) {
  const errors = [];
  const fileName = `flowmatrix-${workflow.slug}.pdf`;
  const filePath = join(pdfDir, fileName);

  try {
    await access(filePath);
  } catch {
    return { fileName, errors: [`PDF-Datei fehlt: ${filePath}`] };
  }

  const buffer = await readFile(filePath);
  const raw = buffer.toString("latin1");

  let text = "";
  try {
    text = await extractText(buffer);
  } catch (error) {
    return {
      fileName,
      errors: [`PDF-Text konnte nicht extrahiert werden: ${error.message}`],
    };
  }

  if (!normalize(text)) {
    return { fileName, errors: ["PDF enthält keinen extrahierbaren Text"] };
  }

  // 1. Inhaltlicher Abgleich
  checkContains(text, workflow.title, "Titel", errors);
  checkContains(text, workflow.description, "Beschreibung", errors);
  checkContains(text, workflow.category, "Kategorie", errors);
  checkContains(text, workflow.details?.difficulty, "Difficulty", errors);
  checkContains(text, workflow.details?.duration, "Dauer", errors);
  checkContains(text, workflow.details?.useCase, "Use Case", errors);

  const steps = Array.isArray(workflow.details?.steps)
    ? workflow.details.steps
    : [];
  steps.forEach((step, index) => {
    const title = typeof step === "string" ? step : step?.title;
    const description =
      typeof step === "string" ? "" : step?.description ?? "";
    checkContains(text, title, `Step ${index + 1} Titel`, errors);
    checkContains(text, description, `Step ${index + 1} Beschreibung`, errors);
  });

  // 2. Junk-/Halluzinations-Check
  checkJunk(text, errors);

  // 3. Struktur
  checkStructure(workflow, text, errors);

  // 4. Link-Integrität
  checkLinks(workflow, text, raw, partner, monetization, errors);

  return { fileName, errors };
}

async function main() {
  for (const file of [workflowsFile, partnerFile, monetizationFile]) {
    if (!existsSync(file)) {
      console.error(`${c.red}✖ Datei nicht gefunden: ${file}${c.reset}`);
      process.exit(1);
    }
  }

  if (!existsSync(pdfDir)) {
    console.error(`${c.red}✖ PDF-Verzeichnis fehlt: ${pdfDir}${c.reset}`);
    process.exit(1);
  }

  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));
  const partner = JSON.parse(await readFile(partnerFile, "utf8"));
  const monetization = JSON.parse(await readFile(monetizationFile, "utf8"));

  monetization.checkoutUrl =
    process.env.PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL?.trim() ||
    process.env.PUBLIC_LEMON_CHECKOUT_URL?.trim() ||
    monetization.checkoutUrl;

  console.log(
    `${c.cyan}${c.bold}▶ Validiere ${workflows.length} Premium-PDFs${c.reset} ${c.dim}(${pdfDir})${c.reset}`
  );

  let failed = 0;
  let passed = 0;

  for (const workflow of workflows) {
    const { fileName, errors } = await validateWorkflow(
      workflow,
      partner,
      monetization
    );

    if (errors.length === 0) {
      passed += 1;
      console.log(`  ${c.green}✓${c.reset} ${fileName}`);
    } else {
      failed += 1;
      console.error(`  ${c.red}✖${c.reset} ${fileName}`);
      for (const error of errors) {
        console.error(`      ${c.red}• ${error}${c.reset}`);
      }
    }
  }

  console.log("");

  if (failed > 0) {
    console.error(
      `${c.red}${c.bold}✖ PDF-Validierung fehlgeschlagen: ${failed} von ${workflows.length} PDFs ungültig.${c.reset}`
    );
    process.exit(1);
  }

  console.log(
    `${c.green}${c.bold}✔ PDF-Validierung erfolgreich: ${passed} PDFs geprüft, keine Junk-Inhalte, alle Links intakt.${c.reset}`
  );
}

main().catch((error) => {
  console.error(`${c.red}${c.bold}✖ Validierung abgebrochen:${c.reset}`, error);
  process.exit(1);
});
