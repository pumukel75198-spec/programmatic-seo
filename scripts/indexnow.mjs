#!/usr/bin/env node
/**
 * indexnow.mjs
 *
 * Meldet alle URLs aus der frisch gebauten Sitemap automatisch bei IndexNow
 * (Bing, Yandex, Seznam u. a.) an. So werden neue programmatische Seiten
 * unmittelbar nach dem Deploy indexiert – ohne manuelles Einreichen.
 *
 * Der Key liegt als Datei unter `public/<key>.txt` und ist damit öffentlich
 * verifizierbar. Er ist kein Secret.
 *
 * Verwendung:
 *   node scripts/indexnow.mjs
 *   node scripts/indexnow.mjs --dry-run
 */

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const distDir = join(root, "dist");
const publicDir = join(root, "public");

const dryRun = process.argv.includes("--dry-run");
const host = (process.env.SITE_URL ?? "https://flowmatrix.dev").replace(/\/$/, "");
const key = process.env.INDEXNOW_KEY ?? "f7c3a9e2b1d84f6a9c0e5d2b8a4f1c73";

function collectUrls() {
  const urls = new Set();
  if (!existsSync(distDir)) return [];

  for (const file of readdirSync(distDir)) {
    if (!/^sitemap.*\.xml$/.test(file)) continue;
    const xml = readFileSync(join(distDir, file), "utf8");
    for (const match of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) {
      urls.add(match[1].trim());
    }
  }
  return [...urls];
}

async function main() {
  const keyFile = join(publicDir, `${key}.txt`);
  if (!existsSync(keyFile)) {
    console.warn(
      `⚠ IndexNow-Key-Datei fehlt: public/${key}.txt – übersprungen.`
    );
    return;
  }

  const urls = collectUrls();
  if (urls.length === 0) {
    console.warn("⚠ Keine URLs in der Sitemap gefunden – übersprungen.");
    return;
  }

  const payload = {
    host: new URL(host).host,
    key,
    keyLocation: `${host}/${key}.txt`,
    urlList: urls,
  };

  if (dryRun) {
    console.log(`✔ Dry-run – ${urls.length} URLs würden gemeldet.`);
    return;
  }

  const response = await fetch("https://api.indexnow.org/indexnow", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify(payload),
  });

  if (response.ok || response.status === 202) {
    console.log(`✔ IndexNow: ${urls.length} URLs gemeldet (${response.status}).`);
  } else {
    const text = await response.text().catch(() => "");
    console.warn(`⚠ IndexNow antwortete mit ${response.status}: ${text.slice(0, 200)}`);
  }
}

main().catch((error) => {
  console.error(`✖ ${error.message}`);
  process.exit(1);
});
