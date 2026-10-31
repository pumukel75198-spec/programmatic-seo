/**
 * Build-time search index for the Intent-Finder.
 *
 * Combines APIs, alternatives and workflows into one flat, localized list.
 * The index is embedded into the /discover page as JSON and searched
 * client-side – no backend, no external search service.
 */
import { apis, alternatives, workflows } from "./content";
import {
  localizeApi,
  localizeAlternative,
  localizeWorkflow,
} from "../i18n/content";

export type SearchItemType = "api" | "alternative" | "workflow";

export interface SearchItem {
  type: SearchItemType;
  slug: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  url: string;
  /** Short secondary line, e.g. pricing or difficulty. */
  meta?: string;
}

/**
 * Builds the localized search index for a given locale.
 * URLs always point to the localized detail pages.
 */
export function buildSearchIndex(lang: string): SearchItem[] {
  const apiItems: SearchItem[] = apis.map((entry) => {
    const api = localizeApi(entry, lang);
    return {
      type: "api",
      slug: api.slug,
      title: api.title,
      description: api.description,
      category: api.category,
      tags: api.tags ?? [],
      url: `/${lang}/apis/${api.slug}/`,
      meta: api.details?.pricing,
    };
  });

  const alternativeItems: SearchItem[] = alternatives.map((entry) => {
    const alternative = localizeAlternative(entry, lang);
    return {
      type: "alternative",
      slug: alternative.slug,
      title: alternative.title,
      description: alternative.description,
      category: alternative.category,
      tags: alternative.tags ?? [],
      url: `/${lang}/alternatives/${alternative.slug}/`,
      meta: alternative.details?.bestFor,
    };
  });

  const workflowItems: SearchItem[] = workflows.map((entry) => {
    const workflow = localizeWorkflow(entry, lang);
    return {
      type: "workflow",
      slug: workflow.slug,
      title: workflow.title,
      description: workflow.description,
      category: workflow.category,
      tags: workflow.tags ?? [],
      url: `/${lang}/workflows/${workflow.slug}/`,
      meta: [workflow.details?.difficulty, workflow.details?.duration]
        .filter(Boolean)
        .join(" · "),
    };
  });

  return [...apiItems, ...alternativeItems, ...workflowItems];
}
