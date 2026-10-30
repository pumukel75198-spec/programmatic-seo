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
  lang: "en",
  locale: "en_US",
  author: "FlowMatrix",
  twitter: "@flowmatrix",
  defaultOgImage: "/og-default.png",
} as const;

export type SiteConfig = typeof site;
