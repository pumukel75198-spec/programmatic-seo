/**
 * expand-insights.mjs
 *
 * Expands the thin, feed-derived insights into substantial articles
 * (850–1,100 words) and removes off-topic entries.
 *
 * Rules:
 *  - No invented facts, statistics, quotes or studies.
 *  - Only expands on the provided summary and general background.
 *  - Writes back to the originating JSON file.
 *
 * Usage:
 *   node scripts/expand-insights.mjs
 *   node scripts/expand-insights.mjs --limit=1
 */
import { readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const insightsPath = join(root, "src", "data", "insights.json");
const seedPath = join(root, "src", "data", "insights-seed.json");

const MODEL = process.env.OPENROUTER_MODEL || "openai/gpt-4o-mini";
const BLOCKED = /5-meo-dmt|lsd|psilocybin/i;
const TARGET_WORDS = 950;

const limitArg = process.argv.find((arg) => arg.startsWith("--limit="));
const LIMIT = limitArg ? Number(limitArg.split("=")[1]) : Infinity;

async function loadEnvKey() {
  const raw = await readFile(join(root, ".env"), "utf8").catch(() => "");
  const match = raw.match(/^OPENROUTER_API_KEY=(.*)$/m);
  return (process.env.OPENROUTER_API_KEY || match?.[1] || "").trim();
}

const API_KEY = await loadEnvKey();
if (!API_KEY) {
  console.error("[insights] OPENROUTER_API_KEY is missing.");
  process.exit(1);
}

const wordCount = (text) =>
  String(text ?? "")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;

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
    if (start !== -1 && end > start)
      return JSON.parse(cleaned.slice(start, end + 1));
    throw new Error("No JSON object in response");
  }
}

async function expand(insight) {
  const prompt = [
    "Du bist ein erfahrener Tech-Redakteur für FlowMatrix (APIs, Alternativen und Automatisierungs-Workflows).",
    `Erweitere den folgenden englischsprachigen Artikel auf etwa ${TARGET_WORDS} Wörter (850–1100).`,
    "Regeln:",
    "- Erfinde KEINE Fakten, Zahlen, Zitate, Studien oder Produktfeatures.",
    "- Nutze ausschließlich den vorhandenen Inhalt und allgemein bekannten Kontext.",
    "- Struktur: Einleitung, 3–5 H2-Abschnitte, Key Takeaways als Bulletlist, FAQ mit 3 Fragen, Fazit.",
    "- Natürliches, redaktionelles Englisch; kein Marketing-Sprech.",
    "- Gib ausschließlich valides JSON zurück:",
    '{"excerpt":"kurzer Teaser (max. 200 Zeichen)","content":"vollständiger Markdown-Artikel"}',
    "",
    JSON.stringify(
      {
        title: insight.title,
        excerpt: insight.excerpt,
        existingContent: insight.content,
        source: insight.source,
        category: insight.category,
        tags: insight.tags,
      },
      null,
      2,
    ),
  ].join("\n");

  const response = await fetch(
    "https://openrouter.ai/api/v1/chat/completions",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://flowmatrix.dev",
        "X-Title": "FlowMatrix insight expansion",
      },
      body: JSON.stringify({
        model: MODEL,
        temperature: 0.4,
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
  const parsed = extractJson(payload.choices?.[0]?.message?.content ?? "");
  if (!parsed?.content || !parsed?.excerpt) {
    throw new Error("Response missing content/excerpt");
  }
  return {
    excerpt: String(parsed.excerpt).trim(),
    content: String(parsed.content).trim(),
  };
}

const insights = JSON.parse(await readFile(insightsPath, "utf8"));
const seed = JSON.parse(await readFile(seedPath, "utf8"));

// Remove off-topic articles from the generated feed.
const cleaned = insights.filter(
  (entry) => !BLOCKED.test(`${entry.title} ${entry.content}`),
);
const removed = insights.length - cleaned.length;
if (removed > 0) {
  await writeFile(
    insightsPath,
    `${JSON.stringify(cleaned, null, 2)}\n`,
    "utf8",
  );
  console.log(`[insights] removed ${removed} off-topic article(s).`);
}

// Expand all generated articles + one relevant seed article so the feed has
// six substantial, indexable posts.
const targets = [
  ...cleaned.map((entry) => ({ entry, file: "generated" })),
  ...seed
    .filter((entry) => !BLOCKED.test(`${entry.title} ${entry.content}`))
    .slice(0, 1)
    .map((entry) => ({ entry, file: "seed" })),
].slice(0, LIMIT);

let done = 0;
for (const target of targets) {
  const { entry, file } = target;
  try {
    let result = await expand(entry);
    if (wordCount(result.content) < 700) {
      result = await expand(entry);
    }
    entry.excerpt = result.excerpt;
    entry.content = result.content;
    entry.updatedAt = new Date().toISOString();
    done += 1;
    const outPath = file === "generated" ? insightsPath : seedPath;
    if (file === "generated") {
      await writeFile(outPath, `${JSON.stringify(cleaned, null, 2)}\n`, "utf8");
    } else {
      await writeFile(outPath, `${JSON.stringify(seed, null, 2)}\n`, "utf8");
    }
    console.log(
      `[insights] expanded ${entry.slug} (${wordCount(result.content)} words)`,
    );
  } catch (error) {
    console.error(`[insights] failed ${entry.slug}: ${error.message}`);
  }
}

console.log(`[insights] done. Expanded ${done} article(s).`);
