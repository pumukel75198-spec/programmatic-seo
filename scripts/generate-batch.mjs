#!/usr/bin/env node
/**
 * generate-batch.mjs
 *
 * Automatischer 3-Tage-Batch: erzeugt zufällig ~10 neue Einträge
 * (APIs, Alternatives, Workflows), reichert sie an, generiert PDFs und
 * Python-Skripte, validiert alles streng und lädt die Premium-Dateien
 * nach KV hoch.
 *
 * Standard-Verteilung (randomisiert, Summe ~10):
 *   - 2–4 APIs
 *   - 3–5 Alternatives
 *   - 2–4 Workflows
 *
 * Verwendung:
 *   node scripts/generate-batch.mjs
 *   node scripts/generate-batch.mjs --dry-run
 *   node scripts/generate-batch.mjs --apis=3 --alternatives=4 --workflows=3
 *
 * Benötigt:
 *   OPENROUTER_API_KEY
 *   CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (für KV-Upload)
 */

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const argv = process.argv.slice(2);
const dryRun = argv.includes("--dry-run");

function argValue(name) {
  const match = argv.find((arg) => arg.startsWith(`--${name}=`));
  return match ? Number(match.split("=")[1]) : null;
}

function randomInt(min, max) {
  return min + Math.floor(Math.random() * (max - min + 1));
}

function pickCounts() {
  const apis = argValue("apis") ?? randomInt(2, 4);
  const alternatives = argValue("alternatives") ?? randomInt(3, 5);
  let workflows = argValue("workflows") ?? randomInt(2, 4);

  // Gesamtsumme auf ~10 begrenzen, ohne die Mindestwerte zu verletzen.
  const total = apis + alternatives + workflows;
  if (total > 10) {
    workflows = Math.max(2, workflows - (total - 10));
  }
  return { apis, alternatives, workflows };
}

const counts = pickCounts();

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

function run(label, command, args, { optional = false } = {}) {
  console.log(
    `\n${c.cyan}${c.bold}▶ ${label}${c.reset} ${c.dim}${command} ${args.join(" ")}${c.reset}`
  );
  if (dryRun) {
    console.log(`${c.yellow}  (dry-run – übersprungen)${c.reset}`);
    return true;
  }
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: "inherit",
    env: process.env,
  });
  if (result.status !== 0) {
    if (optional) {
      console.warn(
        `${c.yellow}  ⚠ ${label} fehlgeschlagen (optional, wird übersprungen)${c.reset}`
      );
      return false;
    }
    console.error(
      `${c.red}  ✖ ${label} fehlgeschlagen (Exit ${result.status})${c.reset}`
    );
    process.exit(result.status ?? 1);
  }
  return true;
}

function node(script, args = [], options) {
  return run(script, process.execPath, [join("scripts", script), ...args], options);
}

console.log(
  `${c.cyan}${c.bold}▶ Automatischer Content-Batch${c.reset} ` +
    `${c.dim}(APIs: ${counts.apis}, Alternatives: ${counts.alternatives}, Workflows: ${counts.workflows})${c.reset}`
);

if (!process.env.OPENROUTER_API_KEY && !dryRun) {
  console.error(
    `${c.red}✖ OPENROUTER_API_KEY ist nicht gesetzt.${c.reset}`
  );
  process.exit(1);
}

// 1) Neue Einträge generieren (target hoch setzen, damit exakt `limit` erzeugt wird).
node("generate-apis.mjs", ["--target=9999", `--limit=${counts.apis}`]);
node("generate-alternatives.mjs", ["--target=9999", `--limit=${counts.alternatives}`]);
node("generate-workflows.mjs", ["--target=9999", `--limit=${counts.workflows}`]);

// 2) Anreichern.
node("enrich-alternatives.mjs", [], { optional: true });
node("enrich-workflows.mjs", [], { optional: true });
node("enrich-workflow-details.mjs", [], { optional: true });
node("sync-partners.mjs", [], { optional: true });

// 3) PDFs erzeugen und streng prüfen.
node("generate-pdfs.mjs");
node("validate-pdfs.mjs");
node("check-pdf-quality.mjs");

// 4) Python-Skripte erzeugen und streng prüfen.
node("generate-api-scripts.mjs");
node("validate-api-scripts.mjs");
node("test-api-scripts.mjs", ["--offline"]);

// 5) Premium-Dateien nach KV hochladen (nur wenn Cloudflare-Zugang gesetzt ist).
if (process.env.CLOUDFLARE_API_TOKEN && process.env.CLOUDFLARE_ACCOUNT_ID) {
  node("upload-pdfs.mjs");
  node("upload-api-scripts.mjs");
} else {
  console.warn(
    `${c.yellow}⚠ CLOUDFLARE_API_TOKEN/ACCOUNT_ID fehlen – KV-Upload übersprungen.${c.reset}`
  );
}

// 6) Statische Seite bauen (prebuild validiert erneut).
run("Astro build", "npm", ["run", "build"]);

console.log(
  `\n${c.green}${c.bold}✔ Batch abgeschlossen.${c.reset} ` +
    `${c.dim}Neue Einträge: ${counts.apis} APIs, ${counts.alternatives} Alternatives, ${counts.workflows} Workflows.${c.reset}`
);
