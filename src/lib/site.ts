/**
 * Central site configuration.
 * All global SEO/branding values are maintained here.
 */
export const site = {
  name: "Programmatic SEO Hub",
  shortName: "pSEO Hub",
  // TODO: Set this to the real production domain before going live.
  url: "https://example.com",
  description:
    "Discover APIs, alternatives and workflows – curated for modern developers and SEO teams.",
  lang: "en",
  locale: "en_US",
  author: "Programmatic SEO Hub",
  twitter: "@programmaticseo",
  defaultOgImage: "/og-default.png",
} as const;

export type SiteConfig = typeof site;
