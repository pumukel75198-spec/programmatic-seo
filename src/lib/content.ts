/**
 * Typed data loaders for the pSEO pipeline.
 *
 * The JSON files in src/data are the single source of truth.
 * They are imported, typed and exposed through helper functions
 * for the dynamic Astro routes.
 */
import apisData from "../data/apis.json";
import alternativesData from "../data/alternatives.json";
import workflowsData from "../data/workflows.json";

export interface ApiDetails {
  provider: string;
  pricing: string;
  features: string[];
  useCase: string;
  website: string;
  /** Optional technical details for developer-focused API pages. */
  endpoint?: string;
  authentication?: string;
  apiKeyRequired?: boolean;
  sdkLanguages?: string[];
  rateLimit?: string;
  docsUrl?: string;
  /** ISO date of the last manual verification of the technical details. */
  lastVerified?: string;
}

export interface ApiEntry {
  slug: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  details: ApiDetails;
}

export interface AlternativeOption {
  name: string;
  description?: string;
  pros?: string[];
  cons?: string[];
  bestFor?: string;
  recommended?: boolean;
  /** Optional fallback URL if the tool is not in src/lib/tools.ts. */
  url?: string;
}

export interface AlternativeDetails {
  original: string;
  /** Alternatives can be plain names (legacy) or enriched objects. */
  alternatives: (string | AlternativeOption)[];
  bestFor: string;
  pricing: string;
  features: string[];
}

export interface AlternativeEntry {
  slug: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  details: AlternativeDetails;
}

export interface WorkflowStepLink {
  label: string;
  url: string;
}

export interface WorkflowStep {
  title: string;
  description?: string;
  links?: WorkflowStepLink[];
}

export interface WorkflowResource {
  label: string;
  url: string;
}

export interface WorkflowDetails {
  difficulty: string;
  duration: string;
  tools: string[];
  /** Steps can be plain strings (legacy) or enriched objects. */
  steps: (string | WorkflowStep)[];
  useCase: string;
  prerequisites?: string[];
  glossary?: { term: string; definition: string }[];
  troubleshooting?: { problem: string; solution: string }[];
  resources?: WorkflowResource[];
}

export interface WorkflowEntry {
  slug: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  /** ISO-like timestamp of generation and live verification. */
  created_and_verified_at?: string;
  details: WorkflowDetails;
}

export const apis = apisData as ApiEntry[];
export const alternatives = alternativesData as AlternativeEntry[];
export const workflows = workflowsData as WorkflowEntry[];

export function getApi(slug: string): ApiEntry | undefined {
  return apis.find((entry) => entry.slug === slug);
}

export function getAlternative(slug: string): AlternativeEntry | undefined {
  return alternatives.find((entry) => entry.slug === slug);
}

export function getWorkflow(slug: string): WorkflowEntry | undefined {
  return workflows.find((entry) => entry.slug === slug);
}

/**
 * Returns related entries (excluding the current one) for internal linking.
 */
export function getRelated<T extends { slug: string }>(
  items: T[],
  slug: string,
  limit = 3,
): T[] {
  return items.filter((item) => item.slug !== slug).slice(0, limit);
}

/**
 * Cross-category related entries based on shared tags and category.
 * Used to link APIs ↔ alternatives ↔ workflows to each other.
 *
 * With `fill = true`, the result is padded with same-category entries (then
 * alphabetically) so every page gets a stable set of internal links even when
 * tags do not overlap. This keeps the crawl graph connected without inventing
 * unrelated recommendations.
 */
export function getRelatedByTags<
  T extends { slug: string; tags: string[]; category: string; title: string },
>(
  items: T[],
  current: { slug: string; tags: string[]; category: string },
  limit = 3,
  fill = false,
): T[] {
  const tags = new Set((current.tags ?? []).map((tag) => tag.toLowerCase()));

  const scored = items
    .filter((item) => item.slug !== current.slug)
    .map((item) => {
      const shared = (item.tags ?? []).filter((tag) =>
        tags.has(tag.toLowerCase()),
      ).length;
      const sameCategory =
        item.category.toLowerCase() === current.category.toLowerCase() ? 1 : 0;
      return { item, score: shared * 2 + sameCategory };
    })
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(({ item }) => item);

  if (!fill || scored.length >= limit) return scored;

  const seen = new Set(scored.map((item) => item.slug));
  const fallback = items
    .filter((item) => item.slug !== current.slug && !seen.has(item.slug))
    .sort((a, b) => {
      const aCategory =
        a.category.toLowerCase() === current.category.toLowerCase() ? 0 : 1;
      const bCategory =
        b.category.toLowerCase() === current.category.toLowerCase() ? 0 : 1;
      return aCategory - bCategory || a.title.localeCompare(b.title);
    });

  for (const item of fallback) {
    if (scored.length >= limit) break;
    scored.push(item);
  }

  return scored;
}
