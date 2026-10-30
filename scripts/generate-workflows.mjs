#!/usr/bin/env node
/**
 * generate-workflows.mjs
 *
 * Erzeugt neue, eigenständige Workflow-Datensätze für `src/data/workflows.json`
 * über die OpenRouter-API.
 *
 * Wichtige Eigenschaften:
 *   - Erzeugt pro Request GENAU EINEN Workflow (sequenziell), damit die
 *     Deduplizierung zuverlässig bleibt.
 *   - Validiert jeden Vorschlag gegen die Limits der PDF-Qualitätsprüfung
 *     (`check-pdf-quality.mjs`), damit die später generierten PDFs nicht am
 *     Gate scheitern.
 *   - Erlaubt ausschließlich Tools, die in `src/data/partner.json` existieren.
 *   - Steps werden als Objekte mit `title`, `description` und leerem
 *     `links`-Array angelegt. Die Detail-Anreicherung (actions, checklist,
 *     expectedResult, commands, config) übernimmt anschließend
 *     `enrich-workflow-details.mjs`.
 *   - Schreibt nach jedem erfolgreichen Workflow atomar zurück.
 *
 * Verwendung:
 *   node scripts/generate-workflows.mjs --dry-run
 *   node scripts/generate-workflows.mjs --target=60 --limit=6
 *   node scripts/generate-workflows.mjs --target=60 --limit=24
 *
 * Optionen:
 *   --dry-run        Nur Prompt/Status anzeigen, keine API-Calls
 *   --target=N       Zielanzahl der Workflows (Default: 60)
 *   --limit=N        Maximal N neue Workflows in diesem Lauf (Default: 5)
 *   --model=ID       OpenRouter-Modell (Default: OPENROUTER_MODEL oder gpt-4o-mini)
 *   --help           Hilfe anzeigen
 */

