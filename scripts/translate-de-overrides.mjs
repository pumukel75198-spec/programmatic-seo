/**
 * translate-de-overrides.mjs
 *
 * Generates German metadata overrides (title, description, category, tags)
 * for data records that do not yet have a manual override in
 * `src/i18n/content.ts`.
 *
 * Output: `src/i18n/de-overrides.generated.json`. Manual overrides always win
 * when both exist. The script is resumable: entries already present in the
 * generated file are skipped.
 *
 * Usage:
 *   node scripts/translate-de-overrides.mjs
 *   node scripts/translate-de-overrides.mjs --limit=8
 */
import { readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const generatedPath = join(root, "src", "i18n", "de-overrides.generated.json");

const limitArg = process.argv.find((arg) => arg.startsWith("--limit="));
const LIMIT = limitArg ? Number(limitArg.split("=")[1]) : Infinity;
const BATCH_SIZE = 8;
const MODEL = process.env.OPENROUTER_MODEL || "openai/gpt-4o-mini";

async function loadEnvKey() {
  const raw = await readFile(join(root, ".env"), "utf8").catch(() => "");
  const match = raw.match(/^OPENROUTER_API_KEY=(.*)$/m);
  return (process.env.OPENROUTER_API_KEY || match?.[1] || "").trim();
}

const API_KEY = await loadEnvKey();
if (!API_KEY) {
  console.error("[i18n] OPENROUTER_API_KEY is missing (.env or environment).");
  process.exit(1);
}

function manualSlugs(source, exportName) {
  const start = source.indexOf(`export const ${exportName}`);
  if (start === -1) return new Set();
  const deMatch = source.slice(start).match(/de:\s*\{([\s\S]*?)\n {2}\},\n\};/);
  if (!deMatch) return new Set();
  return new Set(
    [...deMatch[1].matchAll(/^ {4}"([^"]+)":\s*\{/gm)].map((m) => m[1]),
  );
}

const sources = {
  apis: JSON.parse(
    await readFile(join(root, "src", "data", "apis.json"), "utf8"),
  ),
  alternatives: JSON.parse(
    await readFile(join(root, "src", "data", "alternatives.json"), "utf8"),
  ),
  workflows: JSON.parse(
    await readFile(join(root, "src", "data", "workflows.json"), "utf8"),
  ),
};

const contentSource = await readFile(
  join(root, "src", "i18n", "content.ts"),
  "utf8",
);

const manual = {
  apis: manualSlugs(contentSource, "manualApiOverrides"),
  alternatives: manualSlugs(contentSource, "manualAlternativeOverrides"),
  workflows: manualSlugs(contentSource, "manualWorkflowOverrides"),
};

let generated = { apis: {}, alternatives: {}, workflows: {} };
try {
  generated = JSON.parse(await readFile(generatedPath, "utf8"));
} catch {
  // First run.
}

const pending = [];
for (const kind of ["apis", "alternatives", "workflows"]) {
  for (const entry of sources[kind]) {
    if (manual[kind].has(entry.slug)) continue;
    if (generated[kind]?.[entry.slug]) continue;
    pending.push({
      kind,
      slug: entry.slug,
      title: entry.title,
      description: entry.description,
      category: entry.category,
      tags: entry.tags,
    });
  }
}

console.log(
  `[i18n] pending translations: ${pending.length} ` +
    `(${pending.slice(0, LIMIT).length} in this run)`,
);

function extractJson(text) {
  const cleaned = text
    .replace(/^```(?:json)?/i, "")
    .replace(/```$/i, "")
    .trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start !== -1 && end > start) {
      return JSON.parse(cleaned.slice(start, end + 1));
    }
    throw new Error("No JSON object in response");
  }
}

async function translateBatch(items, attempt = 1) {
  const prompt = [
    "Du bist ein professioneller deutscher SEO-Übersetzer.",
    "Übersetze die Metadaten der folgenden Einträge natürlich und präzise ins Deutsche.",
    "Behalte Produkt-/Markennamen und technische Begriffe (API, SDK, Webhook, LLM, Embedding) unverändert.",
    "Die description soll maximal 158 Zeichen lang sein und den englischen Inhalt treu wiedergeben.",
    "Übersetze auch die Tags ins Deutsche (technische Tags dürfen englisch bleiben).",
    "Verwende durchgehend die professionelle Du-Form (du/dein), niemals die Höflichkeitsform Sie/Ihr.",
    "Gib AUSSCHLIESSLICH valides JSON in exakt dieser Form zurück:",
    '{"items":[{"kind":"apis","slug":"...","title":"...","description":"...","category":"...","tags":["..."]}]}',
    "Gib alle Eingabeeinträge unverändert in Anzahl und Slug zurück.",
    "",
    JSON.stringify({ items }, null, 2),
  ].join("\n");

  const response = await fetch(
    "https://openrouter.ai/api/v1/chat/completions",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://flowmatrix.dev",
        "X-Title": "FlowMatrix DE translations",
      },
      body: JSON.stringify({
        model: MODEL,
        temperature: 0.2,
        max_tokens: 4096,
        response_format: { type: "json_object" },
        messages: [{ role: "user", content: prompt }],
      }),
    },
  );

  if (!response.ok) {
    throw new Error(`OpenRouter ${response.status}: ${await response.text()}`);
  }

  const payload = await response.json();
  const text = payload.choices?.[0]?.message?.content ?? "";
  const parsed = extractJson(text);
  const itemsOut = Array.isArray(parsed) ? parsed : parsed.items;
  if (!Array.isArray(itemsOut)) throw new Error("Response has no items array");

  const bySlug = new Map(
    itemsOut.map((item) => [`${item.kind}:${item.slug}`, item]),
  );
  const result = [];
  for (const item of items) {
    const translated = bySlug.get(`${item.kind}:${item.slug}`);
    if (!translated?.title || !translated?.description) {
      if (attempt < 3) {
        return translateBatch([item], attempt + 1);
      }
      console.warn(
        `[i18n] skipped ${item.kind}/${item.slug} (invalid response)`,
      );
      continue;
    }
    result.push({
      kind: item.kind,
      slug: item.slug,
      title: String(translated.title).trim(),
      description: String(translated.description).trim(),
      category: String(translated.category || item.category).trim(),
      tags: Array.isArray(translated.tags)
        ? translated.tags.map((tag) => String(tag).trim()).filter(Boolean)
        : item.tags,
    });
  }
  return result;
}

async function save() {
  await writeFile(
    generatedPath,
    `${JSON.stringify(generated, null, 2)}\n`,
    "utf8",
  );
}

const work = pending.slice(0, LIMIT);
let done = 0;

for (let index = 0; index < work.length; index += BATCH_SIZE) {
  const batch = work.slice(index, index + BATCH_SIZE);
  try {
    const translated = await translateBatch(batch);
    for (const item of translated) {
      generated[item.kind] ??= {};
      generated[item.kind][item.slug] = {
        title: item.title,
        description: item.description,
        category: item.category,
        tags: item.tags,
      };
      done += 1;
    }
    await save();
    console.log(`[i18n] translated ${done}/${work.length}`);
  } catch (error) {
    console.error(`[i18n] batch failed: ${error.message}`);
  }
}

await save();
console.log(`[i18n] done. Generated overrides: ${done}`);
