#!/usr/bin/env node
/**
 * kv-cache.mjs
 *
 * Kleiner Hash-Cache für die KV-Uploads. Er verhindert, dass bei jedem
 * Batch-Lauf alle PDFs und Python-Skripte erneut nach Cloudflare KV
 * geschrieben werden – das würde das tägliche KV-Operationslimit sprengen.
 *
 * Das Manifest liegt in `src/data/kv-manifest.json` und wird vom Batch
 * mitcommittet, damit es zwischen den GitHub-Actions-Läufen persistent bleibt.
 */

import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const manifestFile = join(root, "src", "data", "kv-manifest.json");

export async function loadManifest() {
  if (!existsSync(manifestFile)) return { pdfs: {}, scripts: {} };
  try {
    const data = JSON.parse(await readFile(manifestFile, "utf8"));
    return {
      pdfs: data && typeof data.pdfs === "object" ? data.pdfs : {},
      scripts: data && typeof data.scripts === "object" ? data.scripts : {},
    };
  } catch {
    return { pdfs: {}, scripts: {} };
  }
}

export async function saveManifest(manifest) {
  await writeFile(
    manifestFile,
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8"
  );
}

export function hashBuffer(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}
