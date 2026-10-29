/**
 * Types and helpers for the generated insights (blog) section.
 *
 * Insights are produced by `scripts/generate-insights.mjs` and stored in
 * `src/data/insights.json`. Each entry contains Markdown content that is
 * rendered at build time by `src/pages/insights/[slug].astro`.
 */
import insightsData from "../data/insights.json";

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
  source: InsightSource;
  relatedWorkflow?: RelatedWorkflow | null;
  publishedAt: string;
  updatedAt?: string;
}

export const insights = insightsData as Insight[];

/** All insights, newest first. */
export function getAllInsights(): Insight[] {
  return [...insights].sort(
    (a, b) =>
      new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
  );
}

export function getInsight(slug: string): Insight | undefined {
  return insights.find((insight) => insight.slug === slug);
}

/** Related insights sharing the most tags/category, excluding the current one. */
export function getRelatedInsights(insight: Insight, limit = 3): Insight[] {
  const tags = new Set(insight.tags.map((tag) => tag.toLowerCase()));

  return insights
    .filter((candidate) => candidate.slug !== insight.slug)
    .map((candidate) => {
      const shared = candidate.tags.filter((tag) =>
        tags.has(tag.toLowerCase())
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
