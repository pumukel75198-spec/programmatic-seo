// @ts-check
import { readFileSync } from "node:fs";
import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";

// Thin/off-topic insights are rendered with noindex, so they must not be in
// the sitemap either. The same thresholds live in src/lib/insights.ts.
const insights = [
  ...JSON.parse(
    readFileSync(new URL("./src/data/insights.json", import.meta.url), "utf8"),
  ),
  ...JSON.parse(
    readFileSync(
      new URL("./src/data/insights-archive.json", import.meta.url),
      "utf8",
    ),
  ),
  ...JSON.parse(
    readFileSync(
      new URL("./src/data/insights-seed.json", import.meta.url),
      "utf8",
    ),
  ),
].filter((entry) => entry && typeof entry === "object");
const BLOCKED_INSIGHT_TOPIC = /5-meo-dmt|lsd|psilocybin/i;
const thinInsights = new Set(
  insights
    .filter((entry) => {
      const words = String(entry.content ?? "")
        .trim()
        .split(/\s+/)
        .filter(Boolean).length;
      return (
        words < 600 ||
        BLOCKED_INSIGHT_TOPIC.test(`${entry.title} ${entry.content}`)
      );
    })
    .map((entry) => entry.slug),
);

/** @type {string[]} */
const locales = ["en"];

// Canonical production origin (also used for sitemap filtering).
const SITE = "https://flowmatrix.dev";

// Date of the last intentional content review. Used as a fallback when a page
// has no more specific timestamp.
const CONTENT_UPDATED = "2026-10-31";

const workflowsData = JSON.parse(
  readFileSync(new URL("./src/data/workflows.json", import.meta.url), "utf8"),
);
const apisData = JSON.parse(
  readFileSync(new URL("./src/data/apis.json", import.meta.url), "utf8"),
);

/**
 * Convert "YYYY-MM-DD HH:MM UTC" / ISO / date-only to ISO, or null.
 * @param {unknown} value
 */
const toIsoDate = (value) => {
  if (typeof value !== "string" || !value.trim()) return null;
  const normalized = value.replace(" UTC", "Z").replace(" ", "T");
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
};

// Per-page lastmod derived from real data timestamps.
/** @type {Record<string, string>} */
const lastmodByPath = {};
for (const workflow of workflowsData) {
  const iso = toIsoDate(workflow?.created_and_verified_at);
  if (iso) lastmodByPath[`/en/workflows/${workflow.slug}/`] = iso;
}
for (const api of apisData) {
  const iso = toIsoDate(api?.details?.lastVerified);
  if (iso) lastmodByPath[`/en/apis/${api.slug}/`] = iso;
}
for (const insight of insights) {
  if (!insight?.slug) continue;
  const iso = toIsoDate(insight.updatedAt ?? insight.publishedAt);
  if (iso) lastmodByPath[`/insights/${insight.slug}/`] = iso;
}

// These legacy paths are client-side redirect shims. They must never appear
// in the sitemap and are additionally marked noindex in their page templates.
const LEGACY_PAGE = /^\/(apis|alternatives|workflows)\/[^/]+\/?$/;
const LEGACY_INDEX = /^\/(apis|alternatives|workflows)\/?$/;

// https://astro.build/config
export default defineConfig({
  // Static export: generates plain HTML/CSS/JS in ./dist
  output: "static",

  // Production domain – used for canonical URLs and the sitemap.
  site: SITE,

  i18n: {
    defaultLocale: "en",
    locales,
    routing: {
      prefixDefaultLocale: true,
      // The root redirect is handled by src/pages/index.astro. Letting Astro
      // also generate it causes a duplicate `/` route warning.
      redirectToDefaultLocale: false,
    },
  },

  // Legacy unlocalized paths and all /de/* URLs are redirected with real
  // HTTP 301s via public/_redirects (Cloudflare Pages). Astro's static
  // `redirects` generated meta-refresh pages, which Google reports as
  // "page with redirect" and which caused duplicate/404 URL signals.

  integrations: [
    sitemap({
      filter: (page) => {
        const path = new URL(page).pathname;
        // Never advertise redirects or error pages as indexable content.
        if (page.includes("/404") || page === `${SITE}/`) return false;
        if (LEGACY_PAGE.test(path) || LEGACY_INDEX.test(path)) return false;

        // Keep thin/off-topic insights out of the sitemap (they are noindex).
        const insightPage = path.match(/^\/insights\/([^/]+)\/?$/);
        if (insightPage && thinInsights.has(insightPage[1])) return false;

        return true;
      },
      // Non-localized pages (e.g. /insights/*) exist only once. Do not emit
      // /de/... alternates for them in the sitemap, otherwise crawlers see
      // hreflang targets that 404.
      serialize(item) {
        // One alternate per language is enough. The legacy redirect shims used
        // to produce a duplicate en-US entry for the same page.
        const seen = new Set();
        const links = (item.links ?? []).filter((link) => {
          const key = link.lang;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

        const pathname = new URL(item.url).pathname;
        const lastmod = lastmodByPath[pathname] ?? CONTENT_UPDATED;

        if (item.url.includes("/insights/")) {
          return { ...item, lastmod, links: [] };
        }
        return { ...item, lastmod, links };
      },
      i18n: {
        defaultLocale: "en",
        locales: {
          en: "en-US",
        },
      },
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
});
