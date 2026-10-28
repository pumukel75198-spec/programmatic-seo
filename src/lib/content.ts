/**
 * Typisierte Daten-Loader für die pSEO-Pipeline.
 *
 * Die JSON-Dateien in src/data sind die Single Source of Truth.
 * Hier werden sie importiert, typisiert und über Hilfsfunktionen
 * für die dynamischen Astro-Routen bereitgestellt.
 */
import apisData from "../data/apis.json";
import alternativenData from "../data/alternativen.json";
import workflowsData from "../data/workflows.json";

export interface ApiDetails {
  provider: string;
  pricing: string;
  features: string[];
  useCase: string;
  website: string;
}

export interface ApiEntry {
  slug: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  details: ApiDetails;
}

export interface AlternativeDetails {
  original: string;
  alternatives: string[];
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

export interface WorkflowDetails {
  difficulty: string;
  duration: string;
  tools: string[];
  steps: string[];
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
export const alternativen = alternativenData as AlternativeEntry[];
export const workflows = workflowsData as WorkflowEntry[];

export function getApi(slug: string): ApiEntry | undefined {
  return apis.find((entry) => entry.slug === slug);
}

export function getAlternative(slug: string): AlternativeEntry | undefined {
  return alternativen.find((entry) => entry.slug === slug);
}

export function getWorkflow(slug: string): WorkflowEntry | undefined {
  return workflows.find((entry) => entry.slug === slug);
}

/**
 * Liefert verwandte Einträge (ohne den aktuellen) für interne Verlinkung.
 */
export function getRelated<T extends { slug: string }>(
  items: T[],
  slug: string,
  limit = 3
): T[] {
  return items.filter((item) => item.slug !== slug).slice(0, limit);
}
