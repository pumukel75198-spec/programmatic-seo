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
    potentialAction: {
      "@type": "SearchAction",
      target: `${absolute("/en/discover/")}?q={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };
}

export function organizationSchema(): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: site.name,
    url: site.url,
    description: site.description,
    logo: {
      "@type": "ImageObject",
      url: absolute("/og-default.png"),
      width: 1200,
      height: 630,
    },
    sameAs: [
      new URL(
        `https://twitter.com/${site.twitter.replace("@", "")}`,
      ).toString(),
    ],
  };
}

export function breadcrumbSchema(
  items: { name: string; url: string }[],
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

/**
 * Product/Offer schema for the paid premium assets (PDF, Python script,
 * Playbook). Only call this when a real checkout URL is configured —
 * otherwise Google would receive an unusable offer.
 */
export function productSchema(input: {
  name: string;
  description: string;
  url: string;
  price: string;
  priceCurrency?: string;
  checkoutUrl: string;
  category?: string;
}): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: input.name,
    description: input.description,
    category: input.category,
    url: absolute(input.url),
    brand: { "@type": "Brand", name: site.name },
    offers: {
      "@type": "Offer",
      url: input.checkoutUrl,
      price: input.price,
      priceCurrency: input.priceCurrency ?? "EUR",
      availability: "https://schema.org/InStock",
    },
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
    dateModified: site.contentUpdated,
    // Deliberately no `offers`: API pricing is usage-based/custom and a
    // hard-coded price of 0 would be misleading structured data.
    featureList: api.details.features,
    provider: {
      "@type": "Organization",
      name: api.details.provider,
      url: api.details.website,
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
    dateModified: site.contentUpdated,
    author: {
      "@type": "Organization",
      name: site.name,
      url: site.url,
    },
    publisher: {
      "@type": "Organization",
      name: site.name,
      url: site.url,
      logo: {
        "@type": "ImageObject",
        url: absolute("/og-default.png"),
      },
    },
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
    dateModified: site.contentUpdated,
    author: {
      "@type": "Organization",
      name: site.name,
      url: site.url,
    },
    publisher: {
      "@type": "Organization",
      name: site.name,
      url: site.url,
      logo: {
        "@type": "ImageObject",
        url: absolute("/og-default.png"),
      },
    },
    tool: workflow.details.tools.map((tool) => ({
      "@type": "HowToTool",
      name: tool,
    })),
    step: workflow.details.steps.map((step, index) => {
      const title = typeof step === "string" ? step : step.title;
      const text =
        typeof step === "string" ? step : (step.description ?? step.title);
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
  items: { name: string; url: string }[],
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
