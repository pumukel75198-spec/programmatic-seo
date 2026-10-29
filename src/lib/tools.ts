import partnerData from "../data/partner.json";

/**
 * Central tool & affiliate link configuration.
 *
 * Tools mentioned across API and workflow records are mapped to their
 * official URLs and optional affiliate URLs. Templates use these helpers
 * to render tools as clean, sponsored links.
 *
 * Affiliate parameters are applied centrally in `getToolLink()`:
 *   - global default: `PUBLIC_AFFILIATE_REF` (fallback: "flowmatrix")
 *   - per-tool override: `affiliateParams`
 *
 * This keeps partner IDs in one place and avoids hard-coding query strings
 * in every tool entry.
 */
export interface ToolConfig {
  name: string;
  url: string;
  affiliateUrl?: string;
  /** Per-tool affiliate parameters, e.g. { ref: "partner-123" }. */
  affiliateParams?: Record<string, string>;
  sponsored?: boolean;
}

/**
 * Legacy placeholder kept so existing entries stay readable. The actual
 * affiliate parameters are appended by `getToolLink()`.
 */
const REF = "";

/** Global affiliate reference, configurable via environment. */
export const AFFILIATE_REF =
  import.meta.env?.PUBLIC_AFFILIATE_REF?.trim() || "flowmatrix";

export const DEFAULT_AFFILIATE_PARAMS: Record<string, string> = {
  ref: AFFILIATE_REF,
};

/**
 * Appends affiliate parameters to a URL without duplicating existing keys
 * and without breaking existing query strings or hash fragments.
 */
