#!/usr/bin/env node
/**
 * upload-pdfs.mjs
 *
 * Lädt alle generierten Premium-PDFs aus `private/downloads/` in den privaten
 * KV-Namespace des Download-Gate-Workers hoch.
 *
 * Key im Namespace: `<slug>.pdf` (ohne `flowmatrix-`-Präfix), weil der Worker
 * genau danach sucht.
 *
 * Voraussetzungen:
 *   - Wrangler ist authentifiziert (CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID
 *     oder `wrangler login`).
 *   - Der KV-Namespace existiert (Default-ID siehe unten).
 *
 * Verwendung:
 *   npm run pdf:upload
 *   PDF_KV_NAMESPACE_ID=... npm run pdf:upload
 */

import { readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const pdfDir = process.env.PDF_OUTPUT_DIR
  ? resolve(root, process.env.PDF_OUTPUT_DIR)
  : join(root, "private", "downloads");
const namespaceId =
  process.env.PDF_KV_NAMESPACE_ID || "60b777e050ae4134bf22d3ef1b6a5a5e";
const npx = process.platform === "win32" ? "npx.cmd" : "npx";

if (!existsSync(pdfDir)) {
  console.error(`✖ PDF-Verzeichnis fehlt: ${pdfDir}`);
  console.error("  Führe zuerst `npm run pdf:generate` aus.");
  process.exit(1);
}

const files = (await readdir(pdfDir))
  .filter((file) => file.toLowerCase().endsWith(".pdf"))
  .sort();

if (files.length === 0) {
  console.error(`✖ Keine PDFs in ${pdfDir} gefunden.`);
  process.exit(1);
}

console.log(
  `▶ Lade ${files.length} PDF(s) in KV-Namespace "${namespaceId}" …`
);

let failed = 0;
for (const file of files) {
  const slug = file.replace(/^flowmatrix-/, "").replace(/\.pdf$/i, "");
  const key = `${slug}.pdf`;
  const filePath = join(pdfDir, file);

  console.log(`  ↑ ${file} → ${key}`);
  try {
    execFileSync(
      npx,
      [
        "wrangler",
        "kv",
        "key",
        "put",
        key,
        `--path=${filePath}`,
        `--namespace-id=${namespaceId}`,
        "--remote",
      ],
      { stdio: "inherit" }
    );
  } catch (error) {
    failed += 1;
    console.error(`  ✖ Upload fehlgeschlagen: ${file}`);
  }
}

if (failed > 0) {
  console.error(`✖ ${failed} von ${files.length} Upload(s) fehlgeschlagen.`);
  process.exit(1);
}

console.log(`✔ Fertig: ${files.length} PDF(s) hochgeladen.`);
