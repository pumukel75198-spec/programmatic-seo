import type { APIRoute } from "astro";
import { getAllInsights } from "../../lib/insights";
import { site } from "../../lib/site";

// Build XML entities from parts so the source is not mangled by
// HTML-entity decoding in editors/tooling.
const AMP = "&" + "amp;";
const LT = "&" + "lt;";
const GT = "&" + "gt;";
const QUOT = "&" + "quot;";
const APOS = "&" + "apos;";

const escapeXml = (value: string): string =>
  String(value ?? "")
    .replace(/&/g, AMP)
    .replace(/</g, LT)
    .replace(/>/g, GT)
    .replace(/"/g, QUOT)
    .replace(/'/g, APOS);

const absolute = (path: string): string => new URL(path, site.url).toString();

export const GET: APIRoute = () => {
  const insights = getAllInsights();
  const feedUrl = absolute("/insights/rss.xml");
  const siteUrl = absolute("/insights/");
  const lastBuildDate = insights.length
    ? new Date(insights[0].publishedAt).toUTCString()
    : new Date().toUTCString();

  const items = insights
    .map((insight) => {
      const url = absolute(`/insights/${insight.slug}/`);
      const pubDate = new Date(insight.publishedAt).toUTCString();
      return `    <item>
      <title>${escapeXml(insight.title)}</title>
      <link>${escapeXml(url)}</link>
      <guid isPermaLink="true">${escapeXml(url)}</guid>
      <pubDate>${pubDate}</pubDate>
      <category>${escapeXml(insight.category)}</category>
      <description>${escapeXml(insight.excerpt)}</description>
    </item>`;
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(site.name)} Insights</title>
    <link>${escapeXml(siteUrl)}</link>
    <description>${escapeXml(
      "Original analysis and practical takeaways on APIs, automation and modern software workflows."
    )}</description>
    <language>en</language>
    <lastBuildDate>${lastBuildDate}</lastBuildDate>
    <atom:link href="${escapeXml(feedUrl)}" rel="self" type="application/rss+xml" />
${items}
  </channel>
</rss>
`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
};
