#!/usr/bin/env node
/**
 * generate-insights.mjs
 *
 * Automatisierter Content-Pipeline für die Insights-Sektion:
 *
 *   1. Liest die RSS-/Atom-Feeds aus `src/data/feeds.json`.
 *   2. Erkennt neue Einträge (Deduplizierung über die Quell-URL).
 *   3. Lässt für jeden neuen Eintrag über die OpenRouter-API einen
 *      eigenständigen, mehrwertorientierten Artikel schreiben.
 *   4. Wählt anhand der bestehenden Workflows (`src/data/workflows.json`)
 *      den thematisch passendsten Workflow und setzt einen kontextbezogenen
 *      internen Link.
 *   5. Speichert die Artikel in `src/data/insights.json`, woraus Astro unter
 *      `src/pages/insights/[slug].astro` statische Seiten generiert.
 *
 * Voraussetzungen:
 *   export OPENROUTER_API_KEY="sk-or-..."   (oder .env im Projektroot)
 *
 * Verwendung:
 *   node scripts/generate-insights.mjs --dry-run
 *   node scripts/generate-insights.mjs --limit=3
 *   node scripts/generate-insights.mjs --feed=TechCrunch --limit=1
 *   node scripts/generate-insights.mjs --lang=de
 *
 * Optionen:
 *   --dry-run          Feeds abrufen und Kandidaten anzeigen, keine API-Calls
 *   --limit=N          Maximal N neue Artikel erzeugen (Default: 5)
 *   --feed=NAME        Nur Feeds verarbeiten, deren Name NAME enthält
 *   --max-age-days=N   Nur Einträge der letzten N Tage (Default: 14)
 *   --model=ID         OpenRouter-Modell (Default: openai/gpt-4o-mini)
 *   --lang=CODE        Sprache der Artikel (Default: en)
 *   --concurrency=N    Parallele Requests (Default: 2)
 *   --help             Hilfe anzeigen
 */

import { readFile, writeFile, rename } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { XMLParser } from "fast-xml-parser";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const feedsFile = join(root, "src", "data", "feeds.json");
const insightsFile = join(root, "src", "data", "insights.json");
const workflowsFile = join(root, "src", "data", "workflows.json");

// Lokale .env laden, falls vorhanden (Node >= 20.6).
try {
  process.loadEnvFile(join(root, ".env"));
} catch {
  // Keine .env vorhanden – Shell-Variablen gelten.
}

const API_URL =
  process.env.OPENROUTER_BASE_URL?.replace(/\/$/, "") ??
  "https://openrouter.ai/api/v1";
const MODEL = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini";
const API_KEY = process.env.OPENROUTER_API_KEY;

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

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
    limit: 5,
    feed: null,
    maxAgeDays: 14,
    model: MODEL,
    lang: "en",
    concurrency: 2,
    help: false,
  };

  for (const arg of argv) {
    if (arg === "--dry-run") opts.dryRun = true;
    else if (arg === "--help" || arg === "-h") opts.help = true;
    else if (arg.startsWith("--limit=")) opts.limit = Number(arg.slice(8));
    else if (arg.startsWith("--feed=")) opts.feed = arg.slice(7);
    else if (arg.startsWith("--max-age-days="))
      opts.maxAgeDays = Number(arg.slice(15));
    else if (arg.startsWith("--model=")) opts.model = arg.slice(8);
    else if (arg.startsWith("--lang=")) opts.lang = arg.slice(7);
    else if (arg.startsWith("--concurrency="))
      opts.concurrency = Math.max(1, Number(arg.slice(14)));
    else {
      console.error(`Unbekannte Option: ${arg}`);
      process.exit(1);
    }
  }

  if (!Number.isFinite(opts.limit) || opts.limit < 0) opts.limit = 5;
  if (!Number.isFinite(opts.maxAgeDays) || opts.maxAgeDays < 0)
    opts.maxAgeDays = 14;
  if (!Number.isFinite(opts.concurrency) || opts.concurrency < 1)
    opts.concurrency = 1;

  return opts;
}

