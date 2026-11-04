/**
 * generate-translation-manifest.mjs
 *
 * Extracts which data records have a real German override in
 * `src/i18n/content.ts` and writes a small manifest that `astro.config.mjs`
 * can read while building the sitemap.
 *
 * The sitemap must not advertise `/de/...` URLs for pages that still show the
 * English body (they are marked noindex and canonicalise to English).
 */
import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const sourceFile = join(root, "src", "i18n", "content.ts");
const generatedFile = join(root, "src", "i18n", "de-overrides.generated.json");
const outputFile = join(root, "src", "data", "translation-coverage.json");

const source = await readFile(sourceFile, "utf8");

function extractBlock(exportName) {
  const start = source.indexOf(`export const ${exportName}`);
  if (start === -1) return "";

  const deMatch = source.slice(start).match(/de:\s*\{([\s\S]*?)\n {2}\},\n\};/);
  return deMatch?.[1] ?? "";
}

function slugsIn(block) {
  return [...block.matchAll(/^ {4}"([^"]+)":\s*\{/gm)].map((match) => match[1]);
}

let generated = {};
if (existsSync(generatedFile)) {
  generated = JSON.parse(await readFile(generatedFile, "utf8"));
}

const manifest = {
  apis: [
    ...new Set([
      ...slugsIn(extractBlock("manualApiOverrides")),
      ...Object.keys(generated.apis ?? {}),
    ]),
  ],
  alternatives: [
    ...new Set([
      ...slugsIn(extractBlock("manualAlternativeOverrides")),
      ...Object.keys(generated.alternatives ?? {}),
    ]),
  ],
  workflows: [
    ...new Set([
      ...slugsIn(extractBlock("manualWorkflowOverrides")),
      ...Object.keys(generated.workflows ?? {}),
    ]),
  ],
};

await writeFile(outputFile, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

console.log(
  `[i18n] translation manifest: ${manifest.apis.length} APIs, ` +
    `${manifest.alternatives.length} alternatives, ` +
    `${manifest.workflows.length} workflows (de)`,
);
