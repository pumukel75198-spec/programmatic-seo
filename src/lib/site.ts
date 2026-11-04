/**
 * Central site configuration.
 * All global SEO/branding values are maintained here.
 */
export const site = {
  name: "FlowMatrix",
  shortName: "FlowMatrix",
  url: "https://flowmatrix.dev",
  description:
    "Discover APIs, alternatives and workflows – curated for modern developers and SEO teams.",
  /** ISO date of the last intentional editorial review of the dataset. */
  contentUpdated: "2026-10-31",
  lang: "en",
  locale: "en_US",
  author: "FlowMatrix",
  twitter: "@flowmatrix",
  defaultOgImage: "/og-default.png",
} as const;

export type SiteConfig = typeof site;
