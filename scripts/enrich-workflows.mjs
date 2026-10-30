#!/usr/bin/env node
/**
 * enrich-workflows.mjs
 *
 * Ergänzt Workflow-Steps, die bisher nur als String (Titel) vorliegen, um
 * ausführliche Beschreibungen und offizielle Dokumentationslinks.
 *
 * Bestehende Objekt-Steps werden nicht verändert. Die Anreicherung erfolgt
 * über die OpenRouter-API.
 *
 * Verwendung:
 *   node scripts/enrich-workflows.mjs --dry-run
 *   node scripts/enrich-workflows.mjs --limit=3
 *   node scripts/enrich-workflows.mjs
 */

import { readFile, writeFile, rename } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const workflowsFile = join(root, "src", "data", "workflows.json");

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
const normalize = (value) =>
  String(value ?? "").replace(/\s+/g, " ").trim();
const lower = (value) => normalize(value).toLowerCase();

function parseArgs(argv) {
  const opts = { dryRun: false, limit: Infinity, concurrency: 2, help: false };
  for (const arg of argv) {
    if (arg === "--dry-run") opts.dryRun = true;
    else if (arg === "--help" || arg === "-h") opts.help = true;
    else if (arg.startsWith("--limit=")) opts.limit = Number(arg.slice(8));
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

function buildPrompt(workflow, stepTitles) {
  return `Du bist ein technischer Redakteur. Für den Workflow "${workflow.title}" (Kategorie: ${workflow.category}) sind folgende Steps nur als kurze Titel vorhanden:

${stepTitles.map((title, index) => `${index + 1}. ${title}`).join("\n")}

Workflow-Beschreibung: ${workflow.description}
Verwendete Tools: ${(workflow.details?.tools ?? []).join(", ") || "—"}

Ergänze für JEDEN Step:
- "description": eine ausführliche, konkrete Beschreibung (2–4 Sätze, 120–300 Zeichen) auf Deutsch.
- "links": 1–2 offizielle Dokumentations- oder Ressourcenlinks (nur http/https).

Antworte ausschließlich mit gültigem JSON:
{
  "steps": [
    {
      "title": "Exakter Titel wie oben",
      "description": "Ausführliche Beschreibung …",
      "links": [{ "label": "Dokumentation", "url": "https://…" }]
    }
  ]
}

Regeln:
- Behalte die Titel exakt bei und liefere genau ${stepTitles.length} Einträge.
- Keine Erfindungen bei URLs; nutze offizielle Hersteller-/Dokumentationsseiten.
- Keine Markdown-Codefences, kein Text außerhalb des JSON.`;
}

async function callOpenRouter({ workflow, stepTitles, attempt = 1, useJsonMode = true }) {
  const maxAttempts = 3;
  const body = {
    model: MODEL,
    temperature: 0.4,
    messages: [
      {
        role: "system",
        content:
          "Du bist ein präziser technischer Redakteur und lieferst ausschließlich valides JSON.",
      },
      { role: "user", content: buildPrompt(workflow, stepTitles) },
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
        "X-Title": "FlowMatrix Workflow Enrichment",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (error) {
    if (attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(`${c.yellow}  ↻ Netzwerkfehler, Retry in ${wait}ms${c.reset}`);
      await sleep(wait);
      return callOpenRouter({ workflow, stepTitles, attempt: attempt + 1, useJsonMode });
    }
    throw error;
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    if (response.status === 400 && useJsonMode) {
      return callOpenRouter({ workflow, stepTitles, attempt, useJsonMode: false });
    }
    const retryable = response.status === 429 || response.status >= 500;
    if (retryable && attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(`${c.yellow}  ↻ HTTP ${response.status}, Retry in ${wait}ms${c.reset}`);
      await sleep(wait);
      return callOpenRouter({ workflow, stepTitles, attempt: attempt + 1, useJsonMode });
    }
    throw new Error(`OpenRouter HTTP ${response.status}: ${text.slice(0, 300)}`);
  }

  const payload = await response.json();
  const parsed = extractJson(payload?.choices?.[0]?.message?.content);
  if (!parsed || !Array.isArray(parsed.steps)) {
    if (attempt < maxAttempts) {
      await sleep(1000 * attempt);
      return callOpenRouter({ workflow, stepTitles, attempt: attempt + 1, useJsonMode });
    }
    throw new Error("LLM lieferte kein gültiges JSON mit 'steps'.");
  }
  return parsed.steps;
}

function validateSteps(generated, stepTitles) {
  const errors = [];
  if (generated.length !== stepTitles.length) {
    errors.push(`Erwartet ${stepTitles.length} Steps, erhalten ${generated.length}`);
  }

  const byTitle = new Map();
  for (const step of generated) {
    if (!step || typeof step !== "object") continue;
    const title = normalize(step.title);
    const description = normalize(step.description);
    if (!title) {
      errors.push("Step ohne Titel");
      continue;
    }
    if (description.length < 60) {
      errors.push(`"${title}": Beschreibung zu kurz (${description.length} Zeichen)`);
    }
    const links = Array.isArray(step.links) ? step.links : [];
    for (const link of links) {
      if (!link?.url || !/^https?:\/\//i.test(link.url)) {
        errors.push(`"${title}": ungültiger Link`);
      }
    }
    byTitle.set(lower(title), { title, description, links });
  }

  for (const title of stepTitles) {
    if (!byTitle.has(lower(title))) {
      errors.push(`Step "${title}" fehlt in der LLM-Antwort`);
    }
  }

  return { errors, byTitle };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log("Verwendung: node scripts/enrich-workflows.mjs [--dry-run] [--limit=N] [--concurrency=N]");
    return;
  }
  if (!opts.dryRun && !API_KEY) {
    console.error(`${c.red}✖ OPENROUTER_API_KEY ist nicht gesetzt.${c.reset}`);
    process.exit(1);
  }
  if (!existsSync(workflowsFile)) {
    console.error(`${c.red}✖ workflows.json nicht gefunden.${c.reset}`);
    process.exit(1);
  }

  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));
  let candidates = workflows.filter((workflow) =>
    (workflow.details?.steps ?? []).some((step) => typeof step === "string")
  );
  candidates = candidates.slice(0, opts.limit);

  console.log(
    `${c.cyan}${c.bold}▶ Workflow-Step-Anreicherung${c.reset} · Kandidaten: ${c.bold}${candidates.length}${c.reset}` +
      (opts.dryRun ? ` · ${c.yellow}DRY RUN${c.reset}` : "")
  );

  if (candidates.length === 0) {
    console.log(`${c.green}✔ Alle Workflows haben bereits strukturierte Steps.${c.reset}`);
    return;
  }

  if (opts.dryRun) {
    for (const workflow of candidates) {
      const titles = workflow.details.steps.filter((s) => typeof s === "string");
      console.log(`\n  ${c.bold}• ${workflow.slug}${c.reset} (${titles.length} Steps)`);
      titles.forEach((title) => console.log(`    - ${title}`));
    }
    return;
  }

  let updated = 0;
  let failed = 0;
  let cursor = 0;

  async function worker() {
    while (cursor < candidates.length) {
      const workflow = candidates[cursor++];
      const stepTitles = workflow.details.steps.filter((s) => typeof s === "string");
      console.log(`\n${c.bold}→ ${workflow.slug}${c.reset} (${stepTitles.length} Steps)`);

      try {
        const generated = await callOpenRouter({ workflow, stepTitles });
        const { errors, byTitle } = validateSteps(generated, stepTitles);
        if (errors.length > 0) {
          throw new Error(errors.join("; "));
        }

        workflow.details.steps = workflow.details.steps.map((step) => {
          if (typeof step !== "string") return step;
          const match = byTitle.get(lower(step));
          if (!match) return step;
          return {
            title: step,
            description: match.description,
            links: match.links,
          };
        });

        updated += 1;
        console.log(`  ${c.green}✓${c.reset} ${stepTitles.length} Steps angereichert`);
      } catch (error) {
        failed += 1;
        console.error(`${c.red}  ✖ ${error.message}${c.reset}`);
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(opts.concurrency, candidates.length) }, () => worker())
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
