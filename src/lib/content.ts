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

export interface WorkflowDetails {
  difficulty: string;
  duration: string;
  tools: string[];
  /** Steps can be plain strings (legacy) or enriched objects. */
  steps: (string | WorkflowStep)[];
  useCase: string;
}

export interface WorkflowEntry {
  slug: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
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
  limit = 3
): T[] {
  return items.filter((item) => item.slug !== slug).slice(0, limit);
}
