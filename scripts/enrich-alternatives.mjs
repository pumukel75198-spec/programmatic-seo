#!/usr/bin/env node
/**
 * enrich-alternatives.mjs
 *
 * Reichert vereinfachte Alternativen-Datensätze an.
 *
 * Ausgangslage: In `src/data/alternatives.json` ist `details.alternatives`
 * bei einigen Einträgen nur ein Array aus Namens-Strings, z. B.
 *   "alternatives": ["Brevo", "MailerLite", "Buttondown"]
 * Bei anderen Einträgen liegen bereits reiche Objekte mit description,
 * pros, cons, bestFor und url vor.
 *
 * Dieses Skript:
 *   1. liest `src/data/alternatives.json`,
 *   2. filtert alle Einträge, deren `details.alternatives` noch Strings enthält,
 *   3. fragt über die OpenRouter-API strukturierte Tool-Profile ab,
 *   4. ersetzt ausschließlich die String-Einträge durch Objekte und
 *      lässt reiche Datensätze unangetastet,
 *   5. schreibt die Datei atomar zurück.
 *
 * Voraussetzungen:
 *   export OPENROUTER_API_KEY="sk-or-..."
 *
 * Verwendung:
 *   node scripts/enrich-alternatives.mjs --dry-run
 *   node scripts/enrich-alternatives.mjs
 *   node scripts/enrich-alternatives.mjs --only=mailchimp-alternatives,trello-alternatives
 *   node scripts/enrich-alternatives.mjs --limit=3 --model=openai/gpt-4o-mini
 *
 * Optionen:
 *   --dry-run        Nur anzeigen, was passieren würde (keine API-Calls, kein Schreiben)
 *   --limit=N        Maximal N Datensätze verarbeiten
 *   --only=a,b       Nur diese Slugs verarbeiten
 *   --model=ID       OpenRouter-Modell (Default: openai/gpt-4o-mini)
 *   --concurrency=N  Parallele Requests (Default: 3)
 *   --no-cache       Cache ignorieren und neu abfragen
 *   --data-file=P    Alternative JSON-Datei (für Tests)
 *   --help           Hilfe anzeigen
 */

import { readFile, writeFile, rename, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
let dataFile = join(root, "src", "data", "alternatives.json");
const cacheDir = join(root, ".cache");
const cacheFile = join(cacheDir, "enrich-alternatives.json");

const API_URL =
  process.env.OPENROUTER_BASE_URL?.replace(/\/$/, "") ??
  "https://openrouter.ai/api/v1";
const MODEL = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini";
const API_KEY = process.env.OPENROUTER_API_KEY;

const REQUIRED_TOOL_FIELDS = [
  "name",
  "description",
  "pros",
  "cons",
  "bestFor",
  "url",
];

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const opts = {
    dryRun: false,
    limit: Infinity,
    only: null,
    model: MODEL,
    concurrency: 3,
    useCache: true,
    dataFile: null,
    help: false,
  };

  for (const arg of argv) {
    if (arg === "--dry-run") opts.dryRun = true;
    else if (arg === "--no-cache") opts.useCache = false;
    else if (arg === "--help" || arg === "-h") opts.help = true;
    else if (arg.startsWith("--limit=")) opts.limit = Number(arg.slice(8));
    else if (arg.startsWith("--only="))
      opts.only = arg
        .slice(7)
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    else if (arg.startsWith("--model=")) opts.model = arg.slice(8);
    else if (arg.startsWith("--concurrency="))
      opts.concurrency = Math.max(1, Number(arg.slice(14)));
    else if (arg.startsWith("--data-file="))
      opts.dataFile = arg.slice(12);
    else {
      console.error(`Unbekannte Option: ${arg}`);
      process.exit(1);
    }
  }

  if (!Number.isFinite(opts.limit) || opts.limit < 0) opts.limit = Infinity;
  if (!Number.isFinite(opts.concurrency) || opts.concurrency < 1)
    opts.concurrency = 1;

  return opts;
}

function printHelp() {
  console.log(`Verwendung: node scripts/enrich-alternatives.mjs [Optionen]

Optionen:
  --dry-run        Nur anzeigen, was passieren würde (keine API-Calls, kein Schreiben)
  --limit=N        Maximal N Datensätze verarbeiten
  --only=a,b       Nur diese Slugs verarbeiten
  --model=ID       OpenRouter-Modell (Default: ${MODEL})
  --concurrency=N  Parallele Requests (Default: 3)
  --no-cache       Cache ignorieren und neu abfragen
  --data-file=P    Alternative JSON-Datei (für Tests)
  --help           Diese Hilfe anzeigen

Umgebungsvariablen:
  OPENROUTER_API_KEY   Erforderlich (außer bei --dry-run)
  OPENROUTER_MODEL     Optional, überschreibt --model
  OPENROUTER_BASE_URL  Optional, Default: https://openrouter.ai/api/v1`);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function isStringArray(value) {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((item) => isNonEmptyString(item))
  );
}

