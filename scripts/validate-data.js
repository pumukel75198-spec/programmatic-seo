#!/usr/bin/env node
/**
 * validate-data.js
 *
 * Prüft die strukturierten JSON-Dateien in src/data:
 *   1. Ob alle JSON-Dateien fehlerfrei geparst werden können.
 *   2. Ob jeder Datensatz ein gültiges "slug"-Feld besitzt.
 *   3. Ob "slugs" über alle Kategorien hinweg eindeutig sind.
 *
 * Ausführen:  node scripts/validate-data.js
 *        oder npm run validate
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(__dirname, "../src/data");

const FILES = ["apis.json", "alternativen.json", "workflows.json"];

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
/** @type {Map<string, string>} slug -> Fundstelle */
const seenSlugs = new Map();
let recordCount = 0;

function fail(message) {
  errorCount += 1;
  console.error(`${c.red}${c.bold}✖ FEHLER:${c.reset} ${c.red}${message}${c.reset}`);
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

    const slug = record.slug;
    if (typeof slug !== "string" || slug.trim() === "") {
      fail(`${location}: Pflichtfeld "slug" fehlt oder ist kein nicht-leerer String.`);
      return;
    }

    const normalized = slug.trim();

    // 4. Doppelte Slugs über alle Kategorien hinweg
    if (seenSlugs.has(normalized)) {
      fail(
        `Doppelter Slug "${normalized}" in ${location} – bereits vergeben in ${seenSlugs.get(normalized)}.`
      );
    } else {
      seenSlugs.set(normalized, location);
    }
  });

  console.log(
    `${c.dim}  • ${file}: ${data.length} Datensatz/Datensätze geprüft${c.reset}`
  );
}

console.log("");

if (errorCount > 0) {
  console.error(
    `${c.red}${c.bold}✖ Validierung fehlgeschlagen: ${errorCount} Fehler gefunden.${c.reset}`
  );
  process.exit(1);
}

console.log(
  `${c.green}${c.bold}✔ Validierung erfolgreich: ${recordCount} Datensätze in ${FILES.length} Dateien, alle Slugs eindeutig.${c.reset}`
);
