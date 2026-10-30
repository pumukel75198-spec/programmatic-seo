#!/usr/bin/env node
/**
 * generate-alternatives.mjs
 *
 * Erzeugt neue Alternatives-Datensätze für `src/data/alternatives.json`
 * über die OpenRouter-API.
 *
 * Qualitätssicherung:
 *   - Erzeugt pro Request GENAU EINEN Alternatives-Eintrag (sequenziell).
 *   - Validiert Slug (`*-alternatives`), Titel, Beschreibung, Tags und die
 *     Details-Struktur.
 *   - Prüft, dass 3–5 echte, eindeutige Alternativen genannt werden.
 *   - Erlaubt nur englische Inhalte (keine Umlaute/ß, keine deutschen
 *     Funktionswörter).
 *   - Verhindert Duplikate über Slug, Titel und Beschreibung.
 *   - Schreibt nach jedem erfolgreichen Eintrag atomar zurück.
 *
 * Die eigentlichen Alternativen liegen zunächst als Strings vor. Anschließend
 * reichert `scripts/enrich-alternatives.mjs` sie um Beschreibung, Pros/Cons,
 * Best-for und URL an.
 *
 * Verwendung:
 *   node scripts/generate-alternatives.mjs --dry-run
 *   node scripts/generate-alternatives.mjs --target=60 --limit=6
 *   node scripts/generate-alternatives.mjs --target=60 --limit=24 --model=openai/gpt-4o
 */

import { readFile, writeFile, rename } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const alternativesFile = join(root, "src", "data", "alternatives.json");

try {
  process.loadEnvFile(join(root, ".env"));
} catch {
  /* Keine .env vorhanden – Shell-Variablen gelten. */
}

const API_URL =
  process.env.OPENROUTER_BASE_URL?.replace(/\/$/, "") ??
  "https://openrouter.ai/api/v1";
const MODEL = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini";
const API_KEY = process.env.OPENROUTER_API_KEY;

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*-alternatives$/;

const PREFERRED_CATEGORIES = [
  "Productivity",
  "Automation",
  "Design",
  "Communication",
  "Databases",
  "Marketing",
  "Project Management",
  "Analytics",
  "CRM & Marketing",
  "Storage",
  "Scheduling",
  "CMS",
  "E-commerce",
  "Collaboration",
  "Support",
  "DevOps",
  "Hosting",
  "AI & LLM",
  "Payments",
  "Backend",
  "Developer Tools",
  "Auth & Identity",
  "Search",
  "AI & Speech",
  "Vector Databases",
  "Finance",
  "Security",
  "Observability",
];