function isValidUrl(value) {
  if (!isNonEmptyString(value)) return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

/** Prüft ein vom LLM geliefertes Tool-Objekt. */
function validateTool(tool) {
  const errors = [];

  if (!tool || typeof tool !== "object" || Array.isArray(tool)) {
    return { ok: false, errors: ["kein Objekt"] };
  }

  for (const field of REQUIRED_TOOL_FIELDS) {
    if (!(field in tool)) errors.push(`"${field}" fehlt`);
  }

  if (!isNonEmptyString(tool.name)) errors.push('"name" ist leer');
  if (!isNonEmptyString(tool.description))
    errors.push('"description" ist leer');
  if (!isStringArray(tool.pros)) errors.push('"pros" ist kein String-Array');
  if (!isStringArray(tool.cons)) errors.push('"cons" ist kein String-Array');
  if (!isNonEmptyString(tool.bestFor)) errors.push('"bestFor" ist leer');
  if (!isValidUrl(tool.url)) errors.push('"url" ist keine gültige http(s)-URL');

  return { ok: errors.length === 0, errors };
}

/** Entfernt Markdown-Codefences und extrahiert das erste JSON-Objekt. */
function extractJson(text) {
  if (typeof text !== "string") return null;

  let cleaned = text.trim();
  cleaned = cleaned.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");

  try {
    return JSON.parse(cleaned);
  } catch {
    // Fallback: erstes { bis letztes }
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start === -1 || end === -1 || end <= start) return null;
    try {
      return JSON.parse(cleaned.slice(start, end + 1));
    } catch {
      return null;
    }
  }
}

// ---------------------------------------------------------------------------
// Cache
// ---------------------------------------------------------------------------

