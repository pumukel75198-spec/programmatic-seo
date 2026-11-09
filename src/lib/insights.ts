/**
 * Types and helpers for the generated insights (blog) section.
 *
 * Generated articles live in `src/data/insights.json` and are produced by
 * `scripts/generate-insights.mjs`. Curated evergreen articles live in
 * `src/data/insights-seed.json` and act as a fallback so the feed always
 * shows at least `MIN_INSIGHTS` high-quality posts.
 *
 * When an article leaves the visible window it is moved to
 * `src/data/insights-archive.json` **with its full content**. Archived
 * articles keep their own pages, so old URLs never turn into 404s or
 * redirects and keep their search value.
 */
import insightsData from "../data/insights.json";
import seedData from "../data/insights-seed.json";
import archiveData from "../data/insights-archive.json";

export interface InsightSource {
  name: string;
  url: string;
  guid?: string;
  publishedAt?: string;
}

export interface RelatedWorkflow {
  slug: string;
  title: string;
  reason: string;
}

export interface Insight {
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  category: string;
  tags: string[];
  /** Language the article was generated in (defaults to "en"). */
  lang?: string;
  source: InsightSource;
  relatedWorkflow?: RelatedWorkflow | null;
  publishedAt: string;
  updatedAt?: string;
  /** Set when the article was moved into the full-text archive. */
  archivedAt?: string;
}

/** The feed must always show at least this many articles. */
export const MIN_INSIGHTS = 6;

/** Maximum number of posts listed on the insights index. */
export const MAX_VISIBLE_INSIGHTS = 40;

/**
 * Minimum length before an insight is allowed into the index. Short,
 * feed-derived summaries are kept for users but marked noindex until they are
 * genuinely expanded by an editor.
 */
export const MIN_INDEXABLE_WORDS = 600;

const BLOCKED_TOPICS = /5-meo-dmt|lsd|psilocybin/i;

const generated = insightsData as Insight[];
const seed = seedData as Insight[];

function isRenderableInsight(value: unknown): value is Insight {
  if (!value || typeof value !== "object") return false;
  const entry = value as Record<string, unknown>;
  return (
    typeof entry.slug === "string" &&
    typeof entry.title === "string" &&
    typeof entry.excerpt === "string" &&
    typeof entry.content === "string" &&
    typeof entry.category === "string" &&
    Array.isArray(entry.tags) &&
    typeof entry.publishedAt === "string" &&
    !!entry.source &&
    typeof entry.source === "object"
  );
}

/** Full-text archive of insights that left the visible window. */
const archived = (archiveData as unknown[]).filter(isRenderableInsight);

export function insightWordCount(insight: Insight): number {
  return insight.content.trim().split(/\s+/).filter(Boolean).length;
}

export function isInsightIndexable(insight: Insight): boolean {
  const haystack = `${insight.title} ${insight.excerpt} ${insight.content}`;
  return (
    insightWordCount(insight) >= MIN_INDEXABLE_WORDS &&
    !BLOCKED_TOPICS.test(haystack)
  );
}

function sortNewestFirst(items: Insight[]): Insight[] {
  return [...items].sort(
    (a, b) =>
      new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime(),
  );
}

function dedupeBySlug(items: Insight[]): Insight[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.slug)) return false;
    seen.add(item.slug);
    return true;
  });
}

/**
 * Visible set: generated articles first. If there are fewer than
 * `MIN_INSIGHTS`, curated seed articles fill the gap. Seed articles never
 * replace generated ones.
 */
function buildVisible(): Insight[] {
  const merged = [...generated];
  const slugs = new Set(merged.map((insight) => insight.slug));

  for (const fallback of seed) {
    if (merged.length >= MIN_INSIGHTS) break;
    if (slugs.has(fallback.slug)) continue;
    merged.push(fallback);
    slugs.add(fallback.slug);
  }

  return merged;
}

/** Visible set for the index (generated first, seed fallback). */
export const insights = buildVisible();

/**
 * All renderable insights: generated + full-text archive + indexable seeds.
 * Archived posts keep their own pages so old URLs never 404 or redirect.
 */
export const allInsights = sortNewestFirst(
  dedupeBySlug([...generated, ...archived, ...seed.filter(isInsightIndexable)]),
);

/** All insights, newest first. Used for static paths and related links. */
export function getAllInsights(): Insight[] {
  return allInsights;
}

/** Newest insights for the index / RSS feed. */
export function getLatestInsights(limit = MAX_VISIBLE_INSIGHTS): Insight[] {
  return allInsights.slice(0, Math.max(0, limit));
}

export function getInsight(slug: string): Insight | undefined {
  return allInsights.find((insight) => insight.slug === slug);
}

/** Related insights sharing the most tags/category, excluding the current one. */
export function getRelatedInsights(insight: Insight, limit = 3): Insight[] {
  const tags = new Set(insight.tags.map((tag) => tag.toLowerCase()));

  return allInsights
    .filter((candidate) => candidate.slug !== insight.slug)
    .map((candidate) => {
      const shared = candidate.tags.filter((tag) =>
        tags.has(tag.toLowerCase()),
      ).length;
      const sameCategory =
        candidate.category.toLowerCase() === insight.category.toLowerCase()
          ? 1
          : 0;
      return { candidate, score: shared * 2 + sameCategory };
    })
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(({ candidate }) => candidate);
}
