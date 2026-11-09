/**
 * Pure, I/O-free rules for the insights generator.
 *
 * Kept separate from `generate-insights.mjs` so they can be unit-tested
 * without network access or an OpenRouter API key.
 */

/** Minimum word count for a substantial, indexable insight. */
export const MIN_ARTICLE_WORDS = 700;

const STOPWORDS = new Set([
  "the",
  "and",
  "for",
  "with",
  "from",
  "that",
  "this",
  "into",
  "your",
  "you",
  "are",
  "was",
  "were",
  "has",
  "have",
  "its",
  "their",
  "how",
  "why",
  "what",
  "when",
  "where",
  "will",
  "can",
  "new",
]);

/**
 * Terms that indicate a topic fits FlowMatrix (APIs, automation, workflows,
 * programmatic SEO, developer platforms). A candidate must hit at least
 * `minRelevance` distinct terms to be generated.
 */
export const NICHE_TERMS = [
  "api",
  "apis",
  "sdk",
  "webhook",
  "webhooks",
  "automation",
  "automate",
  "workflow",
  "workflows",
  "integration",
  "integrations",
  "endpoint",
  "endpoints",
  "developer",
  "developers",
  "programmatic seo",
  "seo",
  "no-code",
  "low-code",
  "graphql",
  "rest api",
  "oauth",
  "authentication",
  "rate limit",
  "data pipeline",
  "event-driven",
  "serverless",
  "agent",
  "agents",
  "mcp",
  "developer platform",
  "api-first",
  "open source",
  "self-hosted",
];

/** Counts distinct niche terms present in title/summary/category/feed. */
export function relevanceScore(item) {
  const haystack = [item?.title, item?.summary, item?.category, item?.feed]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  let score = 0;
  for (const term of NICHE_TERMS) {
    if (haystack.includes(term)) score += 1;
  }
  return score;
}

/** True when a candidate is on-topic enough to be generated. */
export function isRelevant(item, minScore = 2) {
  if (minScore <= 0) return true;
  return relevanceScore(item) >= minScore;
}

/** Lowercase, accent-stripped content words used for title similarity. */
export function normalizeTitle(title) {
  return String(title ?? "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]+/g, " ")
    .split(/\s+/)
    .filter((word) => word.length > 2 && !STOPWORDS.has(word));
}

/** Jaccard similarity of two titles, based on normalized word sets. */
export function jaccardSimilarity(a, b) {
  const left = new Set(normalizeTitle(a));
  const right = new Set(normalizeTitle(b));
  if (left.size === 0 || right.size === 0) return 0;

  let intersection = 0;
  for (const word of left) {
    if (right.has(word)) intersection += 1;
  }
  return intersection / (left.size + right.size - intersection);
}

/** True when a title is too similar to any already known title. */
export function isDuplicateTitle(title, existingTitles, threshold = 0.72) {
  return existingTitles.some(
    (existing) => jaccardSimilarity(title, existing) >= threshold,
  );
}

/** Word count used for the 700-word quality gate. */
export function wordCount(text) {
  return String(text ?? "")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}
