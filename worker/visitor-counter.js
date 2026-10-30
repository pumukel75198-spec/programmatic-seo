/**
 * Cloudflare Worker: globaler Besucherzähler mit KV.
 *
 * Endpunkte:
 *   GET  /count  -> { count: number }   (nur lesen, 60s gecacht)
 *   POST /hit    -> { count: number }   (inkrementieren, rate-limited)
 *
 * KV-Binding: VISITOR_COUNTER
 * Keys:
 *   "total"        -> Gesamtzähler
 *   "rate:<hash>"  -> Rate-Limit-Marker (60s TTL)
 *
 * Datenschutz: Es werden keine IPs im Klartext gespeichert. Für das
 * Rate-Limit wird nur ein gesalzener SHA-256-Hash der IP mit 60s TTL
 * abgelegt. Es werden keine User-Agents oder Cookies gespeichert.
 */

const ALLOWED_ORIGINS = new Set([
  "https://flowmatrix.dev",
  "https://www.flowmatrix.dev",
  "http://localhost:4321",
  "http://localhost:3000",
]);

const BOT_PATTERN =
  /bot|crawler|spider|crawl|slurp|bingpreview|facebookexternalhit|headless|python-requests|curl|wget|scrapy|httpclient|go-http-client|java\/|okhttp|axios|node-fetch|monitor|uptime/i;

function corsHeaders(origin) {
  const allowed =
    origin && ALLOWED_ORIGINS.has(origin) ? origin : "https://flowmatrix.dev";
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(data, status, origin, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...corsHeaders(origin),
      ...extraHeaders,
    },
  });
}

async function hashIp(ip) {
  const data = new TextEncoder().encode(`${ip}|flowmatrix-visitor-counter`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 32);
}

async function readTotal(env) {
  const raw = await env.VISITOR_COUNTER.get("total");
  return Number(raw) || 0;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (url.pathname === "/count" && request.method === "GET") {
      const count = await readTotal(env);
      return json({ count }, 200, origin, {
        "Cache-Control": "public, max-age=60",
      });
    }

    if (url.pathname === "/hit" && request.method === "POST") {
      // 1) Bot-Filter: bekannte Bots/Crawler nicht zählen.
      const userAgent = request.headers.get("User-Agent") || "";
      if (!userAgent || BOT_PATTERN.test(userAgent)) {
        return json({ count: await readTotal(env), skipped: "bot" }, 200, origin);
      }

      // 2) Rate-Limit: max. 1 Hit pro IP und Minute (gehashter Schlüssel).
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const rateKey = `rate:${await hashIp(ip)}`;
      const recent = await env.VISITOR_COUNTER.get(rateKey);
      if (recent) {
        return json(
          { count: await readTotal(env), skipped: "rate" },
          200,
          origin
        );
      }
      await env.VISITOR_COUNTER.put(rateKey, "1", { expirationTtl: 60 });

      // 3) Inkrementieren.
      const next = (await readTotal(env)) + 1;
      await env.VISITOR_COUNTER.put("total", String(next));
      return json({ count: next }, 200, origin);
    }

    return json({ error: "Not found" }, 404, origin);
  },
};
