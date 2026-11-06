#!/usr/bin/env node
/**
 * Synchronisiert alle privaten Premium-Assets aus ./private nach R2.
 *
 * Die Key-Konventionen entsprechen exakt denen der Pipeline
 * (pipeline/run_batch.py):
 *
 *   private/downloads/flowmatrix-<slug>.pdf   -> pdfs/flowmatrix-<slug>.pdf
 *   private/kits/<slug>-kit.zip               -> kits/<slug>-kit.zip
 *   private/api-scripts/<slug>/<slug>.py      -> api-scripts/<slug>/<slug>.py
 *   private/api-kits/<slug>-kit.zip           -> api-kits/<slug>-kit.zip
 *   private/api-kits/<slug>-cheatsheet.pdf    -> api-kits/<slug>-cheatsheet.pdf
 *
 * Der Upload ist idempotent: vorhandene Objekte werden überschrieben.
 * Aufruf:  node scripts/sync-r2.mjs [--dry-run] [--concurrency=6]
 */

import { execFile } from "node:child_process";
import { readdir, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const PRIVATE = path.join(ROOT, "private");
const BUCKET = "flowmatrix-downloads";

const args = process.argv.slice(2);
const DRY_RUN = args.includes("--dry-run");
const concurrencyArg = args.find((a) => a.startsWith("--concurrency="));
const CONCURRENCY = concurrencyArg
  ? Math.max(1, Number.parseInt(concurrencyArg.split("=")[1], 10) || 6)
  : 6;

/** @returns {Promise<string[]>} */
async function listFiles(dir) {
  if (!existsSync(dir)) return [];
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFiles(full)));
    } else if (entry.isFile()) {
      files.push(full);
    }
  }
  return files;
}

/** Baut die Liste { localPath, key } nach den Pipeline-Konventionen. */
async function buildManifest() {
  /** @type {{ localPath: string, key: string }[]} */
  const manifest = [];

  // 1) Workflow-PDFs
  for (const file of await listFiles(path.join(PRIVATE, "downloads"))) {
    if (!file.endsWith(".pdf")) continue;
    manifest.push({ localPath: file, key: `pdfs/${path.basename(file)}` });
  }

  // 2) Workflow-Kits (nur die .zip, nicht entpackte Ordner)
  for (const file of await listFiles(path.join(PRIVATE, "kits"))) {
    if (!file.endsWith(".zip")) continue;
    manifest.push({ localPath: file, key: `kits/${path.basename(file)}` });
  }

  // 3) API-Scripts: nur <slug>/<slug>.py
  const apiScriptsDir = path.join(PRIVATE, "api-scripts");
  if (existsSync(apiScriptsDir)) {
    for (const entry of await readdir(apiScriptsDir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const slug = entry.name;
      const script = path.join(apiScriptsDir, slug, `${slug}.py`);
      if (existsSync(script)) {
        manifest.push({
          localPath: script,
          key: `api-scripts/${slug}/${slug}.py`,
        });
      }
    }
  }

  // 4) API-Kits + Cheatsheets
  for (const file of await listFiles(path.join(PRIVATE, "api-kits"))) {
    if (!file.endsWith(".zip") && !file.endsWith(".pdf")) continue;
    manifest.push({ localPath: file, key: `api-kits/${path.basename(file)}` });
  }

  return manifest;
}

function uploadOne({ localPath, key }) {
  return new Promise((resolve) => {
    const objectPath = `${BUCKET}/${key}`;
    if (DRY_RUN) {
      resolve({ ok: true, key, skipped: true });
      return;
    }
    execFile(
      "npx",
      [
        "wrangler",
        "r2",
        "object",
        "put",
        objectPath,
        "--file",
        localPath,
        "--remote",
      ],
      { cwd: ROOT, maxBuffer: 1024 * 1024 * 16 },
      (error, stdout, stderr) => {
        if (error) {
          resolve({ ok: false, key, error: stderr || error.message });
        } else {
          resolve({ ok: true, key });
        }
      },
    );
  });
}

async function runPool(items, worker, concurrency) {
  let index = 0;
  let done = 0;
  const results = [];
  const total = items.length;

  async function next() {
    while (index < items.length) {
      const current = items[index++];
      const result = await worker(current);
      results.push(result);
      done += 1;
      const status = result.ok ? "OK " : "ERR";
      if (!result.ok) {
        console.log(`  [${status}] ${result.key} -> ${result.error}`);
      } else if (done % 25 === 0 || done === total) {
        console.log(`  [${status}] ${done}/${total} hochgeladen`);
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, total) }, () => next()),
  );
  return results;
}

async function main() {
  if (!existsSync(PRIVATE)) {
    console.error(`[FAIL] Privates Verzeichnis nicht gefunden: ${PRIVATE}`);
    process.exit(1);
  }

  const manifest = await buildManifest();
  console.log(
    `[SYNC] ${manifest.length} Assets -> R2-Bucket "${BUCKET}"` +
      (DRY_RUN ? " (dry-run)" : ` (concurrency=${CONCURRENCY})`),
  );

  const results = await runPool(manifest, uploadOne, CONCURRENCY);
  const failed = results.filter((r) => !r.ok);
  const ok = results.length - failed.length;

  console.log("\n" + "=".repeat(60));
  console.log(`[SYNC] Fertig: ${ok}/${results.length} erfolgreich`);
  if (failed.length) {
    console.log(`[SYNC] ${failed.length} Fehler:`);
    for (const f of failed) console.log(`  - ${f.key}: ${f.error}`);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("[FAIL]", error);
  process.exit(1);
});
