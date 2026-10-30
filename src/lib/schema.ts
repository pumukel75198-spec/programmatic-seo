/**
 * JSON-LD / Schema.org helpers for structured data.
 * Improves rich results and machine readability of the pSEO pages.
 */
import { site } from "./site";
import type { AlternativeEntry, ApiEntry, WorkflowEntry } from "./content";

export type JsonLd = Record<string, unknown>;

const absolute = (path: string) => new URL(path, site.url).toString();

export function websiteSchema(): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: site.name,
    url: site.url,
    description: site.description,
    inLanguage: site.lang,
  };
}

export function organizationSchema(): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: site.name,
    url: site.url,
    logo: absolute("/favicon.svg"),
  };
}

export function breadcrumbSchema(
  items: { name: string; url: string }[]
): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: absolute(item.url),
    })),
  };
}

export function softwareApplicationSchema(api: ApiEntry, lang = "en"): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: api.title,
    description: api.description,
    applicationCategory: api.category,
    operatingSystem: "Web",
    url: absolute(`/${lang}/apis/${api.slug}/`),
    keywords: api.tags.join(", "),
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      description: api.details.pricing,
    },
  };
}

export function articleSchema(entry: AlternativeEntry, lang = "en"): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: entry.title,
    description: entry.description,
    articleSection: entry.category,
    keywords: entry.tags.join(", "),
    url: absolute(`/${lang}/alternatives/${entry.slug}/`),
    inLanguage: lang,
    author: { "@type": "Organization", name: site.name },
    publisher: { "@type": "Organization", name: site.name },
  };
}

export function howToSchema(workflow: WorkflowEntry, lang = "en"): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: workflow.title,
    description: workflow.description,
    totalTime: workflow.details.duration,
    url: absolute(`/${lang}/workflows/${workflow.slug}/`),
    inLanguage: lang,
    tool: workflow.details.tools.map((tool) => ({
      "@type": "HowToTool",
      name: tool,
    })),
    step: workflow.details.steps.map((step, index) => {
      const title = typeof step === "string" ? step : step.title;
      const text =
        typeof step === "string" ? step : step.description ?? step.title;
      return {
        "@type": "HowToStep",
        position: index + 1,
        name: title,
        text,
      };
    }),
  };
}

export function itemListSchema(
  name: string,
  items: { name: string; url: string }[]
): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name,
    numberOfItems: items.length,
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      url: absolute(item.url),
    })),
  };
}
