/**
 * Central tool & affiliate link configuration.
 *
 * Tools mentioned across API and workflow records are mapped to their
 * official URLs and optional affiliate URLs. Templates use these helpers
 * to render tools as clean, sponsored links.
 *
 * TODO: Replace the placeholder `?ref=programmatic-seo` parameters with
 * your real affiliate parameters.
 */
export interface ToolConfig {
  name: string;
  url: string;
  affiliateUrl?: string;
  sponsored?: boolean;
}

const REF = "?ref=programmatic-seo";

export const tools: Record<string, ToolConfig> = {
  "OpenAI API": {
    name: "OpenAI API",
    url: "https://platform.openai.com/",
    affiliateUrl: `https://platform.openai.com/${REF}`,
    sponsored: true,
  },
  Make: {
    name: "Make",
    url: "https://www.make.com/",
    affiliateUrl: `https://www.make.com/en/register${REF}`,
    sponsored: true,
  },
  Notion: {
    name: "Notion",
    url: "https://www.notion.so/",
    affiliateUrl: `https://www.notion.so/${REF}`,
    sponsored: true,
  },
  "Notion API": {
    name: "Notion API",
    url: "https://developers.notion.com/",
    affiliateUrl: `https://www.notion.so/${REF}`,
    sponsored: true,
  },
  Buffer: {
    name: "Buffer",
    url: "https://buffer.com/",
    affiliateUrl: `https://buffer.com/${REF}`,
    sponsored: true,
  },
  Supabase: {
    name: "Supabase",
    url: "https://supabase.com/",
    affiliateUrl: `https://supabase.com/${REF}`,
    sponsored: true,
  },
  Astro: {
    name: "Astro",
    url: "https://astro.build/",
  },
  n8n: {
    name: "n8n",
    url: "https://n8n.io/",
    affiliateUrl: `https://n8n.io/${REF}`,
    sponsored: true,
  },
  "Resend Email API": {
    name: "Resend Email API",
    url: "https://resend.com/",
    affiliateUrl: `https://resend.com/${REF}`,
    sponsored: true,
  },
  "Resend API": {
    name: "Resend API",
    url: "https://resend.com/",
    affiliateUrl: `https://resend.com/${REF}`,
    sponsored: true,
  },
  "Cal.com": {
    name: "Cal.com",
    url: "https://cal.com/",
  },
  "Shopify Admin API": {
    name: "Shopify Admin API",
    url: "https://shopify.dev/docs/api/admin",
  },
  "Cohere Embed API": {
    name: "Cohere Embed API",
    url: "https://cohere.com/",
  },
  "Pinecone Vector API": {
    name: "Pinecone Vector API",
    url: "https://www.pinecone.io/",
  },
  "Cloudflare Workers API": {
    name: "Cloudflare Workers API",
    url: "https://workers.cloudflare.com/",
  },
  "Mapbox Maps API": {
    name: "Mapbox Maps API",
    url: "https://www.mapbox.com/",
  },
  "Deepgram Speech API": {
    name: "Deepgram Speech API",
    url: "https://deepgram.com/",
  },
  "PostHog Analytics API": {
    name: "PostHog Analytics API",
    url: "https://posthog.com/",
  },
  "GitHub Alternatives": {
    name: "GitHub",
    url: "https://github.com/",
  },
  Slack: {
    name: "Slack",
    url: "https://slack.com/",
  },
  "Zendesk Alternatives": {
    name: "Zendesk",
    url: "https://www.zendesk.com/",
  },
  "Stripe Payments API": {
    name: "Stripe Payments API",
    url: "https://stripe.com/",
  },
  "Google Search Console API": {
    name: "Google Search Console API",
    url: "https://developers.google.com/webmaster-tools",
  },
  Vercel: {
    name: "Vercel",
    url: "https://vercel.com/",
    affiliateUrl: `https://vercel.com/${REF}`,
    sponsored: true,
  },
  "Airtable API": {
    name: "Airtable API",
    url: "https://airtable.com/developers/web/api",
  },
  Neon: {
    name: "Neon",
    url: "https://neon.tech/",
  },
  "OpenWeather Weather API": {
    name: "OpenWeather Weather API",
    url: "https://openweathermap.org/api",
  },
  "Cloudflare Pages": {
    name: "Cloudflare Pages",
    url: "https://pages.cloudflare.com/",
  },
  Figma: {
    name: "Figma",
    url: "https://www.figma.com/",
  },
  Airtable: {
    name: "Airtable",
    url: "https://airtable.com/",
  },
  Trello: {
    name: "Trello",
    url: "https://trello.com/",
  },
  "Google Analytics": {
    name: "Google Analytics",
    url: "https://analytics.google.com/",
  },
  HubSpot: {
    name: "HubSpot",
    url: "https://www.hubspot.com/",
  },
  Asana: {
    name: "Asana",
    url: "https://asana.com/",
  },
  Dropbox: {
    name: "Dropbox",
    url: "https://www.dropbox.com/",
  },
  Calendly: {
    name: "Calendly",
    url: "https://calendly.com/",
  },
  WordPress: {
    name: "WordPress",
    url: "https://wordpress.org/",
  },
  Shopify: {
    name: "Shopify",
    url: "https://www.shopify.com/",
  },
  "Monday.com": {
    name: "Monday.com",
    url: "https://monday.com/",
  },
  ClickUp: {
    name: "ClickUp",
    url: "https://clickup.com/",
  },
  Miro: {
    name: "Miro",
    url: "https://miro.com/",
  },
  Loom: {
    name: "Loom",
    url: "https://www.loom.com/",
  },
  Intercom: {
    name: "Intercom",
    url: "https://www.intercom.com/",
  },
  Zendesk: {
    name: "Zendesk",
    url: "https://www.zendesk.com/",
  },
  Jira: {
    name: "Jira",
    url: "https://www.atlassian.com/software/jira",
  },
  GitHub: {
    name: "GitHub",
    url: "https://github.com/",
  },
  GitLab: {
    name: "GitLab",
    url: "https://about.gitlab.com/",
  },
  Bitbucket: {
    name: "Bitbucket",
    url: "https://bitbucket.org/",
  },
  Netlify: {
    name: "Netlify",
    url: "https://www.netlify.com/",
  },
  Zapier: {
    name: "Zapier",
    url: "https://zapier.com/",
  },
};

