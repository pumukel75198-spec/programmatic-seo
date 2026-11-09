#!/usr/bin/env node
/**
 * clean-dist-duplicates.mjs
 *
 * Entfernt versehentliche Cloud-Sync-Duplikate im Build-Output
 * (z. B. `index 2.html`, `sitemap-0 2.xml`).
 *
 * Hintergrund: Liegt das Projekt in einem iCloud-/Dropbox-synchronisierten
 * Ordner, legt der Sync-Dienst beim Schreiben von Dateien gelegentlich
 * Kopien mit dem Suffix " 2", " 3", … an. Diese Dateien werden nie verlinkt,
 * blähen aber jeden Deploy auf und können als Duplikate gecrawlt werden.
 *
 * Das Skript läuft als `postbuild` und zusätzlich unmittelbar vor
 * `wrangler pages deploy`.
 */

import { readdirSync, statSync, unlinkSync } from "node:fs";
import { join } from "node:path";

const ROOT = "dist";
// Matcht Dateinamen mit Cloud-Sync-Suffix: "name 2.html", "index 3.xml", …
const DUPLICATE_RE = / \d+\.[A-Za-z0-9]+$/;

let removed = 0;

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const stats = statSync(path);
    if (stats.isDirectory()) {
      walk(path);
    } else if (DUPLICATE_RE.test(name)) {
      unlinkSync(path);
      removed += 1;
    }
  }
}

try {
  walk(ROOT);
  console.log(`✔ ${removed} Cloud-Sync-Duplikat(e) aus ${ROOT}/ entfernt`);
} catch (error) {
  if (error.code !== "ENOENT") throw error;
  console.log(`${ROOT}/ existiert nicht – nichts zu bereinigen`);
}
