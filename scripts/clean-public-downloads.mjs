#!/usr/bin/env node
/**
 * clean-public-downloads.mjs
 *
 * Entfernt das alte, öffentliche PDF-Verzeichnis `public/downloads/`.
 *
 * Hintergrund: Früher wurden die Premium-PDFs nach `public/downloads/`
 * generiert und damit ungeschützt mit dem statischen Build ausgeliefert.
 * Sie liegen jetzt in `private/downloads/` und werden über den
 * Download-Gate-Worker aus R2 ausgeliefert.
 *
 * Dieses Skript läuft im `prebuild`-Schritt, damit auch bereits vorhandene
 * Altdateien nicht versehentlich weiter deployed werden.
 */

import { rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const publicDownloads = join(root, "public", "downloads");

await rm(publicDownloads, { recursive: true, force: true });
console.log("✔ public/downloads entfernt (Premium-PDFs sind jetzt privat).");