export interface ToolLink {
  name: string;
  href: string;
  sponsored: boolean;
}

export function getToolLink(name: string): ToolLink | null {
  const tool = tools[name];
  if (!tool) return null;
  return {
    name: tool.name,
    href: tool.affiliateUrl ?? tool.url,
    sponsored: tool.sponsored ?? Boolean(tool.affiliateUrl),
  };
}

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, "\u0026amp;")
    .replace(/</g, "\u0026lt;")
    .replace(/>/g, "\u0026gt;")
    .replace(/"/g, "\u0026quot;");

const escapeRegExp = (value: string): string =>
  value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// Sort by length so longer tool names match before shorter prefixes.
const toolNames = Object.keys(tools).sort((a, b) => b.length - a.length);
const toolPattern = new RegExp(
  `\\b(${toolNames.map(escapeRegExp).join("|")})\\b`,
  "g"
);

/**
 * Escapes plain text and turns known tool names into sponsored links.
 * Returns HTML that can be rendered with `set:html`.
 */
export function linkifyTools(text: string): string {
  return escapeHtml(text).replace(toolPattern, (match) => {
    const link = getToolLink(match);
    if (!link) return match;
    const rel = link.sponsored
      ? "noopener sponsored"
      : "noopener noreferrer";
    return `<a href="${link.href}" target="_blank" rel="${rel}" class="text-brand-300 underline decoration-brand-500/30 underline-offset-2 transition-colors hover:text-brand-200">${escapeHtml(link.name)}</a>`;
  });
}