async function loadCache() {
  try {
    const raw = await readFile(cacheFile, "utf8");
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

async function saveCache(cache) {
  await mkdir(cacheDir, { recursive: true });
  await writeFile(cacheFile, `${JSON.stringify(cache, null, 2)}\n`, "utf8");
}

// ---------------------------------------------------------------------------
// OpenRouter
// ---------------------------------------------------------------------------

function buildPrompt(record, toolNames) {
  const original = record.details?.original ?? record.title;
  const category = record.category ?? "Software";

  return `Du bist ein sorgfältiger Software-Analyst. Für den Vergleich "${record.title}" (Kategorie: ${category}, Originalprodukt: ${original}) sollen diese Alternativen mit strukturierten Profilen ergänzt werden:

${toolNames.map((name, index) => `${index + 1}. ${name}`).join("\n")}

Gib ausschließlich gültiges JSON in exakt diesem Schema zurück:
{
  "alternatives": [
    {
      "name": "Exakter Tool-Name wie oben",
      "description": "Ein bis zwei sachliche Sätze auf Deutsch (max. 220 Zeichen).",
      "pros": ["Vorteil 1", "Vorteil 2", "Vorteil 3"],
      "cons": ["Nachteil 1", "Nachteil 2"],
      "bestFor": "Kurze Zielgruppen-/Einsatzbeschreibung auf Deutsch (max. 120 Zeichen).",
      "url": "https://offizielle-website.example"
    }
  ]
}

Regeln:
- Verwende für jedes genannte Tool genau einen Eintrag und behalte den Namen exakt bei.
- "pros" und "cons" enthalten je 2–4 kurze, konkrete Punkte.
- "url" ist die offizielle Website des Tools (keine Affiliate- oder Tracking-Links).
- Keine Erfindungen: Wenn du eine URL nicht sicher kennst, nutze die offizielle Domain des Herstellers.
- Keine Markdown-Codefences, kein erklärender Text außerhalb des JSON.`;
}

async function callOpenRouter({
  model,
  record,
  toolNames,
  attempt = 1,
  useJsonMode = true,
}) {
  const maxAttempts = 3;
  const body = {
    model,
    temperature: 0.2,
    messages: [
      {
        role: "system",
        content:
          "Du lieferst ausschließlich valides JSON. Keine Codefences, keine Kommentare.",
      },
      { role: "user", content: buildPrompt(record, toolNames) },
    ],
  };

  // Nicht jedes OpenRouter-Modell unterstützt response_format. Bei einem
  // 400er wird der Request einmal ohne JSON-Mode wiederholt.
  if (useJsonMode) body.response_format = { type: "json_object" };

  let response;
  try {
    response = await fetch(`${API_URL}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://flowmatrix.com",
        "X-Title": "FlowMatrix Data Enrichment",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(90_000),
    });
  } catch (err) {
    if (attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(
        `${c.yellow}  ↻ Netzwerkfehler (${err.message}), Retry in ${wait}ms${c.reset}`
      );
      await sleep(wait);
      return callOpenRouter({ model, record, toolNames, attempt: attempt + 1 });
    }
    throw err;
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "");

    // Modell unterstützt response_format nicht -> ohne JSON-Mode erneut.
    if (response.status === 400 && useJsonMode) {
      console.warn(
        `${c.yellow}  ↻ HTTP 400 – wiederhole ohne response_format${c.reset}`
      );
      return callOpenRouter({
        model,
        record,
        toolNames,
        attempt,
        useJsonMode: false,
      });
    }

    const retryable = response.status === 429 || response.status >= 500;
    if (retryable && attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(
        `${c.yellow}  ↻ HTTP ${response.status}, Retry in ${wait}ms${c.reset}`
      );
      await sleep(wait);
      return callOpenRouter({
        model,
        record,
        toolNames,
        attempt: attempt + 1,
        useJsonMode,
      });
    }
    throw new Error(
      `OpenRouter HTTP ${response.status}: ${text.slice(0, 300)}`
    );
  }

  const payload = await response.json();
  const content = payload?.choices?.[0]?.message?.content;
  const parsed = extractJson(content);

  if (!parsed || !Array.isArray(parsed.alternatives)) {
    if (attempt < maxAttempts) {
      console.warn(
        `${c.yellow}  ↻ Ungültiges JSON, Retry ${attempt + 1}/${maxAttempts}${c.reset}`
      );
      await sleep(1000 * attempt);
      return callOpenRouter({ model, record, toolNames, attempt: attempt + 1 });
    }
    throw new Error("LLM lieferte kein gültiges JSON mit 'alternatives'.");
  }

  return parsed.alternatives;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const opts = parseArgs(process.argv.slice(2));

  if (opts.help) {
    printHelp();
    return;
  }

  if (opts.dataFile) {
    dataFile = join(root, opts.dataFile);
  }

  if (!opts.dryRun && !API_KEY) {
    console.error(
      `${c.red}${c.bold}✖ OPENROUTER_API_KEY ist nicht gesetzt.${c.reset}\n` +
        `  Setze ihn mit: export OPENROUTER_API_KEY="sk-or-..."\n` +
        `  Oder nutze --dry-run für eine Vorschau.`
    );
    process.exit(1);
  }

  if (!existsSync(dataFile)) {
    console.error(`${c.red}✖ Datendatei nicht gefunden: ${dataFile}${c.reset}`);
    process.exit(1);
  }

  const raw = await readFile(dataFile, "utf8");
  let records;
  try {
    records = JSON.parse(raw);
  } catch (err) {
    console.error(`${c.red}✖ Ungültiges JSON: ${err.message}${c.reset}`);
    process.exit(1);
  }

  if (!Array.isArray(records)) {
    console.error(`${c.red}✖ Erwartet wird ein Array von Datensätzen.${c.reset}`);
    process.exit(1);
  }

  // 1. Kandidaten filtern: mindestens ein String in details.alternatives
  let candidates = records.filter((record) => {
    const list = record?.details?.alternatives;
    return Array.isArray(list) && list.some((item) => typeof item === "string");
  });

  if (opts.only) {
    const allowed = new Set(opts.only);
    candidates = candidates.filter((record) => allowed.has(record.slug));
  }

  candidates = candidates.slice(0, opts.limit);

  console.log(
    `${c.cyan}${c.bold}▶ Alternativen-Anreicherung${c.reset} ${c.dim}(${dataFile})${c.reset}`
  );
  console.log(
    `  Modell: ${c.bold}${opts.model}${c.reset} · Kandidaten: ${c.bold}${candidates.length}${c.reset}` +
      (opts.dryRun ? ` · ${c.yellow}DRY RUN${c.reset}` : "")
  );

  if (candidates.length === 0) {
    console.log(
      `${c.green}✔ Nichts zu tun – alle Alternativen sind bereits angereichert.${c.reset}`
    );
    return;
  }

  const cache = opts.useCache ? await loadCache() : {};
  const cacheDirty = { value: false };

  let updatedRecords = 0;
  let updatedTools = 0;
  let failedRecords = 0;
  const failures = [];

  // 2. Verarbeitung mit begrenzter Parallelität
  let cursor = 0;

  async function worker() {
    while (cursor < candidates.length) {
      const record = candidates[cursor++];
      const list = record.details.alternatives;
      const stringNames = list.filter((item) => typeof item === "string");

      console.log(
        `\n${c.bold}→ ${record.slug}${c.reset} ${c.dim}(${stringNames.length} Tool(s))${c.reset}`
      );

      if (opts.dryRun) {
        for (const name of stringNames) {
          console.log(`  ${c.dim}• würde anreichern:${c.reset} ${name}`);
        }
        continue;
      }

      // Cache-Treffer sammeln
      const generated = new Map();
      const missing = [];

      for (const name of stringNames) {
        const key = name.trim().toLowerCase();
        const cached = cache[key];
        if (cached && validateTool(cached).ok) {
          generated.set(key, cached);
          console.log(`  ${c.green}✓${c.reset} ${name} ${c.dim}(Cache)${c.reset}`);
        } else {
          missing.push(name);
        }
      }

      if (missing.length > 0) {
        try {
          const tools = await callOpenRouter({
            model: opts.model,
            record,
            toolNames: missing,
          });

          for (const tool of tools) {
            const validation = validateTool(tool);
            if (!validation.ok) {
              console.warn(
                `${c.yellow}  ⚠ ${tool?.name ?? "?"}: ${validation.errors.join(", ")}${c.reset}`
              );
              continue;
            }
            const key = tool.name.trim().toLowerCase();
            generated.set(key, tool);
            cache[key] = tool;
            cacheDirty.value = true;
            console.log(`  ${c.green}✓${c.reset} ${tool.name}`);
          }
        } catch (err) {
          failedRecords += 1;
          failures.push({ slug: record.slug, error: err.message });
          console.error(`${c.red}  ✖ Fehler: ${err.message}${c.reset}`);
          continue;
        }
      }

      // 3. Nur String-Einträge ersetzen, reiche Objekte unangetastet lassen
      let changed = 0;
      const nextList = list.map((item) => {
        if (typeof item !== "string") return item;
        const tool = generated.get(item.trim().toLowerCase());
        if (!tool) return item;
        changed += 1;
        return {
          name: tool.name,
          description: tool.description,
          pros: tool.pros,
          cons: tool.cons,
          bestFor: tool.bestFor,
          url: tool.url,
        };
      });

      if (changed > 0) {
        record.details.alternatives = nextList;
        updatedRecords += 1;
        updatedTools += changed;
        console.log(
          `  ${c.green}${c.bold}✔ ${changed} Tool(s) angereichert${c.reset}`
        );
      } else {
        console.warn(
          `${c.yellow}  ⚠ Keine gültigen Profile erhalten – Datensatz unverändert.${c.reset}`
        );
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(opts.concurrency, candidates.length) }, () =>
      worker()
    )
  );

  if (opts.dryRun) {
    console.log(
      `\n${c.yellow}${c.bold}Dry Run beendet – keine Datei geschrieben.${c.reset}`
    );
    return;
  }

  if (cacheDirty.value) {
    await saveCache(cache);
    console.log(`${c.dim}  Cache gespeichert: ${cacheFile}${c.reset}`);
  }

  if (updatedRecords === 0) {
    console.log(
      `\n${c.yellow}${c.bold}Keine Änderungen – Datei bleibt unverändert.${c.reset}`
    );
    if (failures.length > 0) {
      console.log(`${c.red}Fehlgeschlagene Datensätze:${c.reset}`);
      for (const f of failures) console.log(`  • ${f.slug}: ${f.error}`);
      process.exitCode = 1;
    }
    return;
  }

  // 4. Atomar zurückschreiben
  const tmpFile = `${dataFile}.tmp`;
  await writeFile(tmpFile, `${JSON.stringify(records, null, 2)}\n`, "utf8");
  await rename(tmpFile, dataFile);

  console.log(
    `\n${c.green}${c.bold}✔ Fertig: ${updatedTools} Tool(s) in ${updatedRecords} Datensatz/Datensätzen angereichert.${c.reset}`
  );
  console.log(`${c.dim}  Geschrieben: ${dataFile}${c.reset}`);

  if (failures.length > 0) {
    console.log(
      `\n${c.red}${c.bold}${failedRecords} Datensatz/Datensätze fehlgeschlagen:${c.reset}`
    );
    for (const f of failures) console.log(`  • ${f.slug}: ${f.error}`);
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(`${c.red}${c.bold}✖ Unerwarteter Fehler:${c.reset}`, err);
  process.exit(1);
});
