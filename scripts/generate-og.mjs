/**
 * Generates OpenGraph preview images.
 *
 *   1. public/og-default.png from public/og-default.svg (site-wide fallback).
 *   2. Per-entry images under public/og/<type>/<slug>.png for APIs,
 *      alternatives, workflows and insights, so every detail page can ship a
 *      unique social preview.
 *
 * Uses sharp (libvips) for deterministic SVG -> PNG conversion. Runs before
 * `npm run build` via the `prebuild` script, and can be triggered manually
 * with `npm run og:generate`.
 */
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { stat, readFile, mkdir, copyFile } from "node:fs/promises";
import sharp from "sharp";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const publicDir = join(root, "public");
const input = join(publicDir, "og-default.svg");
const output = join(publicDir, "og-default.png");

const WIDTH = 1200;
const HEIGHT = 630;

const ACCENTS = {
  apis: "#6366f1",
  alternatives: "#22d3ee",
  workflows: "#34d399",
  insights: "#a78bfa",
};

// Build XML entities from parts so the source stays readable and is not
// mangled by HTML-entity decoding in editors/tooling.
const AMP = "&" + "amp;";
const LT = "&" + "lt;";
const GT = "&" + "gt;";
const QUOT = "&" + "quot;";
const APOS = "&" + "apos;";

const escapeXml = (value) =>
  String(value ?? "")
    .replace(/&/g, AMP)
    .replace(/</g, LT)
    .replace(/>/g, GT)
    .replace(/"/g, QUOT)
    .replace(/'/g, APOS);

function wrapText(text, maxChars, maxLines = 3) {
  const words = String(text ?? "").split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > maxChars && current) {
      lines.push(current);
      current = word;
      if (lines.length === maxLines) break;
    } else {
      current = candidate;
    }
  }
  if (current && lines.length < maxLines) lines.push(current);

  if (lines.length === maxLines) {
    const joined = lines.join(" ");
    if (joined.length < String(text ?? "").length) {
      lines[maxLines - 1] = `${lines[maxLines - 1].replace(/[.,;:]$/, "")}…`;
    }
  }

  return lines.length ? lines : [""];
}

function buildSvg({ title, subtitle, accent }) {
  const lines = wrapText(title, 26, 3);
  const lineHeight = 66;
  const blockHeight = (lines.length - 1) * lineHeight;
  const startY = 300 - blockHeight / 2;
  const textEls = lines
    .map(
      (line, index) =>
        `<text x="80" y="${startY + index * lineHeight}" font-family="Inter, Helvetica, Arial, sans-serif" font-size="56" font-weight="700" fill="#ffffff">${escapeXml(line)}</text>`
    )
    .join("\n    ");

  return `<svg width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#06070d"/>
      <stop offset="100%" stop-color="#0b1020"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.85" cy="0.15" r="0.6">
      <stop offset="0%" stop-color="${accent}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="${accent}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="${WIDTH}" height="${HEIGHT}" fill="url(#bg)"/>
  <rect width="${WIDTH}" height="${HEIGHT}" fill="url(#glow)"/>
  <rect x="80" y="80" width="56" height="56" rx="14" fill="${accent}"/>
  <text x="108" y="118" text-anchor="middle" font-family="Inter, Helvetica, Arial, sans-serif" font-size="24" font-weight="700" fill="#ffffff">FM</text>
  <text x="152" y="118" font-family="Inter, Helvetica, Arial, sans-serif" font-size="26" font-weight="600" fill="#e2e8f0">FlowMatrix</text>
  <text x="80" y="200" font-family="Inter, Helvetica, Arial, sans-serif" font-size="22" font-weight="600" fill="${accent}" letter-spacing="2">${escapeXml(String(subtitle).toUpperCase())}</text>
  ${textEls}
  <rect x="80" y="540" width="1040" height="2" fill="#ffffff" fill-opacity="0.08"/>
  <text x="80" y="585" font-family="Inter, Helvetica, Arial, sans-serif" font-size="22" fill="#94a3b8">flowmatrix.dev</text>
</svg>`;
}

async function renderDefault() {
  try {
    await stat(input);
  } catch {
    console.error(`[og] Source SVG not found: ${input}`);
    process.exit(1);
  }

  await sharp(input, { density: 144 })
    .resize(WIDTH, HEIGHT, { fit: "cover" })
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toFile(output);

  const { size } = await stat(output);
  const meta = await sharp(output).metadata();
  console.log(
    `[og] Generated ${output} (${meta.width}x${meta.height}, ${meta.format}, ${(size / 1024).toFixed(1)} KB)`
  );
}

async function loadJson(name) {
  try {
    return JSON.parse(await readFile(join(root, "src", "data", name), "utf8"));
  } catch {
    return [];
  }
}

async function renderEntry(type, entry) {
  if (!entry?.slug) return;

  const dir = join(publicDir, "og", type);
  await mkdir(dir, { recursive: true });
  const target = join(dir, `${entry.slug}.png`);

  const svg = buildSvg({
    title: entry.title ?? entry.slug,
    subtitle: entry.category ?? type,
    accent: ACCENTS[type] ?? "#6366f1",
  });

  try {
    await sharp(Buffer.from(svg))
      .png({ compressionLevel: 9, adaptiveFiltering: true })
      .toFile(target);
  } catch (error) {
    // Never break the build because of a single preview image.
    console.warn(`[og] Fallback for ${type}/${entry.slug}: ${error.message}`);
    await copyFile(output, target);
  }
}

async function renderAll() {
  const apis = await loadJson("apis.json");
  const alternatives = await loadJson("alternatives.json");
  const workflows = await loadJson("workflows.json");
  const insights = await loadJson("insights.json");
  const seed = await loadJson("insights-seed.json");

  const insightMap = new Map();
  for (const entry of [...insights, ...seed]) {
    if (entry?.slug && !insightMap.has(entry.slug)) {
      insightMap.set(entry.slug, entry);
    }
  }

  const groups = [
    ["apis", apis],
    ["alternatives", alternatives],
    ["workflows", workflows],
    ["insights", [...insightMap.values()]],
  ];

  let count = 0;
  for (const [type, entries] of groups) {
    for (const entry of entries) {
      await renderEntry(type, entry);
      count += 1;
    }
  }

  console.log(`[og] Generated ${count} per-page preview images.`);
}

await renderDefault();
await renderAll();
