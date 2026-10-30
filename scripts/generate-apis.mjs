#!/usr/bin/env node
/**
 * generate-apis.mjs
 *
 * Erzeugt neue API-Datensätze für `src/data/apis.json` über die
 * OpenRouter-API.
 *
 * Qualitätssicherung:
 *   - Erzeugt pro Request GENAU EINEN API-Eintrag (sequenziell).
 *   - Validiert Pflichtfelder, Slug, Titel-/Description-Längen, Tags und
 *     die Details-Struktur.
 *   - Prüft, dass `website`, `docsUrl` und `endpoint` echte HTTPS-URLs ohne
 *     Platzhalter-Domains sind.
 *   - Erlaubt nur englische Inhalte (keine Umlaute/ß, keine deutschen
 *     Funktionswörter).
 *   - Verhindert Duplikate über Slug, Titel und Beschreibung.
 *   - Schreibt nach jedem erfolgreichen Eintrag atomar zurück.
 *
 * Verwendung:
 *   node scripts/generate-apis.mjs --dry-run
 *   node scripts/generate-apis.mjs --target=75 --limit=5
 *   node scripts/generate-apis.mjs --target=75 --limit=25
 *
 * Optionen:
 *   --dry-run        Nur Status anzeigen, keine API-Calls
 *   --target=N       Zielanzahl der APIs (Default: 75)
 *   --limit=N        Maximal N neue APIs in diesem Lauf (Default: 5)
 *   --model=ID       OpenRouter-Modell (Default: OPENROUTER_MODEL oder gpt-4o-mini)
 *   --help           Hilfe anzeigen
 */