const FORBIDDEN_PATTERNS = [
  [/lorem\s+ipsum/i, "Lorem Ipsum"],
  [/\bTODO\b/i, "TODO"],
  [/\bTBD\b/i, "TBD"],
  [/\bundefined\b/i, "undefined"],
  [/\bNaN\b/, "NaN"],
  [/\b100\s*%/i, "unbelegte 100%-Aussage"],
  [/\bguarantee(?:d|s)?\b/i, "Garantieversprechen"],
  [/\bworld[- ]class\b/i, "Superlativ world-class"],
  [/\bbest\s+(?:tool|solution|platform)\b/i, "Superlativ best"],
  [/\bmarket[- ]leading\b/i, "Superlativ market-leading"],
  [/\{\{/, "Template-Platzhalter"],
];

const GERMAN_WORD_PATTERN =
  /\b(und|oder|für|mit|von|der|das|den|dem|des|eine|einen|ist|sind|wird|werden|nicht|auch|beim|zur|zum|durch|auf|aus|bei|nach|über|unter|zwischen|kann|müssen|sollte)\b/i;

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const normalize = (value) => String(value ?? "").replace(/\s+/g, " ").trim();
const compact = (value) => normalize(value).replace(/\s+/g, "").toLowerCase();
const wordCount = (value) => {
  const text = normalize(value);
  return text ? text.split(/\s+/).length : 0;
};

function parseArgs(argv) {
  const opts = {
    dryRun: false,
    target: 60,
    limit: 5,
    model: MODEL,
    help: false,
  };

  for (const arg of argv) {
    if (arg === "--dry-run") opts.dryRun = true;
    else if (arg === "--help" || arg === "-h") opts.help = true;
    else if (arg.startsWith("--target=")) opts.target = Number(arg.slice(9));
    else if (arg.startsWith("--limit=")) opts.limit = Number(arg.slice(8));
    else if (arg.startsWith("--model=")) opts.model = arg.slice(8);
    else {
      console.error(`Unbekannte Option: ${arg}`);
      process.exit(1);
    }
  }

  if (!Number.isFinite(opts.target) || opts.target < 1) opts.target = 60;
  if (!Number.isFinite(opts.limit) || opts.limit < 0) opts.limit = 5;

  return opts;
}

function printHelp() {
  console.log(`Verwendung: node scripts/generate-alternatives.mjs [Optionen]

Optionen:
  --dry-run        Nur Status anzeigen, keine API-Calls
  --target=N       Zielanzahl der Alternatives (Default: 60)
  --limit=N        Maximal N neue Alternatives in diesem Lauf (Default: 5)
  --model=ID       OpenRouter-Modell (Default: ${MODEL})
  --help           Hilfe anzeigen

Umgebungsvariablen:
  OPENROUTER_API_KEY   Erforderlich (außer bei --dry-run)
  OPENROUTER_MODEL     Optional, überschreibt --model
  OPENROUTER_BASE_URL  Optional, Default: https://openrouter.ai/api/v1`);
}

function extractJson(text) {
  if (typeof text !== "string") return null;
  let cleaned = text.trim();
  cleaned = cleaned.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  try {
    return JSON.parse(cleaned);
  } catch {
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

function buildPrompt({ alternatives, errors }) {
  const existingList = alternatives
    .map(
      (entry) =>
        `- ${entry.slug} | ${entry.title} | ${entry.category} | original: ${entry.details?.original ?? "?"}`
    )
    .join("\n");

  const categoryList = [
    ...new Set([
      ...PREFERRED_CATEGORIES,
      ...alternatives.map((entry) => entry.category).filter(Boolean),
    ]),
  ].join(", ");

  return `Du bist ein technischer Redakteur für FlowMatrix.dev und erstellst GENAU EINEN neuen Alternatives-Datensatz.

BESTEHENDE ALTERNATIVES (nicht duplizieren, kein gleiches Original-Tool):
${existingList}

BEVORZUGTE KATEGORIEN (wähle eine passende; wenn keine passt, eine kurze, konsistente Kategorie):
${categoryList}

AUFGABE
Wähle ein ECHTES, bekanntes Software-Tool, für das es noch keine Alternatives-Seite gibt. Nenne 3–5 ECHTE Alternativen zu diesem Tool. Erfinde keine Produkte, keine Features und keine URLs.

Antworte ausschließlich mit gültigem JSON in exakt diesem Schema:
{
  "slug": "tool-name-alternatives",
  "title": "Tool Name Alternatives",
  "description": "Ein bis zwei Sätze (50–160 Zeichen), endet mit Satzzeichen.",
  "category": "Eine Kategorie",
  "tags": ["tag1", "tag2", "tag3"],
  "details": {
    "original": "Exakter Name des Original-Tools",
    "alternatives": ["Alternative 1", "Alternative 2", "Alternative 3"],
    "bestFor": "Für wen die Alternativen besonders geeignet sind. Endet mit Satzzeichen.",
    "pricing": "Preisspanne oder Free-Tier-Hinweis",
    "features": ["Feature 1", "Feature 2", "Feature 3"]
  }
}

REGELN
- Alle Texte müssen auf ENGLISCH sein. Keine deutschen Wörter, keine Umlaute, kein ß.
- "slug" ist kebab-case und endet exakt auf "-alternatives".
- "title" endet exakt auf "Alternatives" und ist maximal 60 Zeichen lang.
- "description": 50–160 Zeichen, endet mit einem Satzzeichen.
- "tags": 3–5 kurze, englische Schlagworte, keine Duplikate.
- "details.original": exakter Name des Original-Tools.
- "details.alternatives": 3–5 echte, unterschiedliche Tool-Namen als Strings. Keine URLs, keine Beschreibungen.
- "details.bestFor" und "details.pricing" sind Pflicht.
- "details.features": 3–5 konkrete Features der Alternativen.
- Keine unbelegten Superlative, keine Garantien, keine Prozentangaben, kein "100 %".
- Kein Lorem Ipsum, kein TODO, kein TBD, kein undefined, kein NaN.
- Keine Markdown-Codefences, kein Text außerhalb des JSON.
${
  errors && errors.length
    ? `\nKORREKTURHINWEISE (behebe diese Fehler):\n- ${errors.join("\n- ")}`
    : ""
}`;
}

async function callOpenRouter({ prompt, model, attempt = 1, useJsonMode = true }) {
  const maxAttempts = 3;
  const body = {
    model,
    temperature: 0.7,
    messages: [
      {
        role: "system",
        content:
          "Du bist ein präziser technischer Redakteur und lieferst ausschließlich valides JSON auf Englisch.",
      },
      { role: "user", content: prompt },
    ],
  };

  if (useJsonMode) body.response_format = { type: "json_object" };

  let response;
  try {
    response = await fetch(`${API_URL}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://flowmatrix.dev",
        "X-Title": "FlowMatrix Alternatives Generator",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(180_000),
    });
  } catch (error) {
    if (attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(
        `${c.yellow}  ↻ Netzwerkfehler (${error.message}), Retry in ${wait}ms${c.reset}`
      );
      await sleep(wait);
      return callOpenRouter({ prompt, model, attempt: attempt + 1, useJsonMode });
    }
    throw error;
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "");

    if (response.status === 400 && useJsonMode) {
      console.warn(
        `${c.yellow}  ↻ HTTP 400 – wiederhole ohne response_format${c.reset}`
      );
      return callOpenRouter({
        prompt,
        model,
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
        prompt,
        model,
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

  if (!parsed) {
    if (attempt < maxAttempts) {
      console.warn(
        `${c.yellow}  ↻ Ungültiges JSON, Retry ${attempt + 1}/${maxAttempts}${c.reset}`
      );
      await sleep(1000 * attempt);
      return callOpenRouter({
        prompt,
        model,
        attempt: attempt + 1,
        useJsonMode,
      });
    }
    throw new Error("LLM lieferte kein gültiges JSON.");
  }

  if (Array.isArray(parsed)) return parsed[0] ?? null;
  return parsed;
}

function validateAlternatives(candidate, existing) {
  const errors = [];

  if (
    !candidate ||
    typeof candidate !== "object" ||
    Array.isArray(candidate)
  ) {
    return { ok: false, errors: ["Antwort ist kein Objekt"] };
  }

  const slug = normalize(candidate.slug);
  if (!SLUG_PATTERN.test(slug)) {
    errors.push('"slug" muss kebab-case sein und auf "-alternatives" enden');
  } else if (existing.slugs.has(slug)) {
    errors.push(`"slug" existiert bereits: ${slug}`);
  }

  const title = normalize(candidate.title);
  if (!title) errors.push('"title" fehlt');
  else {
    if (title.length > 60) {
      errors.push(`"title" ist zu lang (${title.length} > 60 Zeichen)`);
    }
    if (wordCount(title) > 14) {
      errors.push(`"title" hat zu viele Wörter (${wordCount(title)} > 14)`);
    }
    if (!/^[A-Z0-9]/.test(title)) {
      errors.push('"title" beginnt nicht mit einem Großbuchstaben');
    }
    if (!/alternatives$/i.test(title)) {
      errors.push('"title" muss auf "Alternatives" enden');
    }
    if (existing.titles.has(compact(title))) {
      errors.push(`"title" existiert bereits: ${title}`);
    }
  }

  const description = normalize(candidate.description);
  if (!description) errors.push('"description" fehlt');
  else {
    if (description.length < 50) {
      errors.push(
        `"description" ist zu kurz (${description.length} < 50 Zeichen)`
      );
    }
    if (description.length > 160) {
      errors.push(
        `"description" ist zu lang (${description.length} > 160 Zeichen)`
      );
    }
    if (!/[.!?]$/.test(description)) {
      errors.push('"description" endet nicht mit einem Satzzeichen');
    }
    if (compact(description) === compact(title)) {
      errors.push('"description" wiederholt nur den Titel');
    }
    if (existing.descriptions.has(compact(description))) {
      errors.push('"description" existiert bereits');
    }
  }

  const category = normalize(candidate.category);
  if (!category) errors.push('"category" fehlt');
  else if (category.length > 40) errors.push('"category" ist zu lang');

  const tags = Array.isArray(candidate.tags)
    ? candidate.tags.map(normalize).filter(Boolean)
    : [];
  if (tags.length < 3 || tags.length > 5) {
    errors.push('"tags" muss 3–5 Einträge enthalten');
  }
  if (new Set(tags.map((tag) => tag.toLowerCase())).size !== tags.length) {
    errors.push('"tags" enthält Duplikate');
  }
  if (tags.some((tag) => !/^[a-z0-9][a-z0-9 &/+.-]*$/i.test(tag))) {
    errors.push('"tags" enthält ungültige Zeichen');
  }

  const details =
    candidate.details &&
    typeof candidate.details === "object" &&
    !Array.isArray(candidate.details)
      ? candidate.details
      : null;

  if (!details) {
    return { ok: false, errors: [...errors, '"details" fehlt'] };
  }

  const original = normalize(details.original);
  if (!original) errors.push('"details.original" fehlt');
  else if (compact(original) === compact(title.replace(/\s+alternatives$/i, ""))) {
    // Der Originalname darf im Titel stecken; das ist erwartet.
  }

  const alternatives = Array.isArray(details.alternatives)
    ? details.alternatives.map(normalize).filter(Boolean)
    : [];
  if (alternatives.length < 3 || alternatives.length > 5) {
    errors.push('"details.alternatives" muss 3–5 Einträge enthalten');
  }
  if (
    new Set(alternatives.map((name) => compact(name))).size !==
    alternatives.length
  ) {
    errors.push('"details.alternatives" enthält Duplikate');
  }
  if (
    original &&
    alternatives.some((name) => compact(name) === compact(original))
  ) {
    errors.push('"details.alternatives" darf das Original-Tool nicht enthalten');
  }
  if (
    alternatives.some((name) => /https?:\/\//i.test(name))
  ) {
    errors.push('"details.alternatives" darf keine URLs enthalten');
  }

  const bestFor = normalize(details.bestFor);
  if (!bestFor) errors.push('"details.bestFor" fehlt');
  else if (!/[.!?]$/.test(bestFor)) {
    errors.push('"details.bestFor" endet nicht mit einem Satzzeichen');
  }

  const pricing = normalize(details.pricing);
  if (!pricing) errors.push('"details.pricing" fehlt');

  const features = Array.isArray(details.features)
    ? details.features.map(normalize).filter(Boolean)
    : [];
  if (features.length < 3 || features.length > 5) {
    errors.push('"details.features" muss 3–5 Einträge enthalten');
  }
  if (
    new Set(features.map((feature) => compact(feature))).size !==
    features.length
  ) {
    errors.push('"details.features" enthält Duplikate');
  }

  const serialized = JSON.stringify(candidate);
  for (const [pattern, label] of FORBIDDEN_PATTERNS) {
    if (pattern.test(serialized)) {
      errors.push(`Verbotener Inhalt: ${label}`);
    }
  }

  if (/[äöüß]/i.test(serialized)) {
    errors.push("Deutsche Umlaute/ß gefunden – alle Inhalte müssen englisch sein");
  }
  if (GERMAN_WORD_PATTERN.test(serialized)) {
    const match = serialized.match(GERMAN_WORD_PATTERN);
    errors.push(
      `Deutsches Wort gefunden: "${match?.[0] ?? ""}" – alle Inhalte müssen englisch sein`
    );
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    errors: [],
    entry: {
      slug,
      title,
      description,
      category,
      tags,
      details: {
        original,
        alternatives,
        bestFor,
        pricing,
        features,
      },
    },
  };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));

  if (opts.help) {
    printHelp();
    return;
  }

  if (!opts.dryRun && !API_KEY) {
    console.error(
      `${c.red}${c.bold}✖ OPENROUTER_API_KEY ist nicht gesetzt.${c.reset}\n` +
        "  Setze ihn in .env oder als Umgebungsvariable."
    );
    process.exit(1);
  }

  if (!existsSync(alternativesFile)) {
    console.error(
      `${c.red}✖ Datei nicht gefunden: ${alternativesFile}${c.reset}`
    );
    process.exit(1);
  }

  const alternatives = JSON.parse(
    await readFile(alternativesFile, "utf8")
  );
  if (!Array.isArray(alternatives)) {
    console.error(
      `${c.red}✖ alternatives.json muss ein Array sein.${c.reset}`
    );
    process.exit(1);
  }

  const target = Math.max(alternatives.length, opts.target);
  const missing = Math.max(0, target - alternatives.length);
  const toCreate = Math.min(opts.limit, missing);

  console.log(
    `${c.cyan}${c.bold}▶ Alternatives-Generator${c.reset} ${c.dim}(Modell: ${opts.model})${c.reset}`
  );
  console.log(
    `  Bestand: ${c.bold}${alternatives.length}${c.reset} · Ziel: ${c.bold}${target}${c.reset} · fehlend: ${c.bold}${missing}${c.reset} · dieser Lauf: ${c.bold}${toCreate}${c.reset}` +
      (opts.dryRun ? ` · ${c.yellow}DRY RUN${c.reset}` : "")
  );

  if (toCreate === 0) {
    console.log(
      `${c.green}✔ Ziel bereits erreicht – nichts zu tun.${c.reset}`
    );
    return;
  }

  if (opts.dryRun) {
    const prompt = buildPrompt({ alternatives, errors: [] });
    console.log(
      `\n${c.dim}Prompt-Vorschau (${prompt.length} Zeichen) – erste 1200 Zeichen:${c.reset}`
    );
    console.log(prompt.slice(0, 1200));
    console.log(
      `\n${c.yellow}${c.bold}Dry Run beendet – keine API-Calls, keine Datei geschrieben.${c.reset}`
    );
    return;
  }

  const existing = {
    slugs: new Set(alternatives.map((entry) => entry.slug)),
    titles: new Set(alternatives.map((entry) => compact(entry.title))),
    descriptions: new Set(
      alternatives.map((entry) => compact(entry.description))
    ),
  };

  let created = 0;
  let consecutiveFailures = 0;
  let totalAttempts = 0;
  const maxTotalAttempts = toCreate * 6;
  const maxConsecutiveFailures = Math.max(6, toCreate * 2);
  let lastErrors = [];

  while (
    created < toCreate &&
    consecutiveFailures < maxConsecutiveFailures &&
    totalAttempts < maxTotalAttempts
  ) {
    totalAttempts += 1;
    const prompt = buildPrompt({ alternatives, errors: lastErrors });

    console.log(
      `\n${c.bold}→ Vorschlag ${created + 1}/${toCreate}${c.reset} ${c.dim}(Versuch ${totalAttempts})${c.reset}`
    );

    let candidate;
    try {
      candidate = await callOpenRouter({ prompt, model: opts.model });
    } catch (error) {
      consecutiveFailures += 1;
      lastErrors = [];
      console.error(`${c.red}  ✖ ${error.message}${c.reset}`);
      continue;
    }

    const validation = validateAlternatives(candidate, existing);
    if (!validation.ok) {
      consecutiveFailures += 1;
      lastErrors = validation.errors;
      console.warn(
        `${c.yellow}  ↻ Vorschlag verworfen (${validation.errors.length} Fehler)${c.reset}`
      );
      for (const error of validation.errors.slice(0, 8)) {
        console.warn(`      ${c.yellow}• ${error}${c.reset}`);
      }
      continue;
    }

    const entry = validation.entry;
    alternatives.push(entry);
    existing.slugs.add(entry.slug);
    existing.titles.add(compact(entry.title));
    existing.descriptions.add(compact(entry.description));
    created += 1;
    consecutiveFailures = 0;
    lastErrors = [];

    const tmpFile = `${alternativesFile}.tmp`;
    await writeFile(
      tmpFile,
      `${JSON.stringify(alternatives, null, 2)}\n`,
      "utf8"
    );
    await rename(tmpFile, alternativesFile);

    console.log(
      `  ${c.green}✓${c.reset} ${entry.slug} – ${entry.title} ${c.dim}(${entry.category}, ${entry.details.alternatives.length} Alternativen)${c.reset}`
    );
    console.log(
      `  ${c.dim}  Fortschritt: ${alternatives.length}/${target}${c.reset}`
    );
  }

  console.log("");
  if (created === 0) {
    console.error(
      `${c.red}${c.bold}✖ Keine Alternatives erzeugt.${c.reset}`
    );
    process.exitCode = 1;
    return;
  }

  console.log(
    `${c.green}${c.bold}✔ Fertig: ${created} neue Alternatives erzeugt, ${alternatives.length} insgesamt.${c.reset}`
  );
  if (alternatives.length < target) {
    console.log(
      `${c.yellow}  Hinweis: Ziel ${target} noch nicht erreicht. Erneut ausführen, um weitere Einträge zu erzeugen.${c.reset}`
    );
  }
  console.log(`${c.dim}  Geschrieben: ${alternativesFile}${c.reset}`);
  console.log(
    `${c.dim}  Nächster Schritt: node scripts/enrich-alternatives.mjs${c.reset}`
  );
}

main().catch((error) => {
  console.error(
    `${c.red}${c.bold}✖ Unerwarteter Fehler:${c.reset}`,
    error
  );
  process.exit(1);
});
