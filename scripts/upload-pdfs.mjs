#!/usr/bin/env node
/**
 * upload-pdfs.mjs
 *
 * Lädt alle generierten Premium-PDFs aus `private/downloads/` in den privaten
 * KV-Namespace des Download-Gate-Workers – direkt über die Cloudflare-API
 * (parallel, ohne einen Wrangler-Prozess pro Datei).
 *
 * Key im Namespace: `<slug>.pdf` (ohne `flowmatrix-`-Präfix), weil der Worker
 * genau danach sucht.
 *
 * Voraussetzungen:
 *   - CLOUDFLARE_ACCOUNT_ID und CLOUDFLARE_API_TOKEN sind gesetzt
 *     (Token mit Workers KV Storage:Edit).
 *   - Der KV-Namespace existiert (Default-ID siehe unten).
 *
 * Verwendung:
 *   npm run pdf:upload
 *   PDF_KV_NAMESPACE_ID=... npm run pdf:upload
 */

import { readdir, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const pdfDir = process.env.PDF_OUTPUT_DIR
  ? resolve(root, process.env.PDF_OUTPUT_DIR)
  : join(root, "private", "downloads");
const namespaceId =
  process.env.PDF_KV_NAMESPACE_ID || "60b777e050ae4134bf22d3ef1b6a5a5e";
const accountId = process.env.CLOUDFLARE_ACCOUNT_ID;
const apiToken = process.env.CLOUDFLARE_API_TOKEN;

if (!accountId || !apiToken) {
  console.error(
    "✖ CLOUDFLARE_ACCOUNT_ID und CLOUDFLARE_API_TOKEN müssen gesetzt sein."
  );
  process.exit(1);
}

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

const baseUrl = `https://api.cloudflare.com/client/v4/accounts/${accountId}/storage/kv/namespaces/${namespaceId}/values`;

async function upload(file) {
  const slug = file.replace(/^flowmatrix-/, "").replace(/\.pdf$/i, "");
  const key = `${slug}.pdf`;
  const body = await readFile(join(pdfDir, file));

  const response = await fetch(`${baseUrl}/${encodeURIComponent(key)}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${apiToken}`,
      "Content-Type": "application/octet-stream",
    },
    body,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${text.slice(0, 200)}`);
  }

  console.log(`  ✓ ${key}`);
}

let failed = 0;
let cursor = 0;
const concurrency = 5;

async function worker() {
  while (cursor < files.length) {
    const file = files[cursor++];
    try {
      await upload(file);
    } catch (error) {
      failed += 1;
      console.error(`  ✖ ${file}: ${error.message}`);
    }
  }
}

await Promise.all(
  Array.from({ length: Math.min(concurrency, files.length) }, () => worker())
);

if (failed > 0) {
  console.error(`✖ ${failed} von ${files.length} Upload(s) fehlgeschlagen.`);
  process.exit(1);
}

console.log(`✔ Fertig: ${files.length} PDF(s) hochgeladen.`);
