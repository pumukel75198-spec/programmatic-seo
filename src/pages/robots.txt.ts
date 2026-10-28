import type { APIRoute } from "astro";
import { site } from "../lib/site";

export const GET: APIRoute = ({ site: astroSite }) => {
  const base = astroSite ?? new URL(site.url);
  const sitemapUrl = new URL("sitemap-index.xml", base).toString();

  const body = [
    "User-agent: *",
    "Allow: /",
    "",
    `Sitemap: ${sitemapUrl}`,
    "",
  ].join("\n");

  return new Response(body, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
};
