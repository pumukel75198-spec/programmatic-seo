/**
 * Zentrale Site-Konfiguration.
 * Hier werden alle globalen SEO-/Branding-Werte gepflegt.
 */
export const site = {
  name: "Programmatic SEO Hub",
  shortName: "pSEO Hub",
  // TODO: Vor dem Livegang auf die echte Produktionsdomain setzen.
  url: "https://example.com",
  description:
    "Entdecke APIs, Alternativen und Workflows – kuratiert für moderne Entwickler und SEO-Teams.",
  lang: "de",
  locale: "de_DE",
  author: "Programmatic SEO Hub",
  twitter: "@programmaticseo",
  defaultOgImage: "/og-default.png",
} as const;

export type SiteConfig = typeof site;
