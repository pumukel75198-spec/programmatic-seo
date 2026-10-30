#!/usr/bin/env node
/**
 * enrich-workflow-details.mjs
 *
 * Erzeugt für jeden Workflow eine lückenlose Master-Anleitung. Pro Workflow
 * werden alle Steps gemeinsam angereichert, damit Tools und Zwischenschritte
 * konsistent über den gesamten Ablauf verteilt werden.
 *
 * Neue Felder pro Step:
 *   - description, actions, commands, config, tools, checklist, expectedResult
 *
 * Bestehende Titel und Links bleiben erhalten.
 *
 * Verwendung:
 *   node scripts/enrich-workflow-details.mjs --dry-run
 *   node scripts/enrich-workflow-details.mjs --limit=2
 *   node scripts/enrich-workflow-details.mjs --force
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
  /* no .env */
}

const API_URL =
  process.env.OPENROUTER_BASE_URL?.replace(/\/$/, "") ??
  "https://openrouter.ai/api/v1";
const MODEL = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini";
const API_KEY = process.env.OPENROUTER_API_KEY;

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
const lower = (value) => normalize(value).toLowerCase();

function parseArgs(argv) {
  const opts = {
    dryRun: false,
    limit: Infinity,
    concurrency: 2,
    force: false,
    only: null,
    help: false,
  };
  for (const arg of argv) {
    if (arg === "--dry-run") opts.dryRun = true;
    else if (arg === "--force") opts.force = true;
    else if (arg === "--help" || arg === "-h") opts.help = true;
    else if (arg.startsWith("--limit=")) opts.limit = Number(arg.slice(8));
    else if (arg.startsWith("--only="))
      opts.only = arg
        .slice(7)
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
    else if (arg.startsWith("--concurrency="))
      opts.concurrency = Math.max(1, Number(arg.slice(14)));
    else {
      console.error(`Unbekannte Option: ${arg}`);
      process.exit(1);
    }
  }
  if (!Number.isFinite(opts.limit) || opts.limit < 0) opts.limit = Infinity;
  return opts;
}

