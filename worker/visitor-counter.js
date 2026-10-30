/**
 * Cloudflare Worker: globaler Besucherzähler mit KV.
 *
 * Endpunkte:
 *   GET  /count  -> { count: number }   (nur lesen)
 *   POST /hit    -> { count: number }   (inkrementieren)
 *
 * KV-Binding: VISITOR_COUNTER
 * Key: "total"
 *
 * Hinweis: KV ist eventually consistent. Für einen einfachen,
 * DSGVO-freundlichen Zähler ohne personenbezogene Daten ist das
 * ausreichend. Es werden keine IPs oder User-Agents gespeichert.
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (url.pathname === "/count" && request.method === "GET") {
      const raw = await env.VISITOR_COUNTER.get("total");
      return json({ count: Number(raw) || 0 });
    }

    if (url.pathname === "/hit" && request.method === "POST") {
      const raw = await env.VISITOR_COUNTER.get("total");
      const next = (Number(raw) || 0) + 1;
      await env.VISITOR_COUNTER.put("total", String(next));
      return json({ count: next });
    }

    return json({ error: "Not found" }, 404);
  },
};