export function withAffiliateParams(
  url: string,
  params: Record<string, string> = DEFAULT_AFFILIATE_PARAMS
): string {
  try {
    const parsed = new URL(url);
    for (const [key, value] of Object.entries(params)) {
      if (!value) continue;
      parsed.searchParams.set(key, value);
    }
    return parsed.toString();
  } catch {
    return url;
  }
}

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
  Obsidian: {
    name: "Obsidian",
    url: "https://obsidian.md/",
    affiliateUrl: `https://obsidian.md/${REF}`,
    sponsored: true,
  },
  Coda: {
    name: "Coda",
    url: "https://coda.io/",
  },
  AppFlowy: {
    name: "AppFlowy",
    url: "https://appflowy.io/",
  },
  Pipedream: {
    name: "Pipedream",
    url: "https://pipedream.com/",
  },
  Penpot: {
    name: "Penpot",
    url: "https://penpot.app/",
    affiliateUrl: `https://penpot.app/${REF}`,
    sponsored: true,
  },
  Sketch: {
    name: "Sketch",
    url: "https://www.sketch.com/",
  },
  Framer: {
    name: "Framer",
    url: "https://www.framer.com/",
  },
  Mattermost: {
    name: "Mattermost",
    url: "https://mattermost.com/",
    affiliateUrl: `https://mattermost.com/${REF}`,
    sponsored: true,
  },
  "Rocket.Chat": {
    name: "Rocket.Chat",
    url: "https://rocket.chat/",
  },
  Discord: {
    name: "Discord",
    url: "https://discord.com/",
  },
  Baserow: {
    name: "Baserow",
    url: "https://baserow.io/",
    affiliateUrl: `https://baserow.io/${REF}`,
    sponsored: true,
  },
  NocoDB: {
    name: "NocoDB",
    url: "https://nocodb.com/",
  },
  SeaTable: {
    name: "SeaTable",
    url: "https://seatable.io/",
  },
  Brevo: {
    name: "Brevo",
    url: "https://www.brevo.com/",
  },
  MailerLite: {
    name: "MailerLite",
    url: "https://www.mailerlite.com/",
  },
  Buttondown: {
    name: "Buttondown",
    url: "https://buttondown.email/",
  },
  Plane: {
    name: "Plane",
    url: "https://plane.so/",
  },
  Vikunja: {
    name: "Vikunja",
    url: "https://vikunja.io/",
  },
  Linear: {
    name: "Linear",
    url: "https://linear.app/",
  },
  Plausible: {
    name: "Plausible",
    url: "https://plausible.io/",
  },
  Umami: {
    name: "Umami",
    url: "https://umami.is/",
  },
  Matomo: {
    name: "Matomo",
    url: "https://matomo.org/",
  },
  Pipedrive: {
    name: "Pipedrive",
    url: "https://www.pipedrive.com/",
  },
  Odoo: {
    name: "Odoo",
    url: "https://www.odoo.com/",
  },
  Excalidraw: {
    name: "Excalidraw",
    url: "https://excalidraw.com/",
  },
  tldraw: {
    name: "tldraw",
    url: "https://tldraw.dev/",
  },
  Cap: {
    name: "Cap",
    url: "https://cap.so/",
  },
  "OBS Studio": {
    name: "OBS Studio",
    url: "https://obsproject.com/",
  },
  "Screen Studio": {
    name: "Screen Studio",
    url: "https://www.screen.studio/",
  },
  Crisp: {
    name: "Crisp",
    url: "https://crisp.chat/",
  },
  Chatwoot: {
    name: "Chatwoot",
    url: "https://www.chatwoot.com/",
  },
  Freshdesk: {
    name: "Freshdesk",
    url: "https://freshdesk.com/",
  },
  Zammad: {
    name: "Zammad",
    url: "https://zammad.com/",
  },
  YouTrack: {
    name: "YouTrack",
    url: "https://www.jetbrains.com/youtrack/",
  },
  Gitea: {
    name: "Gitea",
    url: "https://gitea.com/",
  },
  Forgejo: {
    name: "Forgejo",
    url: "https://forgejo.org/",
  },
  Render: {
    name: "Render",
    url: "https://render.com/",
  },
  Coolify: {
    name: "Coolify",
    url: "https://coolify.io/",
  },
  WooCommerce: {
    name: "WooCommerce",
    url: "https://woocommerce.com/",
  },
  Medusa: {
    name: "Medusa",
    url: "https://medusajs.com/",
  },
  BigCommerce: {
    name: "BigCommerce",
    url: "https://www.bigcommerce.com/",
  },
  Nextcloud: {
    name: "Nextcloud",
    url: "https://nextcloud.com/",
  },
  "Proton Drive": {
    name: "Proton Drive",
    url: "https://proton.me/drive",
  },
  pCloud: {
    name: "pCloud",
    url: "https://www.pcloud.com/",
  },
  Zcal: {
    name: "Zcal",
    url: "https://zcal.co/",
  },
  Rallly: {
    name: "Rallly",
    url: "https://rallly.co/",
  },
  Ghost: {
    name: "Ghost",
    url: "https://ghost.org/",
  },
  Hugo: {
    name: "Hugo",
    url: "https://gohugo.io/",
  },
  OpenAI: {
    name: "OpenAI",
    url: "https://openai.com/",
    affiliateUrl: `https://openai.com/${REF}`,
    sponsored: true,
  },
  Stripe: {
    name: "Stripe",
    url: "https://stripe.com/",
    affiliateUrl: `https://stripe.com/${REF}`,
    sponsored: true,
  },
  Anthropic: {
    name: "Anthropic",
    url: "https://www.anthropic.com/",
    affiliateUrl: `https://www.anthropic.com/${REF}`,
    sponsored: true,
  },
  Google: {
    name: "Google",
    url: "https://ai.google.dev/",
  },
  Resend: {
    name: "Resend",
    url: "https://resend.com/",
    affiliateUrl: `https://resend.com/${REF}`,
    sponsored: true,
  },
  Clerk: {
    name: "Clerk",
    url: "https://clerk.com/",
    affiliateUrl: `https://clerk.com/${REF}`,
    sponsored: true,
  },
  Cloudflare: {
    name: "Cloudflare",
    url: "https://www.cloudflare.com/",
    affiliateUrl: `https://www.cloudflare.com/${REF}`,
    sponsored: true,
  },
  Mapbox: {
    name: "Mapbox",
    url: "https://www.mapbox.com/",
    affiliateUrl: `https://www.mapbox.com/${REF}`,
    sponsored: true,
  },
  Twilio: {
    name: "Twilio",
    url: "https://www.twilio.com/",
    affiliateUrl: `https://www.twilio.com/${REF}`,
    sponsored: true,
  },
  "Hugging Face": {
    name: "Hugging Face",
    url: "https://huggingface.co/",
    affiliateUrl: `https://huggingface.co/${REF}`,
    sponsored: true,
  },
  Cohere: {
    name: "Cohere",
    url: "https://cohere.com/",
    affiliateUrl: `https://cohere.com/${REF}`,
    sponsored: true,
  },
  Pinecone: {
    name: "Pinecone",
    url: "https://www.pinecone.io/",
    affiliateUrl: `https://www.pinecone.io/${REF}`,
    sponsored: true,
  },
  Auth0: {
    name: "Auth0",
    url: "https://auth0.com/",
    affiliateUrl: `https://auth0.com/${REF}`,
    sponsored: true,
  },
  "Twilio SendGrid": {
    name: "Twilio SendGrid",
    url: "https://sendgrid.com/",
    affiliateUrl: `https://sendgrid.com/${REF}`,
    sponsored: true,
  },
  Algolia: {
    name: "Algolia",
    url: "https://www.algolia.com/",
    affiliateUrl: `https://www.algolia.com/${REF}`,
    sponsored: true,
  },
  OpenWeather: {
    name: "OpenWeather",
    url: "https://openweathermap.org/",
  },
  "Mistral AI": {
    name: "Mistral AI",
    url: "https://mistral.ai/",
    affiliateUrl: `https://mistral.ai/${REF}`,
    sponsored: true,
  },
  Groq: {
    name: "Groq",
    url: "https://groq.com/",
    affiliateUrl: `https://groq.com/${REF}`,
    sponsored: true,
  },
  "Together AI": {
    name: "Together AI",
    url: "https://www.together.ai/",
    affiliateUrl: `https://www.together.ai/${REF}`,
    sponsored: true,
  },
  Replicate: {
    name: "Replicate",
    url: "https://replicate.com/",
    affiliateUrl: `https://replicate.com/${REF}`,
    sponsored: true,
  },
  ElevenLabs: {
    name: "ElevenLabs",
    url: "https://elevenlabs.io/",
    affiliateUrl: `https://elevenlabs.io/${REF}`,
    sponsored: true,
  },
  Deepgram: {
    name: "Deepgram",
    url: "https://deepgram.com/",
    affiliateUrl: `https://deepgram.com/${REF}`,
    sponsored: true,
  },
  "Stability AI": {
    name: "Stability AI",
    url: "https://stability.ai/",
    affiliateUrl: `https://stability.ai/${REF}`,
    sponsored: true,
  },
  Weaviate: {
    name: "Weaviate",
    url: "https://weaviate.io/",
    affiliateUrl: `https://weaviate.io/${REF}`,
    sponsored: true,
  },
  Qdrant: {
    name: "Qdrant",
    url: "https://qdrant.tech/",
    affiliateUrl: `https://qdrant.tech/${REF}`,
    sponsored: true,
  },
  MongoDB: {
    name: "MongoDB",
    url: "https://www.mongodb.com/",
    affiliateUrl: `https://www.mongodb.com/${REF}`,
    sponsored: true,
  },
  PlanetScale: {
    name: "PlanetScale",
    url: "https://planetscale.com/",
    affiliateUrl: `https://planetscale.com/${REF}`,
    sponsored: true,
  },
  Upstash: {
    name: "Upstash",
    url: "https://upstash.com/",
    affiliateUrl: `https://upstash.com/${REF}`,
    sponsored: true,
  },
  Liveblocks: {
    name: "Liveblocks",
    url: "https://liveblocks.io/",
    affiliateUrl: `https://liveblocks.io/${REF}`,
    sponsored: true,
  },
  Ably: {
    name: "Ably",
    url: "https://ably.com/",
    affiliateUrl: `https://ably.com/${REF}`,
    sponsored: true,
  },
  PostHog: {
    name: "PostHog",
    url: "https://posthog.com/",
    affiliateUrl: `https://posthog.com/${REF}`,
    sponsored: true,
  },
  Sentry: {
    name: "Sentry",
    url: "https://sentry.io/",
    affiliateUrl: `https://sentry.io/${REF}`,
    sponsored: true,
  },
  LaunchDarkly: {
    name: "LaunchDarkly",
    url: "https://launchdarkly.com/",
    affiliateUrl: `https://launchdarkly.com/${REF}`,
    sponsored: true,
  },
  Doppler: {
    name: "Doppler",
    url: "https://www.doppler.com/",
    affiliateUrl: `https://www.doppler.com/${REF}`,
    sponsored: true,
  },
};