function printHelp() {
  console.log(`Verwendung: node scripts/generate-insights.mjs [Optionen]

Optionen:
  --dry-run          Feeds abrufen und Kandidaten anzeigen, keine API-Calls
  --limit=N          Maximal N neue Artikel erzeugen (Default: 5)
  --feed=NAME        Nur Feeds verarbeiten, deren Name NAME enthält
  --max-age-days=N   Nur Einträge der letzten N Tage (Default: 14)
  --model=ID         OpenRouter-Modell (Default: ${MODEL})
  --lang=CODE        Sprache der Artikel (Default: en)
  --concurrency=N    Parallele Requests (Default: 2)
  --help             Diese Hilfe anzeigen

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

function stripHtml(input) {
  return String(input ?? "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&/gi, "&")
    .replace(/</gi, "<")
    .replace(/>/gi, ">")
    .replace(/"/gi, '"')
    .replace(/'|'/gi, "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/\s+/g, " ")
    .trim();
}

function slugify(input) {
  return String(input ?? "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function textOf(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map(textOf).find(Boolean) ?? "";
  if (typeof value === "object") {
    return (
      textOf(value["#text"]) ||
      textOf(value["#cdata"]) ||
      textOf(value.__cdata) ||
      ""
    );
  }
  return "";
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

// ---------------------------------------------------------------------------
// Feed parsing
// ---------------------------------------------------------------------------

const xmlParser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "@_",
  cdataPropName: "#cdata",
  textNodeName: "#text",
  trimValues: true,
  parseTagValue: false,
});

function asArray(value) {
  if (value === null || value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function pickLink(item) {
  const link = item.link;
  if (typeof link === "string") return link;
  if (Array.isArray(link)) {
    const alternate = link.find(
      (entry) => entry?.["@_rel"] === "alternate" || !entry?.["@_rel"]
    );
    return alternate?.["@_href"] ?? textOf(alternate) ?? "";
  }
  if (link && typeof link === "object") {
    return link["@_href"] ?? textOf(link);
  }
  return textOf(item.guid) || textOf(item.id);
}

function parseFeed(xml, feed) {
  const doc = xmlParser.parse(xml);
  const channel = doc.rss?.channel ?? doc["rdf:RDF"]?.channel;
  const atom = doc.feed;

  const rawItems = channel
    ? asArray(channel.item)
    : atom
      ? asArray(atom.entry)
      : asArray(doc["rdf:RDF"]?.item);

  return rawItems
    .map((item) => {
      const title = stripHtml(textOf(item.title));
      const url = pickLink(item);
      const summary = stripHtml(
        textOf(item.description) ||
          textOf(item.summary) ||
          textOf(item["content:encoded"]) ||
          textOf(item.content)
      );
      const dateRaw =
        textOf(item.pubDate) ||
        textOf(item.published) ||
        textOf(item.updated) ||
        textOf(item["dc:date"]);
      const parsedDate = dateRaw ? new Date(dateRaw) : new Date();
      const publishedAt = Number.isNaN(parsedDate.getTime())
        ? new Date().toISOString()
        : parsedDate.toISOString();
      const guid = textOf(item.guid) || textOf(item.id) || url;

      return {
        title,
        url,
        summary,
        publishedAt,
        guid,
        feed: feed.name,
        category: feed.category,
      };
    })
    .filter((item) => isNonEmptyString(item.title) && isNonEmptyString(item.url));
}

async function fetchFeed(feed) {
  const response = await fetch(feed.url, {
    headers: {
      "User-Agent": "FlowMatrixBot/1.0 (+https://flowmatrix.com)",
      Accept: "application/rss+xml, application/atom+xml, application/xml, text/xml",
    },
    signal: AbortSignal.timeout(20_000),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const xml = await response.text();
  return parseFeed(xml, feed);
}

// ---------------------------------------------------------------------------
// OpenRouter
// ---------------------------------------------------------------------------

function buildPrompt({ item, workflows, lang }) {
  const workflowList = workflows
    .map(
      (workflow) =>
        `- slug: ${workflow.slug} | title: ${workflow.title} | category: ${workflow.category} | tags: ${(workflow.tags ?? []).join(", ")} | description: ${workflow.description}`
    )
    .join("\n");

  return `Du bist ein erfahrener Tech-Redakteur. Schreibe einen völlig eigenständigen, mehrwertorientierten Artikel auf Sprache "${lang}" zu folgender Quelle.

QUELLE
Titel: ${item.title}
Feed: ${item.feed} (${item.category})
URL: ${item.url}
Zusammenfassung: ${item.summary || "(keine Zusammenfassung verfügbar)"}

BESTEHENDE WORKFLOWS (für interne Verlinkung)
${workflowList}

AUFGABE
1. Analysiere das Thema und schreibe einen originellen Artikel (ca. 600–900 Wörter). Kein Copy-Paste, keine bloße Zusammenfassung. Erkläre Hintergründe, ordne das Thema ein und gib konkrete, umsetzbare Erkenntnisse.
2. Wähle GENAU EINEN thematisch passenden Workflow aus der Liste oben. Wenn keiner passt, setze "relatedWorkflowSlug" auf null.
3. Baue – falls ein Workflow passt – einen natürlichen, kontextbezogenen internen Link im Markdown ein: [Titel des Workflows](/en/workflows/SLUG). Der Link muss inhaltlich Sinn ergeben, nicht nur angehängt wirken.
4. Nutze Markdown mit einer H2-Gliederung (3–5 Abschnitte), kurzen Absätzen und ggf. einer Liste. Keine H1 (der Titel wird separat gerendert).

Antworte ausschließlich mit gültigem JSON in exakt diesem Schema:
{
  "title": "Prägnanter, eigenständiger Titel (max. 70 Zeichen)",
  "slug": "kebab-case-slug",
  "excerpt": "Ein bis zwei Sätze Teaser (max. 180 Zeichen)",
  "content": "Markdown-Inhalt mit H2-Abschnitten",
  "category": "Kurze Kategorie",
  "tags": ["tag1", "tag2", "tag3"],
  "relatedWorkflowSlug": "slug-aus-der-liste-oder-null",
  "relatedWorkflowReason": "Ein Satz, warum dieser Workflow passt (oder leer)"
}

Regeln:
- "slug" nur aus Kleinbuchstaben, Zahlen und Bindestrichen.
- "tags" enthält 3–5 kurze Schlagworte.
- Keine Markdown-Codefences um das JSON, kein Text außerhalb des JSON.`;
}

async function callOpenRouter({ model, item, workflows, lang, attempt = 1, useJsonMode = true }) {
  const maxAttempts = 3;
  const body = {
    model,
    temperature: 0.7,
    messages: [
      {
        role: "system",
        content:
          "Du bist ein präziser Tech-Redakteur und lieferst ausschließlich valides JSON.",
      },
      { role: "user", content: buildPrompt({ item, workflows, lang }) },
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
        "HTTP-Referer": "https://flowmatrix.com",
        "X-Title": "FlowMatrix Insights Generator",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (err) {
    if (attempt < maxAttempts) {
      const wait = 1000 * 2 ** (attempt - 1);
      console.warn(
        `${c.yellow}  ↻ Netzwerkfehler (${err.message}), Retry in ${wait}ms${c.reset}`
      );
      await sleep(wait);
      return callOpenRouter({ model, item, workflows, lang, attempt: attempt + 1, useJsonMode });
    }
    throw err;
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "");

    if (response.status === 400 && useJsonMode) {
      console.warn(
        `${c.yellow}  ↻ HTTP 400 – wiederhole ohne response_format${c.reset}`
      );
      return callOpenRouter({
        model,
        item,
        workflows,
        lang,
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
        item,
        workflows,
        lang,
        attempt: attempt + 1,
        useJsonMode,
      });
    }
    throw new Error(`OpenRouter HTTP ${response.status}: ${text.slice(0, 300)}`);
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
      return callOpenRouter({ model, item, workflows, lang, attempt: attempt + 1, useJsonMode });
    }
    throw new Error("LLM lieferte kein gültiges JSON.");
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Validation & linking
// ---------------------------------------------------------------------------

function validateArticle(article, workflows, existingSlugs) {
  const errors = [];

  if (!article || typeof article !== "object" || Array.isArray(article)) {
    return { ok: false, errors: ["kein Objekt"] };
  }

  if (!isNonEmptyString(article.title)) errors.push('"title" fehlt');
  if (!isNonEmptyString(article.excerpt)) errors.push('"excerpt" fehlt');
  if (!isNonEmptyString(article.content)) errors.push('"content" fehlt');
  if (!isNonEmptyString(article.category)) errors.push('"category" fehlt');
  if (!isStringArray(article.tags)) errors.push('"tags" ist kein String-Array');

  if (isNonEmptyString(article.content) && article.content.length < 400) {
    errors.push('"content" ist zu kurz (< 400 Zeichen)');
  }

  let slug = isNonEmptyString(article.slug) ? article.slug.trim() : "";
  if (!SLUG_PATTERN.test(slug)) {
    slug = slugify(article.title);
  }
  if (!slug) errors.push("kein gültiger Slug ableitbar");
  if (existingSlugs.has(slug)) {
    let suffix = 2;
    while (existingSlugs.has(`${slug}-${suffix}`)) suffix += 1;
    slug = `${slug}-${suffix}`;
  }

  const workflowSlugs = new Set(workflows.map((workflow) => workflow.slug));
  let relatedWorkflowSlug = article.relatedWorkflowSlug;
  if (relatedWorkflowSlug && !workflowSlugs.has(relatedWorkflowSlug)) {
    relatedWorkflowSlug = null;
  }

  return {
    ok: errors.length === 0,
    errors,
    slug,
    relatedWorkflowSlug: relatedWorkflowSlug ?? null,
  };
}

/**
 * Stellt sicher, dass der interne Workflow-Link im Markdown vorhanden ist.
 * Der LLM-Link wird bevorzugt; fehlt er, wird ein kontextueller Abschnitt
 * am Ende ergänzt.
 */
function ensureWorkflowLink(content, workflow, lang) {
  if (!workflow) return content;

  const linkPattern = new RegExp(
    `\\]\\([^)]*\\/workflows\\/${workflow.slug}\\/?\\)`,
    "i"
  );
  if (linkPattern.test(content)) return content;

  const heading = lang === "de" ? "## Passender Workflow" : "## Related workflow";
  const intro =
    lang === "de"
      ? "Wenn du das direkt umsetzen möchtest, passt dieser Workflow aus unserem Katalog:"
      : "If you want to put this into practice, this workflow from our catalog is a good fit:";

  return `${content.trim()}\n\n${heading}\n\n${intro} [${workflow.title}](/en/workflows/${workflow.slug}).`;
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

  if (!opts.dryRun && !API_KEY) {
    console.error(
      `${c.red}${c.bold}✖ OPENROUTER_API_KEY ist nicht gesetzt.${c.reset}\n` +
        `  Setze ihn in .env oder als Umgebungsvariable.`
    );
    process.exit(1);
  }

  for (const file of [feedsFile, insightsFile, workflowsFile]) {
    if (!existsSync(file)) {
      console.error(`${c.red}✖ Datei nicht gefunden: ${file}${c.reset}`);
      process.exit(1);
    }
  }

  const feeds = JSON.parse(await readFile(feedsFile, "utf8"));
  const insights = JSON.parse(await readFile(insightsFile, "utf8"));
  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));

  if (!Array.isArray(feeds) || !Array.isArray(insights) || !Array.isArray(workflows)) {
    console.error(`${c.red}✖ feeds.json, insights.json und workflows.json müssen Arrays sein.${c.reset}`);
    process.exit(1);
  }

  const selectedFeeds = opts.feed
    ? feeds.filter((feed) =>
        feed.name.toLowerCase().includes(opts.feed.toLowerCase())
      )
    : feeds;

  console.log(
    `${c.cyan}${c.bold}▶ Insights-Generator${c.reset} ${c.dim}(Modell: ${opts.model}, Sprache: ${opts.lang})${c.reset}`
  );
  console.log(
    `  Feeds: ${c.bold}${selectedFeeds.length}${c.reset} · bestehende Insights: ${c.bold}${insights.length}${c.reset}` +
      (opts.dryRun ? ` · ${c.yellow}DRY RUN${c.reset}` : "")
  );

  // 1. Feeds abrufen
  const knownUrls = new Set(
    insights.map((insight) => insight?.source?.url).filter(Boolean)
  );
  const knownGuids = new Set(
    insights.map((insight) => insight?.source?.guid).filter(Boolean)
  );

  const cutoff = Date.now() - opts.maxAgeDays * 24 * 60 * 60 * 1000;
  const candidates = [];
  const seenInRun = new Set();

  for (const feed of selectedFeeds) {
    try {
      const items = await fetchFeed(feed);
      let fresh = 0;

      for (const item of items) {
        if (knownUrls.has(item.url) || knownGuids.has(item.guid)) continue;
        if (seenInRun.has(item.url)) continue;
        if (new Date(item.publishedAt).getTime() < cutoff) continue;

        seenInRun.add(item.url);
        candidates.push(item);
        fresh += 1;
      }

      console.log(
        `  ${c.green}✓${c.reset} ${feed.name}: ${items.length} Einträge, ${fresh} neu`
      );
    } catch (err) {
      console.warn(
        `${c.yellow}  ⚠ ${feed.name}: Feed konnte nicht geladen werden (${err.message})${c.reset}`
      );
    }
  }

  candidates.sort(
    (a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
  );

  const selected = candidates.slice(0, opts.limit);

  console.log(
    `\n  Neue Kandidaten: ${c.bold}${candidates.length}${c.reset} · ausgewählt: ${c.bold}${selected.length}${c.reset}`
  );

  if (selected.length === 0) {
    console.log(
      `${c.green}✔ Nichts zu tun – keine neuen Einträge in den letzten ${opts.maxAgeDays} Tagen.${c.reset}`
    );
    return;
  }

  if (opts.dryRun) {
    for (const item of selected) {
      console.log(
        `\n  ${c.bold}• ${item.title}${c.reset}\n    ${c.dim}${item.feed} · ${item.publishedAt}${c.reset}\n    ${c.dim}${item.url}${c.reset}`
      );
    }
    console.log(
      `\n${c.yellow}${c.bold}Dry Run beendet – keine API-Calls, keine Datei geschrieben.${c.reset}`
    );
    return;
  }

  // 2. Artikel generieren
  const existingSlugs = new Set(insights.map((insight) => insight.slug));
  const created = [];
  const failures = [];
  let cursor = 0;

  async function worker() {
    while (cursor < selected.length) {
      const item = selected[cursor++];
      console.log(`\n${c.bold}→ ${item.title}${c.reset} ${c.dim}(${item.feed})${c.reset}`);

      try {
        const article = await callOpenRouter({
          model: opts.model,
          item,
          workflows,
          lang: opts.lang,
        });

        const validation = validateArticle(article, workflows, existingSlugs);
        if (!validation.ok) {
          throw new Error(`Validierung fehlgeschlagen: ${validation.errors.join(", ")}`);
        }

        const workflow = validation.relatedWorkflowSlug
          ? workflows.find((entry) => entry.slug === validation.relatedWorkflowSlug)
          : null;

        const content = ensureWorkflowLink(article.content, workflow, opts.lang);

        const insight = {
          slug: validation.slug,
          title: article.title.trim(),
          excerpt: article.excerpt.trim(),
          content,
          category: article.category.trim(),
          tags: article.tags.map((tag) => String(tag).trim()).filter(Boolean),
          source: {
            name: item.feed,
            url: item.url,
            guid: item.guid,
            publishedAt: item.publishedAt,
          },
          relatedWorkflow: workflow
            ? {
                slug: workflow.slug,
                title: workflow.title,
                reason: isNonEmptyString(article.relatedWorkflowReason)
                  ? article.relatedWorkflowReason.trim()
                  : "",
              }
            : null,
          publishedAt: item.publishedAt,
          updatedAt: new Date().toISOString(),
        };

        existingSlugs.add(insight.slug);
        created.push(insight);

        console.log(
          `  ${c.green}✓${c.reset} ${insight.slug} ${c.dim}(${insight.content.length} Zeichen)${c.reset}`
        );
        if (workflow) {
          console.log(
            `  ${c.green}↳${c.reset} verlinkt mit Workflow: ${workflow.title}`
          );
        }
      } catch (err) {
        failures.push({ title: item.title, error: err.message });
        console.error(`${c.red}  ✖ ${err.message}${c.reset}`);
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(opts.concurrency, selected.length) }, () =>
      worker()
    )
  );

  if (created.length === 0) {
    console.log(
      `\n${c.yellow}${c.bold}Keine Artikel erzeugt – Datei bleibt unverändert.${c.reset}`
    );
    if (failures.length > 0) process.exitCode = 1;
    return;
  }

  // 3. Atomar speichern (neueste zuerst)
  const merged = [...insights, ...created].sort(
    (a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
  );

  const tmpFile = `${insightsFile}.tmp`;
  await writeFile(tmpFile, `${JSON.stringify(merged, null, 2)}\n`, "utf8");
  await rename(tmpFile, insightsFile);

  console.log(
    `\n${c.green}${c.bold}✔ Fertig: ${created.length} Artikel erzeugt, ${merged.length} insgesamt.${c.reset}`
  );
  console.log(`${c.dim}  Geschrieben: ${insightsFile}${c.reset}`);

  if (failures.length > 0) {
    console.log(
      `\n${c.red}${c.bold}${failures.length} Eintrag/Einträge fehlgeschlagen:${c.reset}`
    );
    for (const failure of failures) {
      console.log(`  • ${failure.title}: ${failure.error}`);
    }
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(`${c.red}${c.bold}✖ Unerwarteter Fehler:${c.reset}`, err);
  process.exit(1);
});