import { readFile, writeFile, rename } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const workflowsFile = join(root, "src", "data", "workflows.json");
const partnerFile = join(root, "src", "data", "partner.json");

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
  "Content & SEO",
  "Sales & CRM",
  "Marketing & Automation",
  "Support & AI",
  "Data & Engineering",
  "Finance & Operations",
  "E-commerce",
  "Productivity & Collaboration",
  "Analytics & Monitoring",
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
  [/\bbest\s+(?:solution|tool|platform)\b/i, "Superlativ best solution"],
  [/\bmarket[- ]leading\b/i, "Superlativ market-leading"],
  [/\bapi\.openai\.com\/v1\/engines\b/i, "veralteter OpenAI-Endpunkt"],
  [/\bapi\.openai\.com\/v1\/completions\b/i, "veralteter OpenAI-Completions-Endpunkt"],
  [/\btext-davinci\b/i, "veraltetes Modell text-davinci"],
  [/\bgpt-3\.5-turbo\b/i, "veraltetes Modell gpt-3.5-turbo"],
  [/\bnpm init astro\b/i, "veralteter Befehl npm init astro"],
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
const isNonEmptyString = (value) =>
  typeof value === "string" && value.trim() !== "";

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
  console.log(`Verwendung: node scripts/generate-workflows.mjs [Optionen]

Optionen:
  --dry-run        Nur Status anzeigen, keine API-Calls
  --target=N       Zielanzahl der Workflows (Default: 60)
  --limit=N        Maximal N neue Workflows in diesem Lauf (Default: 5)
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

function buildPrompt({ workflows, tools, errors }) {
  const existingList = workflows
    .map(
      (workflow) =>
        `- ${workflow.slug} | ${workflow.title} | ${workflow.category} | ${(workflow.tags ?? []).join(", ")}`
    )
    .join("\n");

  const categoryList = [
    ...new Set([
      ...PREFERRED_CATEGORIES,
      ...workflows.map((workflow) => workflow.category).filter(Boolean),
    ]),
  ].join(", ");

  const recentList = workflows
    .slice(-6)
    .map((workflow) => `- ${workflow.title} (${workflow.category})`)
    .join("\n");

  const automatedCount = workflows.filter((workflow) =>
    /^Automated\b/i.test(workflow.title)
  ).length;

  const automatedRule =
    automatedCount >= 5
      ? 'Beginne den Titel NICHT mit "Automated". Wähle eine konkrete, andere Formulierung.'
      : "";

  return `Du bist ein technischer Redakteur für FlowMatrix.dev und erstellst GENAU EINEN neuen, eigenständigen Workflow-Datensatz.

BESTEHENDE WORKFLOWS (nicht duplizieren, kein gleiches Thema):
${existingList}

ZULETZT ERZEUGT (besonders nicht duplizieren):
${recentList}

VERFÜGBARE TOOLS (verwende ausschließlich diese exakten Namen):
${tools.join(", ")}

BEVORZUGTE KATEGORIEN (wähle eine passende; wenn keine passt, eine kurze, konsistente Kategorie):
${categoryList}

AUFGABE
Erfinde einen konkreten, praxisnahen Automatisierungs-Workflow, der noch nicht in der Liste steht. Der Workflow muss für Entwickler, SEO-Teams oder moderne Softwareteams relevant sein und sich klar von den bestehenden unterscheiden.

Antworte ausschließlich mit gültigem JSON in exakt diesem Schema:
{
  "slug": "kebab-case-slug",
  "title": "Prägnanter Titel (max. 60 Zeichen, max. 14 Wörter)",
  "description": "Ein bis zwei Sätze (50–160 Zeichen), endet mit Satzzeichen.",
  "category": "Eine Kategorie",
  "tags": ["tag1", "tag2", "tag3"],
  "details": {
    "difficulty": "Beginner | Intermediate | Advanced",
    "duration": "z. B. 30–45 minutes",
    "tools": ["Exakter ToolName aus der Liste"],
    "steps": [
      {
        "title": "Konkreter Schritt-Titel",
        "description": "2–4 Sätze, 80–300 Zeichen, endet mit Satzzeichen.",
        "links": []
      }
    ],
    "useCase": "Ein bis zwei Sätze, was der Workflow löst. Endet mit Satzzeichen."
  }
}

REGELN
- Alle Texte müssen auf ENGLISCH sein. Keine deutschen Wörter, keine Umlaute, kein ß.
${automatedRule ? `- ${automatedRule}\n` : ""}- Bevorzuge Workflows, die APIs oder Alternativen aus der Tool-Liste sinnvoll kombinieren.
- Wähle ein Thema, das sich klar von den zuletzt erzeugten Workflows unterscheidet.
- "steps": 4–6 Schritte. Jeder Schritt ist ein Objekt mit title, description und einem leeren links-Array.
- "tools": 1–3 Tools, ausschließlich exakte Namen aus der verfügbaren Liste. Verteile sie sinnvoll über die Schritte.
- "tags": 3–5 kurze, englische Schlagworte, keine Duplikate.
- "difficulty": exakt Beginner, Intermediate oder Advanced.
- Keine erfundenen URLs, keine Links in den Steps.
- Keine unbelegten Superlative, keine Garantien, keine Prozentangaben, kein "100 %".
- Keine veralteten Modelle/Endpunkte (kein text-davinci, kein gpt-3.5-turbo, kein /v1/engines, kein /v1/completions).
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
    temperature: 0.8,
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
        "X-Title": "FlowMatrix Workflow Generator",
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

function validateWorkflow(candidate, existing, partner) {
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

  const difficulty = normalize(details.difficulty);
  if (!["Beginner", "Intermediate", "Advanced"].includes(difficulty)) {
    errors.push(
      '"details.difficulty" muss Beginner, Intermediate oder Advanced sein'
    );
  }

  const duration = normalize(details.duration);
  if (!duration) errors.push('"details.duration" fehlt');
  else if (duration.length > 40) errors.push('"details.duration" ist zu lang');

  const useCase = normalize(details.useCase);
  if (!useCase) errors.push('"details.useCase" fehlt');
  else {
    if (useCase.length < 30) errors.push('"details.useCase" ist zu kurz');
    if (!/[.!?]$/.test(useCase)) {
      errors.push('"details.useCase" endet nicht mit einem Satzzeichen');
    }
  }

  const tools = Array.isArray(details.tools)
    ? details.tools.map(normalize).filter(Boolean)
    : [];
  if (tools.length < 1) errors.push('"details.tools" fehlt');
  if (tools.length > 3) errors.push('"details.tools" darf maximal 3 Tools enthalten');
  if (new Set(tools).size !== tools.length) {
    errors.push('"details.tools" enthält Duplikate');
  }
  for (const tool of tools) {
    if (!(tool in partner)) {
      errors.push(`Tool "${tool}" fehlt in partner.json`);
    }
  }

  const rawSteps = Array.isArray(details.steps) ? details.steps : [];
  if (rawSteps.length < 3) {
    errors.push('"details.steps" benötigt mindestens 3 Schritte');
  }
  if (rawSteps.length > 8) {
    errors.push('"details.steps" darf maximal 8 Schritte enthalten');
  }

  const seenStepTitles = new Set();
  const steps = [];

  rawSteps.forEach((step, index) => {
    const label = `Step ${index + 1}`;
    if (!step || typeof step !== "object" || Array.isArray(step)) {
      errors.push(`${label}: ist kein Objekt`);
      return;
    }

    const stepTitle = normalize(step.title);
    const stepDescription = normalize(step.description);

    if (!stepTitle) errors.push(`${label}: "title" fehlt`);
    else {
      if (stepTitle.length > 90) {
        errors.push(`${label}: "title" ist zu lang`);
      }
      const words = wordCount(stepTitle);
      if (words < 2 || words > 14) {
        errors.push(`${label}: "title" muss 2–14 Wörter haben`);
      }
      if (!/^[A-Z0-9]/.test(stepTitle)) {
        errors.push(`${label}: "title" beginnt nicht mit einem Großbuchstaben`);
      }
      if (seenStepTitles.has(compact(stepTitle))) {
        errors.push(`${label}: doppelter "title"`);
      }
      seenStepTitles.add(compact(stepTitle));
    }

    if (!stepDescription) errors.push(`${label}: "description" fehlt`);
    else {
      if (stepDescription.length < 25) {
        errors.push(`${label}: "description" ist zu kurz`);
      }
      if (stepDescription.length > 400) {
        errors.push(`${label}: "description" ist zu lang`);
      }
      if (wordCount(stepDescription) > 40) {
        errors.push(`${label}: "description" hat zu viele Wörter`);
      }
      if (!/[.!?]$/.test(stepDescription)) {
        errors.push(`${label}: "description" endet nicht mit einem Satzzeichen`);
      }
      if (compact(stepDescription) === compact(stepTitle)) {
        errors.push(`${label}: "description" wiederholt nur den Titel`);
      }
    }

    if (!Array.isArray(step.links)) {
      errors.push(`${label}: "links" muss ein Array sein`);
    } else if (step.links.length > 0) {
      errors.push(
        `${label}: "links" muss leer sein (Links werden aus partner.json ergänzt)`
      );
    }

    steps.push({
      title: stepTitle,
      description: stepDescription,
      links: [],
    });
  });

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
    workflow: {
      slug,
      title,
      description,
      category,
      tags,
      details: {
        difficulty,
        duration,
        tools,
        steps,
        useCase,
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

  for (const file of [workflowsFile, partnerFile]) {
    if (!existsSync(file)) {
      console.error(`${c.red}✖ Datei nicht gefunden: ${file}${c.reset}`);
      process.exit(1);
    }
  }

  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));
  const partner = JSON.parse(await readFile(partnerFile, "utf8"));

  if (!Array.isArray(workflows)) {
    console.error(`${c.red}✖ workflows.json muss ein Array sein.${c.reset}`);
    process.exit(1);
  }

  const tools = Object.keys(partner).filter(
    (name) => name !== "CRM" && !/alternatives$/i.test(name)
  );

  const target = Math.max(workflows.length, opts.target);
  const missing = Math.max(0, target - workflows.length);
  const toCreate = Math.min(opts.limit, missing);

  console.log(
    `${c.cyan}${c.bold}▶ Workflow-Generator${c.reset} ${c.dim}(Modell: ${opts.model})${c.reset}`
  );
  console.log(
    `  Bestand: ${c.bold}${workflows.length}${c.reset} · Ziel: ${c.bold}${target}${c.reset} · fehlend: ${c.bold}${missing}${c.reset} · dieser Lauf: ${c.bold}${toCreate}${c.reset}` +
      (opts.dryRun ? ` · ${c.yellow}DRY RUN${c.reset}` : "")
  );
  console.log(`  Verfügbare Tools: ${tools.length}`);

  if (toCreate === 0) {
    console.log(
      `${c.green}✔ Ziel bereits erreicht – nichts zu tun.${c.reset}`
    );
    return;
  }

  if (opts.dryRun) {
    const prompt = buildPrompt({ workflows, tools, errors: [] });
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
    slugs: new Set(workflows.map((workflow) => workflow.slug)),
    titles: new Set(workflows.map((workflow) => compact(workflow.title))),
    descriptions: new Set(
      workflows.map((workflow) => compact(workflow.description))
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
    const prompt = buildPrompt({ workflows, tools, errors: lastErrors });

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

    const validation = validateWorkflow(candidate, existing, partner);
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

    const workflow = validation.workflow;
    workflows.push(workflow);
    existing.slugs.add(workflow.slug);
    existing.titles.add(compact(workflow.title));
    existing.descriptions.add(compact(workflow.description));
    created += 1;
    consecutiveFailures = 0;
    lastErrors = [];

    const tmpFile = `${workflowsFile}.tmp`;
    await writeFile(
      tmpFile,
      `${JSON.stringify(workflows, null, 2)}\n`,
      "utf8"
    );
    await rename(tmpFile, workflowsFile);

    console.log(
      `  ${c.green}✓${c.reset} ${workflow.slug} – ${workflow.title} ${c.dim}(${workflow.details.steps.length} Steps, ${workflow.details.tools.join(", ")})${c.reset}`
    );
    console.log(
      `  ${c.dim}  Fortschritt: ${workflows.length}/${target}${c.reset}`
    );
  }

  console.log("");
  if (created === 0) {
    console.error(
      `${c.red}${c.bold}✖ Keine Workflows erzeugt.${c.reset}`
    );
    process.exitCode = 1;
    return;
  }

  console.log(
    `${c.green}${c.bold}✔ Fertig: ${created} neue Workflows erzeugt, ${workflows.length} insgesamt.${c.reset}`
  );
  if (workflows.length < target) {
    console.log(
      `${c.yellow}  Hinweis: Ziel ${target} noch nicht erreicht. Erneut ausführen, um weitere Workflows zu erzeugen.${c.reset}`
    );
  }
  console.log(`${c.dim}  Geschrieben: ${workflowsFile}${c.reset}`);
  console.log(
    `${c.dim}  Nächster Schritt: node scripts/enrich-workflow-details.mjs${c.reset}`
  );
}

main().catch((error) => {
  console.error(
    `${c.red}${c.bold}✖ Unerwarteter Fehler:${c.reset}`,
    error
  );
  process.exit(1);
});