function extractJson(text) {
  if (typeof text !== "string") return null;
  let cleaned = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
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

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function isStringArray(value, min = 1) {
  return (
    Array.isArray(value) &&
    value.length >= min &&
    value.every((item) => isNonEmptyString(item))
  );
}

function buildPrompt(workflow, steps, availableTools) {
  const toolList = availableTools
    .map(
      (tool) =>
        `- ${tool.name} (Affiliate: ${tool.affiliateUrl ?? tool.url ?? "—"})`
    )
    .join("\n");

  const stepList = steps
    .map(
      (step, index) =>
        `${index + 1}. ${step.title}\n   Bisher: ${step.description || "(keine Beschreibung)"}`
    )
    .join("\n");

  return `Du bist ein technischer Redakteur und erstellst eine lückenlose Master-Anleitung, mit der ein Käufer das Setup von A bis Z exakt nachbauen kann.

WORKFLOW
Titel: ${workflow.title}
Kategorie: ${workflow.category}
Beschreibung: ${workflow.description}
Difficulty: ${workflow.details?.difficulty ?? "—"}
Dauer: ${workflow.details?.duration ?? "—"}
Tools im Workflow: ${(workflow.details?.tools ?? []).join(", ") || "—"}

STEPS
${stepList}

VERFÜGBARE TOOLS (nur diese verwenden)
${toolList || "—"}

AUFGABE
Liefere für JEDEN Step eine vollständige, praxisnahe Anleitung. Antworte ausschließlich mit gültigem JSON:

{
  "steps": [
    {
      "title": "Exakter Titel wie oben",
      "description": "Ausführliche Beschreibung (2–4 Sätze, 150–350 Zeichen).",
      "actions": [
        "Konkrete Handlung 1 mit Klickpfad/Parameter",
        "Konkrete Handlung 2",
        "Konkrete Handlung 3"
      ],
      "commands": [
        { "label": "Kurzer Titel", "language": "bash", "code": "echter Befehl" }
      ],
      "config": [
        { "key": "PARAMETER_NAME", "value": "konkreter Wert oder <Platzhalter>", "description": "Wofür der Parameter ist" }
      ],
      "tools": ["ToolName aus der Liste"],
      "checklist": [
        "Überprüfbarer Punkt 1",
        "Überprüfbarer Punkt 2"
      ],
      "expectedResult": "Ein Satz, was nach diesem Schritt fertig ist."
    }
  ]
}

REGELN
- Liefere genau ${steps.length} Steps in der Reihenfolge oben und behalte die Titel exakt bei.
- "actions": 3–6 konkrete, nummerierbare Handlungen. Nenne echte Menüpunkte, Endpunkte, Tabellen, Felder oder Parameter.
- "commands": nur wenn sinnvoll; echte, aktuelle CLI-/API-/Code-Schnipsel. Keine veralteten Modelle (kein text-davinci-003). Platzhalter nur als <...>.
- "config": nur wenn sinnvoll; echte Umgebungsvariablen/Parameter.
- "tools": nur Tools aus der Liste, die in diesem Schritt wirklich gebraucht werden. Verteile die Tools sinnvoll über die Steps; leeres Array, wenn keins nötig ist.
- "checklist": 2–4 überprüfbare Punkte.
- "expectedResult": genau ein Satz.
- Verwende ausschließlich aktuelle, offizielle Befehle und Modelle. Beispiele: \`npm create astro@latest\`, \`npm install astro\`, \`gpt-4o-mini\`. Verboten: \`npm init astro\`, \`text-davinci-003\`, \`gpt-3.5-turbo\`.
- OpenAI: Verwende immer \`https://api.openai.com/v1/chat/completions\` mit \`messages\`. Kein \`/v1/engines/\`, kein \`/v1/completions\`.
- Erfinde keine Aktionen, die nicht zum Step-Titel passen. Für OpenAI: API-Key unter https://platform.openai.com/api-keys erstellen.
- Keine Platzhalter wie "TODO", "Lorem Ipsum", "[Hier einfügen]", "undefined".
- Keine Markdown-Codefences, kein Text außerhalb des JSON.`;
}

const FORBIDDEN_PATTERNS = [
  [/text-davinci/i, "veraltetes Modell text-davinci"],
  [/gpt-3\.5-turbo/i, "veraltetes Modell gpt-3.5-turbo"],
  [/npm init astro/i, "veralteter Befehl npm init astro"],
  [/api\.openai\.com\/v1\/engines\//i, "veralteter OpenAI-Endpoint /v1/engines"],
  [/api\.openai\.com\/v1\/completions/i, "veralteter OpenAI-Completions-Endpoint"],
  [/lorem ipsum/i, "Lorem Ipsum"],
  [/\btodo\b/i, "TODO"],
  [/\[hier einfügen\]/i, "Platzhalter [Hier einfügen]"],
  [/\bundefined\b/i, "undefined"],
];

async function callOpenRouter({ workflow, steps, availableTools, attempt = 1, useJsonMode = true }) {
  const maxAttempts = 3;
  const body = {
    model: MODEL,
    temperature: 0.25,
    messages: [
      {
        role: "system",
        content:
          "Du bist ein präziser technischer Redakteur und lieferst ausschließlich valides JSON.",
      },
      { role: "user", content: buildPrompt(workflow, steps, availableTools) },
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
        "X-Title": "FlowMatrix Workflow Detail Enrichment",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(180_000),
    });
  } catch (error) {
    if (attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(`${c.yellow}  ↻ Netzwerkfehler, Retry in ${wait}ms${c.reset}`);
      await sleep(wait);
      return callOpenRouter({ workflow, steps, availableTools, attempt: attempt + 1, useJsonMode });
    }
    throw error;
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    if (response.status === 400 && useJsonMode) {
      return callOpenRouter({ workflow, steps, availableTools, attempt, useJsonMode: false });
    }
    const retryable = response.status === 429 || response.status >= 500;
    if (retryable && attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(`${c.yellow}  ↻ HTTP ${response.status}, Retry in ${wait}ms${c.reset}`);
      await sleep(wait);
      return callOpenRouter({ workflow, steps, availableTools, attempt: attempt + 1, useJsonMode });
    }
    throw new Error(`OpenRouter HTTP ${response.status}: ${text.slice(0, 300)}`);
  }

  const payload = await response.json();
  const parsed = extractJson(payload?.choices?.[0]?.message?.content);
  if (!parsed || !Array.isArray(parsed.steps)) {
    if (attempt < maxAttempts) {
      await sleep(1000 * attempt);
      return callOpenRouter({ workflow, steps, availableTools, attempt: attempt + 1, useJsonMode });
    }
    throw new Error("LLM lieferte kein gültiges JSON mit 'steps'.");
  }
  return parsed.steps;
}

function validateStepDetail(detail, availableToolNames) {
  const errors = [];
  const serialized = JSON.stringify(detail);
  for (const [pattern, label] of FORBIDDEN_PATTERNS) {
    if (pattern.test(serialized)) {
      errors.push(`verbotener Inhalt: ${label}`);
    }
  }
  if (!isNonEmptyString(detail.description)) errors.push("description fehlt");
  if (!isStringArray(detail.actions, 3)) errors.push("actions: mindestens 3 Einträge erwartet");
  if (!isStringArray(detail.checklist, 2)) errors.push("checklist: mindestens 2 Einträge erwartet");
  if (!isNonEmptyString(detail.expectedResult)) errors.push("expectedResult fehlt");

  if (detail.commands !== undefined) {
    if (!Array.isArray(detail.commands)) errors.push("commands muss ein Array sein");
    else {
      for (const command of detail.commands) {
        if (!isNonEmptyString(command?.label) || !isNonEmptyString(command?.code)) {
          errors.push("commands: label und code sind Pflicht");
        }
      }
    }
  }

  if (detail.config !== undefined) {
    if (!Array.isArray(detail.config)) errors.push("config muss ein Array sein");
    else {
      for (const entry of detail.config) {
        if (!isNonEmptyString(entry?.key) || !isNonEmptyString(entry?.value)) {
          errors.push("config: key und value sind Pflicht");
        }
      }
    }
  }

  if (detail.tools !== undefined) {
    if (!Array.isArray(detail.tools)) errors.push("tools muss ein Array sein");
    else {
      for (const tool of detail.tools) {
        if (!availableToolNames.has(tool)) {
          errors.push(`tools: "${tool}" ist nicht im Workflow definiert`);
        }
      }
    }
  }

  return errors;
}

function isComplete(step) {
  return (
    typeof step === "object" &&
    isStringArray(step.actions, 3) &&
    isStringArray(step.checklist, 2) &&
    isNonEmptyString(step.expectedResult)
  );
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log("Verwendung: node scripts/enrich-workflow-details.mjs [--dry-run] [--limit=N] [--concurrency=N] [--force]");
    return;
  }
  if (!opts.dryRun && !API_KEY) {
    console.error(`${c.red}✖ OPENROUTER_API_KEY ist nicht gesetzt.${c.reset}`);
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

  const only = opts.only ? new Set(opts.only) : null;
  const candidates = workflows.filter((workflow) => {
    if (only && !only.has(workflow.slug)) return false;
    const steps = (workflow.details?.steps ?? []).filter(
      (step) => typeof step === "object"
    );
    if (steps.length === 0) return false;
    return opts.force || steps.some((step) => !isComplete(step));
  });

  const selected = candidates.slice(0, opts.limit);

  console.log(
    `${c.cyan}${c.bold}▶ Workflow-Detail-Anreicherung${c.reset} · offene Workflows: ${c.bold}${candidates.length}${c.reset} · ausgewählt: ${c.bold}${selected.length}${c.reset}` +
      (opts.dryRun ? ` · ${c.yellow}DRY RUN${c.reset}` : "")
  );

  if (selected.length === 0) {
    console.log(`${c.green}✔ Alle Workflows sind bereits vollständig angereichert.${c.reset}`);
    return;
  }

  if (opts.dryRun) {
    for (const workflow of selected) {
      console.log(`  • ${workflow.slug} (${workflow.details.steps.length} Steps)`);
    }
    return;
  }

  let updated = 0;
  let failed = 0;
  let cursor = 0;

  async function worker() {
    while (cursor < selected.length) {
      const workflow = selected[cursor++];
      const steps = workflow.details.steps.filter(
        (step) => typeof step === "object"
      );
      const availableToolNames = new Set(workflow.details?.tools ?? []);
      const availableTools = [...availableToolNames].map((name) => ({
        name,
        ...(partner[name] ?? { url: "" }),
      }));

      console.log(`\n${c.bold}→ ${workflow.slug}${c.reset} (${steps.length} Steps)`);

      try {
        const generated = await callOpenRouter({
          workflow,
          steps,
          availableTools,
        });

        if (generated.length !== steps.length) {
          throw new Error(
            `Erwartet ${steps.length} Steps, erhalten ${generated.length}`
          );
        }

        const byTitle = new Map();
        for (const detail of generated) {
          const title = normalize(detail?.title);
          if (!title) continue;
          const errors = validateStepDetail(detail, availableToolNames);
          if (errors.length > 0) {
            throw new Error(`"${title}": ${errors.join("; ")}`);
          }
          byTitle.set(lower(title), detail);
        }

        for (const step of steps) {
          const detail = byTitle.get(lower(step.title));
          if (!detail) {
            throw new Error(`Step "${step.title}" fehlt in der LLM-Antwort`);
          }
          step.description = detail.description.trim();
          step.actions = detail.actions.map((item) => String(item).trim());
          step.commands = Array.isArray(detail.commands)
            ? detail.commands.map((command) => ({
                label: String(command.label).trim(),
                language: String(command.language ?? "bash").trim(),
                code: String(command.code).trim(),
              }))
            : [];
          step.config = Array.isArray(detail.config)
            ? detail.config.map((entry) => ({
                key: String(entry.key).trim(),
                value: String(entry.value).trim(),
                description: String(entry.description ?? "").trim(),
              }))
            : [];
          step.tools = Array.isArray(detail.tools)
            ? detail.tools.map((tool) => String(tool).trim())
            : [];
          step.checklist = detail.checklist.map((item) => String(item).trim());
          step.expectedResult = detail.expectedResult.trim();
        }

        updated += 1;
        console.log(`  ${c.green}✓${c.reset} ${steps.length} Steps angereichert`);
      } catch (error) {
        failed += 1;
        console.error(`${c.red}  ✖ ${error.message}${c.reset}`);
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(opts.concurrency, selected.length) }, () => worker())
  );

  if (updated === 0) {
    console.log(`\n${c.yellow}Keine Änderungen.${c.reset}`);
    if (failed > 0) process.exitCode = 1;
    return;
  }

  const tmpFile = `${workflowsFile}.tmp`;
  await writeFile(tmpFile, `${JSON.stringify(workflows, null, 2)}\n`, "utf8");
  await rename(tmpFile, workflowsFile);

  console.log(
    `\n${c.green}${c.bold}✔ Fertig: ${updated} Workflows angereichert${failed ? `, ${failed} fehlgeschlagen` : ""}.${c.reset}`
  );
  if (failed > 0) process.exitCode = 1;
}

main().catch((error) => {
  console.error(`${c.red}${c.bold}✖ Unerwarteter Fehler:${c.reset}`, error);
  process.exit(1);
});