import { readFile, writeFile, rename } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const apisFile = join(root, "src", "data", "apis.json");

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

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const PREFERRED_CATEGORIES = [
  "AI & LLM",
  "AI & Speech",
  "AI & Vision",
  "AI & Embeddings",
  "AI & Inference",
  "Vector Databases",
  "Payments",
  "Finance",
  "Backend",
  "Databases",
  "Auth & Identity",
  "Communication",
  "Email",
  "Messaging",
  "Search",
  "Analytics",
  "Observability",
  "DevOps",
  "Security",
  "E-commerce",
  "Productivity",
  "Geodata",
  "Weather",
  "Realtime",
  "Storage",
  "CRM",
  "Customer Support",
  "Developer Tools",
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
  [/\bbest\s+(?:api|solution|tool|platform)\b/i, "Superlativ best"],
  [/\bmarket[- ]leading\b/i, "Superlativ market-leading"],
  [/\{\{/, "Template-Platzhalter"],
];

const GERMAN_WORD_PATTERN =
  /\b(und|oder|für|mit|von|der|das|den|dem|des|eine|einen|ist|sind|wird|werden|nicht|auch|beim|zur|zum|durch|auf|aus|bei|nach|über|unter|zwischen|kann|müssen|sollte)\b/i;

const PLACEHOLDER_HOST_PATTERN =
  /(?:^|\.)(?:example\.(?:com|org|net)|localhost|127\.0\.0\.1|0\.0\.0\.0)$/i;

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
const isNonEmptyString = (value) =>
  typeof value === "string" && value.trim() !== "";

function parseArgs(argv) {
  const opts = {
    dryRun: false,
    target: 75,
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

  if (!Number.isFinite(opts.target) || opts.target < 1) opts.target = 75;
  if (!Number.isFinite(opts.limit) || opts.limit < 0) opts.limit = 5;

  return opts;
}

function printHelp() {
  console.log(`Verwendung: node scripts/generate-apis.mjs [Optionen]

Optionen:
  --dry-run        Nur Status anzeigen, keine API-Calls
  --target=N       Zielanzahl der APIs (Default: 75)
  --limit=N        Maximal N neue APIs in diesem Lauf (Default: 5)
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

function validateHttpsUrl(value, label, errors, required = false) {
  if (!isNonEmptyString(value)) {
    if (required) errors.push(`${label} fehlt`);
    return;
  }
  let url;
  try {
    url = new URL(value);
  } catch {
    errors.push(`${label} ist keine gültige URL: ${value}`);
    return;
  }
  if (url.protocol !== "https:") {
    errors.push(`${label} muss https sein: ${value}`);
  }
  if (PLACEHOLDER_HOST_PATTERN.test(url.hostname)) {
    errors.push(`${label} verwendet eine Platzhalter-Domain: ${url.hostname}`);
  }
}

/**
 * Prüft eine optionale HTTPS-URL, ohne Fehler zu pushen. Ungültige optionale
 * URLs (z. B. Azure-Endpoints mit <region>-Platzhalter) werden einfach
 * weggelassen, statt den gesamten API-Vorschlag zu verwerfen.
 */
function isValidHttpsUrl(value) {
  if (!isNonEmptyString(value)) return false;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:") return false;
    if (PLACEHOLDER_HOST_PATTERN.test(url.hostname)) return false;
    return true;
  } catch {
    return false;
  }
}

function buildPrompt({ apis, errors }) {
  const existingList = apis
    .map(
      (api) =>
        `- ${api.slug} | ${api.title} | ${api.category} | ${(api.tags ?? []).join(", ")}`
    )
    .join("\n");

  const categoryList = [
    ...new Set([
      ...PREFERRED_CATEGORIES,
      ...apis.map((api) => api.category).filter(Boolean),
    ]),
  ].join(", ");

  return `Du bist ein technischer Redakteur für FlowMatrix.dev und erstellst GENAU EINEN neuen API-Datensatz.

BESTEHENDE APIs (nicht duplizieren, kein gleiches Produkt):
${existingList}

BEVORZUGTE KATEGORIEN (wähle eine passende; wenn keine passt, eine kurze, konsistente Kategorie):
${categoryList}

AUFGABE
Wähle eine ECHTE, öffentlich dokumentierte API von einem etablierten Anbieter, die noch nicht in der Liste steht. Erfinde kein Produkt, keine Features und keine URLs. Wenn du dir bei einer Angabe nicht sicher bist, lass das optionale Feld weg.

Antworte ausschließlich mit gültigem JSON in exakt diesem Schema:
{
  "slug": "kebab-case-slug",
  "title": "Prägnanter API-Name (max. 60 Zeichen, max. 14 Wörter)",
  "description": "Ein bis zwei Sätze (50–160 Zeichen), endet mit Satzzeichen.",
  "category": "Eine Kategorie",
  "tags": ["tag1", "tag2", "tag3"],
  "details": {
    "provider": "Name des Anbieters",
    "pricing": "Konkrete Preisangabe oder Free-Tier-Hinweis",
    "features": ["Feature 1", "Feature 2", "Feature 3"],
    "useCase": "Ein bis zwei Sätze, wofür die API genutzt wird. Endet mit Satzzeichen.",
    "website": "https://echte-anbieter-website.tld",
    "endpoint": "https://echte-api-domain.tld/v1",
    "authentication": "z. B. Bearer API key",
    "apiKeyRequired": true,
    "sdkLanguages": ["JavaScript", "Python"],
    "rateLimit": "z. B. 100 requests/minute",
    "docsUrl": "https://echte-dokumentation.tld"
  }
}

REGELN
- Alle Texte müssen auf ENGLISCH sein. Keine deutschen Wörter, keine Umlaute, kein ß.
- "title": Der offizielle Produktname, keine Erfindung.
- "description": 50–160 Zeichen, endet mit einem Satzzeichen.
- "tags": 3–5 kurze, englische Schlagworte, keine Duplikate.
- "details.provider", "details.pricing", "details.useCase" sind Pflicht.
- "details.features": 3–5 konkrete, technische Features.
- "details.website" ist Pflicht und muss eine echte HTTPS-URL sein.
- "details.docsUrl" und "details.endpoint" sind optional, aber wenn vorhanden echte HTTPS-URLs.
- Keine Platzhalter-Domains (example.com, localhost, 127.0.0.1).
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
        "X-Title": "FlowMatrix API Generator",
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

function validateApi(candidate, existing) {
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
    errors.push('"slug" ist nicht kebab-case');
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

  const provider = normalize(details.provider);
  if (!provider) errors.push('"details.provider" fehlt');
  else {
    const providerCount = existing.providers?.get(provider) ?? 0;
    if (providerCount >= 4) {
      errors.push(
        `Zu viele APIs von "${provider}" (${providerCount}). Wähle einen anderen Anbieter für mehr Vielfalt.`
      );
    }
  }

  const pricing = normalize(details.pricing);
  if (!pricing) errors.push('"details.pricing" fehlt');

  const useCase = normalize(details.useCase);
  if (!useCase) errors.push('"details.useCase" fehlt');
  else {
    if (useCase.length < 30) errors.push('"details.useCase" ist zu kurz');
    if (!/[.!?]$/.test(useCase)) {
      errors.push('"details.useCase" endet nicht mit einem Satzzeichen');
    }
  }

  const features = Array.isArray(details.features)
    ? details.features.map(normalize).filter(Boolean)
    : [];
  if (features.length < 3 || features.length > 5) {
    errors.push('"details.features" muss 3–5 Einträge enthalten');
  }
  if (new Set(features.map((feature) => compact(feature))).size !== features.length) {
    errors.push('"details.features" enthält Duplikate');
  }

  validateHttpsUrl(details.website, '"details.website"', errors, true);

  // Optionale URLs: Bei ungültigem Wert oder Platzhalter (z. B. Azure
  // <region>-Endpoint) wird das Feld ausgelassen, statt den Datensatz zu
  // verwerfen. Die API bleibt so vollständig nutzbar.
  const docsUrl = isValidHttpsUrl(details.docsUrl)
    ? normalize(details.docsUrl)
    : null;
  const endpoint = isValidHttpsUrl(details.endpoint)
    ? normalize(details.endpoint)
    : null;

  const authentication = normalize(details.authentication);
  if (details.authentication !== undefined && !authentication) {
    errors.push('"details.authentication" ist leer');
  }

  const apiKeyRequired = details.apiKeyRequired;
  if (
    apiKeyRequired !== undefined &&
    typeof apiKeyRequired !== "boolean"
  ) {
    errors.push('"details.apiKeyRequired" muss ein Boolean sein');
  }

  const sdkLanguages = Array.isArray(details.sdkLanguages)
    ? details.sdkLanguages.map(normalize).filter(Boolean)
    : [];
  if (
    details.sdkLanguages !== undefined &&
    !Array.isArray(details.sdkLanguages)
  ) {
    errors.push('"details.sdkLanguages" muss ein Array sein');
  }
  if (sdkLanguages.length > 8) {
    errors.push('"details.sdkLanguages" enthält zu viele Einträge');
  }

  const rateLimit = normalize(details.rateLimit);
  if (details.rateLimit !== undefined && !rateLimit) {
    errors.push('"details.rateLimit" ist leer');
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

  const api = {
    slug,
    title,
    description,
    category,
    tags,
    details: {
      provider,
      pricing,
      features,
      useCase,
      website: normalize(details.website),
    },
  };

  if (authentication) api.details.authentication = authentication;
  if (typeof apiKeyRequired === "boolean") {
    api.details.apiKeyRequired = apiKeyRequired;
  }
  if (sdkLanguages.length > 0) api.details.sdkLanguages = sdkLanguages;
  if (rateLimit) api.details.rateLimit = rateLimit;
  if (endpoint) {
    api.details.endpoint = endpoint;
  }
  if (docsUrl) {
    api.details.docsUrl = docsUrl;
  }

  return { ok: true, errors: [], api };
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

  if (!existsSync(apisFile)) {
    console.error(`${c.red}✖ Datei nicht gefunden: ${apisFile}${c.reset}`);
    process.exit(1);
  }

  const apis = JSON.parse(await readFile(apisFile, "utf8"));
  if (!Array.isArray(apis)) {
    console.error(`${c.red}✖ apis.json muss ein Array sein.${c.reset}`);
    process.exit(1);
  }

  const target = Math.max(apis.length, opts.target);
  const missing = Math.max(0, target - apis.length);
  const toCreate = Math.min(opts.limit, missing);

  console.log(
    `${c.cyan}${c.bold}▶ API-Generator${c.reset} ${c.dim}(Modell: ${opts.model})${c.reset}`
  );
  console.log(
    `  Bestand: ${c.bold}${apis.length}${c.reset} · Ziel: ${c.bold}${target}${c.reset} · fehlend: ${c.bold}${missing}${c.reset} · dieser Lauf: ${c.bold}${toCreate}${c.reset}` +
      (opts.dryRun ? ` · ${c.yellow}DRY RUN${c.reset}` : "")
  );

  if (toCreate === 0) {
    console.log(
      `${c.green}✔ Ziel bereits erreicht – nichts zu tun.${c.reset}`
    );
    return;
  }

  if (opts.dryRun) {
    const prompt = buildPrompt({ apis, errors: [] });
    console.log(
      `\n${c.dim}Prompt-Vorschau (${prompt.length} Zeichen) – erste 1200 Zeichen:${c.reset}`
    );
    console.log(prompt.slice(0, 1200));
    console.log(
      `\n${c.yellow}${c.bold}Dry Run beendet – keine API-Calls, keine Datei geschrieben.${c.reset}`
    );
    return;
  }

  const providerCounts = new Map();
  for (const api of apis) {
    const provider = normalize(api.details?.provider);
    if (provider) {
      providerCounts.set(provider, (providerCounts.get(provider) ?? 0) + 1);
    }
  }

  const existing = {
    slugs: new Set(apis.map((api) => api.slug)),
    titles: new Set(apis.map((api) => compact(api.title))),
    descriptions: new Set(apis.map((api) => compact(api.description))),
    providers: providerCounts,
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
    const prompt = buildPrompt({ apis, errors: lastErrors });

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

    const validation = validateApi(candidate, existing);
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

    const api = validation.api;
    apis.push(api);
    existing.slugs.add(api.slug);
    existing.titles.add(compact(api.title));
    existing.descriptions.add(compact(api.description));
    const providerKey = normalize(api.details.provider);
    existing.providers.set(
      providerKey,
      (existing.providers.get(providerKey) ?? 0) + 1
    );
    created += 1;
    consecutiveFailures = 0;
    lastErrors = [];

    const tmpFile = `${apisFile}.tmp`;
    await writeFile(
      tmpFile,
      `${JSON.stringify(apis, null, 2)}\n`,
      "utf8"
    );
    await rename(tmpFile, apisFile);

    console.log(
      `  ${c.green}✓${c.reset} ${api.slug} – ${api.title} ${c.dim}(${api.category}, ${api.details.features.length} Features)${c.reset}`
    );
    console.log(
      `  ${c.dim}  Fortschritt: ${apis.length}/${target}${c.reset}`
    );
  }

  console.log("");
  if (created === 0) {
    console.error(`${c.red}${c.bold}✖ Keine APIs erzeugt.${c.reset}`);
    process.exitCode = 1;
    return;
  }

  console.log(
    `${c.green}${c.bold}✔ Fertig: ${created} neue APIs erzeugt, ${apis.length} insgesamt.${c.reset}`
  );
  if (apis.length < target) {
    console.log(
      `${c.yellow}  Hinweis: Ziel ${target} noch nicht erreicht. Erneut ausführen, um weitere APIs zu erzeugen.${c.reset}`
    );
  }
  console.log(`${c.dim}  Geschrieben: ${apisFile}${c.reset}`);
}

main().catch((error) => {
  console.error(
    `${c.red}${c.bold}✖ Unerwarteter Fehler:${c.reset}`,
    error
  );
  process.exit(1);
});
