#!/usr/bin/env node
/**
 * validate-data.js
 *
 * Prüft die strukturierten JSON-Dateien in src/data:
 *   1. Ob alle JSON-Dateien fehlerfrei geparst werden können.
 *   2. Ob jeder Datensatz alle Pflichtfelder besitzt
 *      (slug, title, description, category, tags, details).
 *   3. Ob "slug" URL-freundlich (kebab-case) und über alle Kategorien eindeutig ist.
 *   4. Ob "tags" ein Array und "details" ein Objekt ist.
 *   5. SEO-Warnungen für Title-/Description-Längen.
 *
 * Ausführen:  node scripts/validate-data.js
 *        oder npm run validate
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(__dirname, "../src/data");

const FILES = ["apis.json", "alternatives.json", "workflows.json"];
const REQUIRED_FIELDS = [
  "slug",
  "title",
  "description",
  "category",
  "tags",
  "details",
];
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

let errorCount = 0;
let warningCount = 0;
/** @type {Map<string, string>} slug -> Fundstelle */
const seenSlugs = new Map();
let recordCount = 0;

function fail(message) {
  errorCount += 1;
  console.error(`${c.red}${c.bold}✖ FEHLER:${c.reset} ${c.red}${message}${c.reset}`);
}

function warn(message) {
  warningCount += 1;
  console.warn(`${c.yellow}${c.bold}⚠ WARNUNG:${c.reset} ${c.yellow}${message}${c.reset}`);
}

console.log(`${c.cyan}${c.bold}▶ Validiere Datendateien in ${dataDir}${c.reset}\n`);

for (const file of FILES) {
  const filePath = path.join(dataDir, file);
  let raw;

  // 1. Datei lesen
  try {
    raw = readFileSync(filePath, "utf8");
  } catch (err) {
    fail(`${file}: Datei konnte nicht gelesen werden (${err.code ?? err.message}).`);
    continue;
  }

  // 2. JSON parsen
  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    fail(`${file}: Ungültiges JSON – ${err.message}`);
    continue;
  }

  if (!Array.isArray(data)) {
    fail(`${file}: Erwartet wird ein Array von Datensätzen.`);
    continue;
  }

  if (data.length === 0) {
    fail(`${file}: Das Array ist leer – mindestens ein Datensatz wird erwartet.`);
    continue;
  }

  // 3. Datensätze prüfen
  data.forEach((record, index) => {
    recordCount += 1;
    const location = `${file}[${index}]`;

    if (record === null || typeof record !== "object" || Array.isArray(record)) {
      fail(`${location}: Datensatz ist kein Objekt.`);
      return;
    }

    // Pflichtfelder vorhanden?
    for (const field of REQUIRED_FIELDS) {
      if (!(field in record)) {
        fail(`${location}: Pflichtfeld "${field}" fehlt.`);
      }
    }

    // slug: nicht leer, kebab-case, eindeutig
    const slug = record.slug;
    if (typeof slug !== "string" || slug.trim() === "") {
      fail(`${location}: Pflichtfeld "slug" fehlt oder ist kein nicht-leerer String.`);
    } else {
      const normalized = slug.trim();
      if (!SLUG_PATTERN.test(normalized)) {
        fail(
          `${location}: Slug "${normalized}" ist nicht URL-freundlich (erwartet: kebab-case, z. B. "openai-whisper-api").`
        );
      }
      if (seenSlugs.has(normalized)) {
        fail(
          `Doppelter Slug "${normalized}" in ${location} – bereits vergeben in ${seenSlugs.get(normalized)}.`
        );
      } else {
        seenSlugs.set(normalized, location);
      }
    }

    // title
    if (typeof record.title !== "string" || record.title.trim() === "") {
      fail(`${location}: "title" fehlt oder ist leer.`);
    } else if (record.title.length > 60) {
      warn(
        `${location}: "title" ist ${record.title.length} Zeichen lang (empfohlen: ≤ 60).`
      );
    }

    // description
    if (
      typeof record.description !== "string" ||
      record.description.trim() === ""
    ) {
      fail(`${location}: "description" fehlt oder ist leer.`);
    } else {
      if (record.description.length > 160) {
        warn(
          `${location}: "description" ist ${record.description.length} Zeichen lang (empfohlen: ≤ 160).`
        );
      }
      if (record.description.length < 50) {
        warn(
          `${location}: "description" ist sehr kurz (${record.description.length} Zeichen, empfohlen: ≥ 50).`
        );
      }
    }

    // category
    if (typeof record.category !== "string" || record.category.trim() === "") {
      fail(`${location}: "category" fehlt oder ist leer.`);
    }

    // tags
    if (!Array.isArray(record.tags)) {
      fail(`${location}: "tags" muss ein Array sein.`);
    } else if (record.tags.length === 0) {
      warn(`${location}: "tags" ist leer.`);
    } else if (
      record.tags.some((tag) => typeof tag !== "string" || tag.trim() === "")
    ) {
      fail(`${location}: "tags" enthält leere oder nicht-string Werte.`);
    }

    // details
    if (
      record.details === null ||
      typeof record.details !== "object" ||
      Array.isArray(record.details)
    ) {
      fail(`${location}: "details" muss ein Objekt sein.`);
    } else if (Object.keys(record.details).length === 0) {
      warn(`${location}: "details" ist leer.`);
    }
  });

  console.log(
    `${c.dim}  • ${file}: ${data.length} Datensatz/Datensätze geprüft${c.reset}`
  );
}

console.log("");

if (errorCount > 0) {
  console.error(
    `${c.red}${c.bold}✖ Validierung fehlgeschlagen: ${errorCount} Fehler, ${warningCount} Warnungen.${c.reset}`
  );
  process.exit(1);
}

const warningSuffix =
  warningCount > 0 ? ` (${warningCount} Warnungen)` : "";
console.log(
  `${c.green}${c.bold}✔ Validierung erfolgreich: ${recordCount} Datensätze in ${FILES.length} Dateien, alle Slugs eindeutig.${warningSuffix}${c.reset}`
);
