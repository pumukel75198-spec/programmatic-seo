#!/usr/bin/env node
/**
 * upload-api-scripts.mjs
 *
 * Lädt die generierten Python-Starter-Skripte aus `private/api-scripts/` in den
 * privaten KV-Namespace des Download-Gate-Workers – direkt über die
 * Cloudflare-API (parallel).
 *
 * Keys pro API:
 *   script:<slug>:py        -> <slug>.py
 *   script:<slug>:readme    -> README.md
 *   script:<slug>:metadata  -> metadata.json
 *
 * Voraussetzungen:
 *   - CLOUDFLARE_ACCOUNT_ID und CLOUDFLARE_API_TOKEN sind gesetzt
 *     (Token mit Workers KV Storage:Edit).
 *   - Der KV-Namespace existiert (Default-ID siehe unten).
 *
 * Verwendung:
 *   npm run api-scripts:upload
 */

import { readdir, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadManifest, saveManifest, hashBuffer } from "./kv-cache.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const scriptsDir = process.env.API_SCRIPTS_OUTPUT_DIR
  ? resolve(root, process.env.API_SCRIPTS_OUTPUT_DIR)
  : join(root, "private", "api-scripts");
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

if (!existsSync(scriptsDir)) {
  console.error(`✖ Skript-Verzeichnis fehlt: ${scriptsDir}`);
  console.error("  Führe zuerst `npm run api-scripts:generate` aus.");
  process.exit(1);
}

const slugs = (await readdir(scriptsDir, { withFileTypes: true }))
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort();

if (slugs.length === 0) {
  console.error(`✖ Keine Skript-Ordner in ${scriptsDir} gefunden.`);
  process.exit(1);
}

console.log(
  `▶ Lade Skripte für ${slugs.length} API(s) in KV-Namespace "${namespaceId}" …`
);

const baseUrl = `https://api.cloudflare.com/client/v4/accounts/${accountId}/storage/kv/namespaces/${namespaceId}/values`;
const manifest = await loadManifest();

async function put(key, body, contentType) {
  const hash = hashBuffer(body);
  // Unveränderte Dateien nicht erneut schreiben (KV-Tageslimit schonen).
  if (manifest.scripts[key] === hash) return false;

  const response = await fetch(`${baseUrl}/${encodeURIComponent(key)}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${apiToken}`,
      "Content-Type": contentType,
    },
    body,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${text.slice(0, 200)}`);
  }
  manifest.scripts[key] = hash;
  return true;
}

async function uploadSlug(slug) {
  const dir = join(scriptsDir, slug);
  const py = await readFile(join(dir, `${slug}.py`));
  const readme = await readFile(join(dir, "README.md"));
  const metadata = await readFile(join(dir, "metadata.json"));

  const changed = [];
  if (await put(`script:${slug}:py`, py, "text/x-python")) changed.push("py");
  if (await put(`script:${slug}:readme`, readme, "text/markdown")) changed.push("readme");
  if (await put(`script:${slug}:metadata`, metadata, "application/json")) changed.push("metadata");

  if (changed.length > 0) {
    console.log(`  ✓ ${slug} (${changed.join(", ")})`);
  } else {
    console.log(`  ↺ ${slug} (unverändert)`);
  }
}

let failed = 0;
let cursor = 0;
const concurrency = 5;

async function worker() {
  while (cursor < slugs.length) {
    const slug = slugs[cursor++];
    try {
      await uploadSlug(slug);
    } catch (error) {
      failed += 1;
      console.error(`  ✖ ${slug}: ${error.message}`);
    }
  }
}

await Promise.all(
  Array.from({ length: Math.min(concurrency, slugs.length) }, () => worker())
);

await saveManifest(manifest);

if (failed > 0) {
  console.error(`✖ ${failed} von ${slugs.length} API(s) fehlgeschlagen.`);
  process.exit(1);
}

console.log(`✔ Fertig: Skripte für ${slugs.length} API(s) geprüft, Änderungen hochgeladen.`);
