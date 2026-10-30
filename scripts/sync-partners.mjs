#!/usr/bin/env node
/**
 * sync-partners.mjs
 *
 * Erweitert `src/data/partner.json` um alle APIs aus `apis.json` und alle
 * konkreten Alternativen aus `alternatives.json`, die noch nicht als Tool
 * hinterlegt sind.
 *
 * Ziel: Workflows können die neuen APIs und Alternativen als Tools verwenden,
 * ohne dass die PDF-Qualitätsprüfung an fehlenden `partner.json`-Einträgen
 * scheitert.
 *
 * Regeln:
 *   - Bestehende Einträge werden NIE überschrieben (echte Affiliate-Links
 *     bleiben erhalten).
 *   - Nur Tools mit gültiger HTTPS-URL werden übernommen.
 *   - Platzhalter-Domains (example.com, localhost, 127.0.0.1) werden ignoriert.
 *   - Die Ausgabe wird alphabetisch sortiert.
 *
 * Verwendung:
 *   node scripts/sync-partners.mjs --dry-run
 *   node scripts/sync-partners.mjs
 */

import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const partnerFile = join(root, "src", "data", "partner.json");
const apisFile = join(root, "src", "data", "apis.json");
const alternativesFile = join(root, "src", "data", "alternatives.json");

const PLACEHOLDER_HOST_PATTERN =
  /(?:^|\.)(?:example\.(?:com|org|net)|localhost|127\.0\.0\.1|0\.0\.0\.0)$/i;

function isValidHttpsUrl(value) {
  if (typeof value !== "string" || value.trim() === "") return false;
  try {
    const url = new URL(value.trim());
    if (url.protocol !== "https:") return false;
    if (PLACEHOLDER_HOST_PATTERN.test(url.hostname)) return false;
    return true;
  } catch {
    return false;
  }
}

function parseArgs(argv) {
  return {
    dryRun: argv.includes("--dry-run"),
    help: argv.includes("--help") || argv.includes("-h"),
  };
}

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log("Verwendung: node scripts/sync-partners.mjs [--dry-run]");
    return;
  }

  for (const file of [partnerFile, apisFile, alternativesFile]) {
    if (!existsSync(file)) {
      console.error(`✖ Datei nicht gefunden: ${file}`);
      process.exit(1);
    }
  }

  const partner = JSON.parse(await readFile(partnerFile, "utf8"));
  const apis = JSON.parse(await readFile(apisFile, "utf8"));
  const alternatives = JSON.parse(await readFile(alternativesFile, "utf8"));

  const added = [];
  const skipped = [];

  function addTool(name, url) {
    const key = String(name ?? "").trim();
    if (!key) return;
    if (partner[key]) {
      skipped.push(key);
      return;
    }
    if (!isValidHttpsUrl(url)) {
      skipped.push(`${key} (keine gültige HTTPS-URL)`);
      return;
    }
    partner[key] = {
      name: key,
      url: url.trim(),
      affiliateUrl: url.trim(),
      sponsored: false,
    };
    added.push(key);
  }

  for (const api of apis) {
    addTool(api.title, api.details?.website);
  }

  for (const entry of alternatives) {
    for (const alternative of entry.details?.alternatives ?? []) {
      if (typeof alternative === "string") continue;
      addTool(alternative.name, alternative.url);
    }
  }

  const sorted = Object.fromEntries(
    Object.entries(partner).sort(([a], [b]) => a.localeCompare(b))
  );

  console.log(
    `${c.cyan}${c.bold}▶ Partner-Sync${c.reset} · Bestand vorher: ${Object.keys(partner).length}`
  );
  console.log(`  Neu: ${c.green}${added.length}${c.reset} · übersprungen: ${skipped.length}`);
  for (const name of added) {
    console.log(`  ${c.green}+${c.reset} ${name}`);
  }

  if (opts.dryRun) {
    console.log(
      `\n${c.yellow}${c.bold}Dry Run beendet – keine Datei geschrieben.${c.reset}`
    );
    return;
  }

  await writeFile(
    partnerFile,
    `${JSON.stringify(sorted, null, 2)}\n`,
    "utf8"
  );
  console.log(
    `\n${c.green}${c.bold}✔ Fertig: ${Object.keys(sorted).length} Tools in partner.json.${c.reset}`
  );
  console.log(`${c.dim}  Geschrieben: ${partnerFile}${c.reset}`);
}

main().catch((error) => {
  console.error("✖ Unerwarteter Fehler:", error);
  process.exit(1);
});