/**
 * Merge central partner overrides from `src/data/partner.json`.
 * This keeps affiliate URLs/IDs in one place while preserving the
 * existing tool catalogue as a fallback.
 */
const partnerOverrides = partnerData as Record<string, Partial<ToolConfig>>;
for (const [name, override] of Object.entries(partnerOverrides)) {
  const existing = tools[name];
  const merged: ToolConfig = {
    ...(existing ?? { name, url: "" }),
    ...override,
    name,
    url: override.url ?? existing?.url ?? "",
  };
  tools[name] = merged;
}

export interface ToolLink {
  name: string;
  href: string;
  sponsored: boolean;
}

export function getToolLink(name: string): ToolLink | null {
  const tool = tools[name];
  if (!tool) return null;

  const baseUrl = tool.affiliateUrl ?? tool.url;
  const params = tool.affiliateParams ?? DEFAULT_AFFILIATE_PARAMS;
  const sponsored = tool.sponsored ?? Boolean(tool.affiliateUrl);

  return {
    name: tool.name,
    href: sponsored ? withAffiliateParams(baseUrl, params) : baseUrl,
    sponsored,
  };
}

/** Returns the affiliate URL for a tool, or its official URL as fallback. */
export function getAffiliateUrl(name: string): string | null {
  return getToolLink(name)?.href ?? null;
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
