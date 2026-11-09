#!/usr/bin/env node
/**
 * Content-quality audit for the pSEO dataset.
 *
 * Blocks on visible editorial problems (placeholders, missing required fields,
 * duplicate slugs/titles/descriptions) and warns about non-blocking issues
 * (legacy hidden snippets, thin insights, missing optional fields).
 *
 * Usage: npm run content:audit
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => JSON.parse(readFileSync(join(root, path), "utf8"));

const apis = read("src/data/apis.json");
const alternatives = read("src/data/alternatives.json");
const workflows = read("src/data/workflows.json");
const generatedInsights = read("src/data/insights.json");
const seedInsights = read("src/data/insights-seed.json");
const archive = read("src/data/insights-archive.json");

const wordCount = (value) =>
  String(value ?? "")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;

// The site only renders seed insights that pass the 600-word threshold.
const insights = [
  ...generatedInsights,
  ...archive.filter((entry) => entry && typeof entry === "object"),
  ...seedInsights.filter((entry) => wordCount(entry?.content) >= 600),
];

// Visible editorial text must not contain env-style placeholders. Documented
// tenant templates such as https://{your-domain}.atlassian.net are acceptable.
const VISIBLE_PLACEHOLDER =
  /YOUR_[A-Z0-9_]+|example\.com|lorem ipsum|\bdummy\b|\bplaceholder\b|TODO|FIXME|realistic fallback/i;
// Code snippets are stricter: angle/brace placeholders are not runnable.
const SNIPPET_PLACEHOLDER =
  /YOUR_[A-Z0-9_]+|<YOUR|your-[a-z]|example\.com|lorem ipsum|\bdummy\b|\bplaceholder\b|TODO|FIXME|realistic fallback/i;

const failures = [];
const warnings = [];
let hiddenSnippets = 0;
const fail = (message) => failures.push(message);
const warn = (message) => warnings.push(message);

const isString = (value) => typeof value === "string" && value.trim() !== "";
const hasPlaceholder = (value) =>
  typeof value === "string" && VISIBLE_PLACEHOLDER.test(value);

function checkDuplicates(label, items) {
  for (const field of ["slug", "title", "description"]) {
    const seen = new Set();
    for (const item of items) {
      const value = item?.[field];
      if (!isString(value)) continue;
      const key = value.trim().toLowerCase();
      if (seen.has(key)) fail(`${label}: duplicate ${field} "${value}"`);
      seen.add(key);
    }
  }
}

function requireFields(context, object, fields) {
  for (const field of fields) {
    if (!isString(object?.[field])) fail(`${context}: missing ${field}`);
  }
}

// ---------------------------------------------------------------------------
// APIs
// ---------------------------------------------------------------------------
for (const api of apis) {
  const context = `api ${api.slug}`;
  requireFields(context, api, ["slug", "title", "description", "category"]);
  if (hasPlaceholder(api.title) || hasPlaceholder(api.description)) {
    fail(`${context}: placeholder in visible text`);
  }
  if (!Array.isArray(api.tags) || api.tags.length === 0) {
    fail(`${context}: missing tags`);
  }

  const details = api.details ?? {};
  requireFields(context, details, [
    "provider",
    "pricing",
    "website",
    "useCase",
  ]);
  if (!Array.isArray(details.features) || details.features.length === 0) {
    fail(`${context}: missing details.features`);
  }
  if (!isString(details.lastVerified)) {
    warn(`${context}: missing details.lastVerified`);
  }
  if (!isString(details.docsUrl) && !isString(details.endpoint)) {
    warn(`${context}: missing docsUrl/endpoint`);
  }
}
checkDuplicates("apis", apis);

// ---------------------------------------------------------------------------
// Alternatives
// ---------------------------------------------------------------------------
for (const alternative of alternatives) {
  const context = `alternative ${alternative.slug}`;
  requireFields(context, alternative, [
    "slug",
    "title",
    "description",
    "category",
  ]);
  if (
    hasPlaceholder(alternative.title) ||
    hasPlaceholder(alternative.description)
  ) {
    fail(`${context}: placeholder in visible text`);
  }

  const details = alternative.details ?? {};
  requireFields(context, details, ["original", "bestFor", "pricing"]);
  if (!Array.isArray(details.alternatives) || details.alternatives.length < 2) {
    fail(`${context}: needs at least 2 alternatives`);
  }
  if (!Array.isArray(details.features) || details.features.length === 0) {
    fail(`${context}: missing details.features`);
  }

  const options = (details.alternatives ?? []).map((option) =>
    typeof option === "string" ? { name: option } : option,
  );
  if (options.some((option) => !isString(option.name))) {
    fail(`${context}: alternative without name`);
  }
  if (!options.some((option) => option.recommended)) {
    fail(`${context}: no recommended alternative`);
  }
  if (options.some((option) => !isString(option.bestFor))) {
    warn(`${context}: alternative missing bestFor`);
  }
}
checkDuplicates("alternatives", alternatives);

// ---------------------------------------------------------------------------
// Workflows
// ---------------------------------------------------------------------------
for (const workflow of workflows) {
  const context = `workflow ${workflow.slug}`;
  requireFields(context, workflow, [
    "slug",
    "title",
    "description",
    "category",
  ]);
  if (hasPlaceholder(workflow.title) || hasPlaceholder(workflow.description)) {
    fail(`${context}: placeholder in visible text`);
  }
  if (!isString(workflow.created_and_verified_at)) {
    fail(`${context}: missing created_and_verified_at`);
  }

  const details = workflow.details ?? {};
  requireFields(context, details, ["difficulty", "duration", "useCase"]);
  if (!Array.isArray(details.tools) || details.tools.length === 0) {
    fail(`${context}: missing tools`);
  }
  if (!Array.isArray(details.resources) || details.resources.length === 0) {
    fail(`${context}: missing resources`);
  }
  if (!Array.isArray(details.steps) || details.steps.length < 3) {
    fail(`${context}: needs at least 3 steps`);
  }

  const steps = details.steps ?? [];
  steps.forEach((step, index) => {
    const stepContext = `${context} step ${index + 1}`;
    if (typeof step === "string") {
      warn(`${stepContext}: legacy string step`);
      return;
    }
    for (const field of [
      "title",
      "description",
      "technical_explanation",
      "expectedResult",
    ]) {
      if (!isString(step?.[field])) {
        fail(`${stepContext}: missing ${field}`);
      } else if (hasPlaceholder(step[field])) {
        fail(`${stepContext}: placeholder in ${field}`);
      }
    }
    if (isString(step?.code_snippet)) {
      const lines = step.code_snippet
        .split("\n")
        .filter((line) => line.trim()).length;
      if (SNIPPET_PLACEHOLDER.test(step.code_snippet) || lines < 10) {
        hiddenSnippets += 1;
      }
    }
  });

  // Every listed tool should appear somewhere in the step content. Compare
  // significant tokens (e.g. "Together AI API" -> "together"/"ai") to avoid
  // false positives from suffixes such as "API".
  const stepText = JSON.stringify(steps).toLowerCase();
  for (const tool of details.tools ?? []) {
    const tokens = String(tool)
      .toLowerCase()
      .replace(/\bapi\b/g, " ")
      .replace(/[^a-z0-9 ]/g, " ")
      .split(/\s+/)
      .filter(
        (token) =>
          token.length > 2 && !["the", "and", "for", "inc"].includes(token),
      );
    const stem = (token) => token.replace(/(ies|es|s)$/, "");
    const mentioned =
      tokens.length === 0 ||
      tokens.some(
        (token) => stepText.includes(token) || stepText.includes(stem(token)),
      );
    if (!mentioned) {
      warn(`${context}: tool "${tool}" not mentioned in steps`);
    }
  }
}
checkDuplicates("workflows", workflows);

// ---------------------------------------------------------------------------
// Insights
// ---------------------------------------------------------------------------
for (const insight of insights) {
  if (!insight || typeof insight !== "object") continue;
  const context = `insight ${insight.slug}`;
  requireFields(context, insight, [
    "slug",
    "title",
    "excerpt",
    "content",
    "category",
    "publishedAt",
  ]);
  if (!insight.source || !isString(insight.source.url)) {
    fail(`${context}: missing source.url`);
  }
  if (hasPlaceholder(insight.title) || hasPlaceholder(insight.excerpt)) {
    fail(`${context}: placeholder in visible text`);
  }
  const words = wordCount(insight.content);
  if (words < 600) {
    warn(`${context}: thin content (${words} words) -> noindex`);
  }
}
checkDuplicates("insights", insights);

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------
console.log(
  `Content audit: ${apis.length} APIs, ${alternatives.length} alternatives, ` +
    `${workflows.length} workflows, ${insights.length} insights`,
);
console.log(
  `Hidden legacy snippets (not rendered, kit backlog): ${hiddenSnippets}`,
);

if (warnings.length > 0) {
  console.log(`\nWarnings (${warnings.length}):`);
  for (const warning of warnings.slice(0, 40)) console.log(`  ⚠ ${warning}`);
  if (warnings.length > 40) {
    console.log(`  … ${warnings.length - 40} more`);
  }
}

if (failures.length > 0) {
  console.error(`\nFAILURES (${failures.length}):`);
  for (const failure of failures) console.error(`  ✖ ${failure}`);
  process.exit(1);
}

console.log("\n✔ No blocking content-quality issues.");
