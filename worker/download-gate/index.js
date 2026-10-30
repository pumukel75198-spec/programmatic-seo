/**
 * Cloudflare Worker: geschütztes Download-Gate für Premium-PDFs.
 *
 * Problem vorher: Die PDFs lagen unter `public/downloads/` und waren ohne Kauf
 * abrufbar; der "Unlock" im Frontend war nur localStorage/`?purchased=1` und
 * damit trivial fälschbar.
 *
 * Lösung:
 *   1. PDFs liegen NICHT mehr im öffentlichen Build, sondern in einem
 *      privaten R2-Bucket (`DOWNLOADS`).
 *   2. Der Käufer erhält von Lemon Squeezy einen Lizenzschlüssel.
 *   3. `POST /api/validate` prüft den Schlüssel gegen die offizielle
 *      Lemon-Squeezy-License-API und gibt bei Gültigkeit ein kurzlebiges,
 *      HMAC-signiertes Token zurück.
 *   4. `GET /api/download?token=…&slug=…` prüft das Token und streamt das PDF
 *      aus R2. Ohne gültiges Token gibt es keinen Zugriff.
 *
 * Benötigte Bindings / Variablen (siehe wrangler.toml + README.md):
 *   - R2-Binding: DOWNLOADS
 *   - Secret:     DOWNLOAD_TOKEN_SECRET   (zufälliger, langer String)
 *   - Secret:     LEMON_PRODUCT_MAP       (JSON, siehe README)
 *   - Var:        ALLOW_ALL_ON_VALID      ("1" nur für Testphase)
 */

const ALLOWED_ORIGINS = new Set([
  "https://flowmatrix.dev",
  "https://www.flowmatrix.dev",
  "http://localhost:4321",
  "http://localhost:3000",
]);

const LEMON_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate";

/** Gültigkeitsdauer eines Download-Tokens in Sekunden. */
const TOKEN_TTL_SECONDS = 600;

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

/* -------------------------------------------------------------------------- */
/* Base64url + HMAC                                                           */
/* -------------------------------------------------------------------------- */

function bytesToBase64Url(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (const byte of view) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function base64UrlEncode(value) {
  return bytesToBase64Url(new TextEncoder().encode(value));
}

function base64UrlDecode(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

async function hmacSign(secret, data) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(data)
  );
  return bytesToBase64Url(signature);
}

async function sha256Hex(value) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value)
  );
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

/** Konstantzeit-Vergleich, um Timing-Angriffe zu vermeiden. */
function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

/* -------------------------------------------------------------------------- */
/* Produkt-Mapping                                                            */
/* -------------------------------------------------------------------------- */

function parseProductMap(env) {
  try {
    const parsed = JSON.parse(env.LEMON_PRODUCT_MAP || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

/**
 * Ordnet eine Lemon-Squeezy-Lizenz einem Produkt zu.
 *
 * Map-Format (LEMON_PRODUCT_MAP):
 * {
 *   "variant:123456": { "type": "single", "slugs": ["content-automation"] },
 *   "product:789012": { "type": "bundle", "slugs": ["*"] },
 *   "product:345678": { "type": "subscription", "slugs": ["*"] }
 * }
 *
 * `slugs: ["*"]` erlaubt alle PDFs (Bundle/Abo). Ein einzelnes Produkt darf
 * nur die explizit gelisteten Slugs herunterladen.
 */
function resolveProduct(env, meta) {
  const map = parseProductMap(env);
  const variantKey = `variant:${meta?.variant_id}`;
  const productKey = `product:${meta?.product_id}`;

  if (map[variantKey]) {
    return { key: variantKey, ...map[variantKey] };
  }
  if (map[productKey]) {
    return { key: productKey, ...map[productKey] };
  }

  // Nur für die Testphase, solange noch keine echten Produkt-IDs bekannt sind.
  if (env.ALLOW_ALL_ON_VALID === "1") {
    return { key: "all", type: "all", slugs: ["*"] };
  }

  return null;
}

/* -------------------------------------------------------------------------- */
/* Lemon Squeezy                                                              */
/* -------------------------------------------------------------------------- */

async function validateLicense(licenseKey) {
  const response = await fetch(LEMON_VALIDATE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: new URLSearchParams({ license_key: licenseKey }).toString(),
  });

  if (!response.ok) {
    return { ok: false, httpStatus: response.status };
  }

  const data = await response.json();
  const status = data?.license_key?.status;
  const valid = data?.valid === true && status === "active";

  return { ok: valid, data, status };
}

/* -------------------------------------------------------------------------- */
/* Token                                                                      */
/* -------------------------------------------------------------------------- */

async function createToken(env, { licenseKey, product }) {
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    h: await sha256Hex(licenseKey),
    p: product.key,
    s: product.slugs,
    exp: now + TOKEN_TTL_SECONDS,
  };
  const encoded = base64UrlEncode(JSON.stringify(payload));
  const signature = await hmacSign(env.DOWNLOAD_TOKEN_SECRET, encoded);
  return {
    token: `${encoded}.${signature}`,
    expiresAt: new Date(payload.exp * 1000).toISOString(),
  };
}

async function verifyToken(env, token) {
  if (!token || typeof token !== "string") return null;
  const [encoded, signature] = token.split(".");
  if (!encoded || !signature) return null;

  const expected = await hmacSign(env.DOWNLOAD_TOKEN_SECRET, encoded);
  if (!timingSafeEqual(signature, expected)) return null;

  let payload;
  try {
    payload = JSON.parse(base64UrlDecode(encoded));
  } catch {
    return null;
  }

  if (!payload?.exp || payload.exp < Math.floor(Date.now() / 1000)) {
    return null;
  }
  return payload;
}

function isSlugAllowed(payload, slug) {
  if (!payload || !slug) return false;
  if (payload.s === "*") return true;
  return Array.isArray(payload.s) && payload.s.includes(slug);
}

/* -------------------------------------------------------------------------- */
/* Handler                                                                    */
/* -------------------------------------------------------------------------- */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (url.pathname === "/api/health" && request.method === "GET") {
      return json({ ok: true }, 200, origin);
    }

    /* --- Lizenz validieren ------------------------------------------------- */
    if (url.pathname === "/api/validate" && request.method === "POST") {
      if (!env.DOWNLOAD_TOKEN_SECRET) {
        return json(
          { valid: false, error: "Server nicht konfiguriert (Token-Secret fehlt)." },
          500,
          origin
        );
      }

      let body;
      try {
        body = await request.json();
      } catch {
        return json({ valid: false, error: "Ungültiger Request-Body." }, 400, origin);
      }

      const licenseKey = String(body?.licenseKey ?? "").trim();
      const slug = String(body?.slug ?? "").trim();

      if (!licenseKey) {
        return json(
          { valid: false, error: "Bitte einen Lizenzschlüssel eingeben." },
          400,
          origin
        );
      }

      const result = await validateLicense(licenseKey);
      if (!result.ok) {
        return json(
          {
            valid: false,
            error:
              result.httpStatus === 404
                ? "Lizenzschlüssel nicht gefunden."
                : "Lizenzschlüssel ist ungültig oder nicht aktiv.",
          },
          200,
          origin
        );
      }

      const meta = result.data?.meta ?? {};
      const product = resolveProduct(env, meta);
      if (!product) {
        return json(
          {
            valid: false,
            error:
              "Diese Lizenz ist keinem PDF-Produkt zugeordnet. Bitte Support kontaktieren.",
          },
          200,
          origin
        );
      }

      if (slug && !isSlugAllowed({ s: product.slugs }, slug)) {
        return json(
          {
            valid: false,
            error: "Diese Lizenz gilt nicht für dieses PDF.",
          },
          200,
          origin
        );
      }

      const { token, expiresAt } = await createToken(env, {
        licenseKey,
        product,
      });

      const downloadUrl = slug
        ? `${url.origin}/api/download?token=${encodeURIComponent(token)}&slug=${encodeURIComponent(slug)}`
        : null;

      return json(
        {
          valid: true,
          product: { type: product.type, slugs: product.slugs },
          token,
          expiresAt,
          downloadUrl,
        },
        200,
        origin
      );
    }

    /* --- Python-Skript ausliefern ----------------------------------------- */
    if (url.pathname === "/api/script" && request.method === "GET") {
      if (!env.DOWNLOAD_TOKEN_SECRET) {
        return json({ error: "Server nicht konfiguriert." }, 500, origin);
      }

      const token = url.searchParams.get("token");
      const slug = String(url.searchParams.get("slug") ?? "").trim();
      const file = String(url.searchParams.get("file") ?? "py").trim();

      if (!slug || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
        return json({ error: "Ungültiger Slug." }, 400, origin);
      }

      const allowedFiles = {
        py: { key: "py", name: `${slug}.py`, type: "text/x-python" },
        readme: { key: "readme", name: "README.md", type: "text/markdown" },
        metadata: {
          key: "metadata",
          name: "metadata.json",
          type: "application/json",
        },
      };
      const target = allowedFiles[file];
      if (!target) {
        return json({ error: "Ungültiger Dateityp." }, 400, origin);
      }

      const payload = await verifyToken(env, token);
      if (!payload) {
        return json(
          { error: "Download-Token ist ungültig oder abgelaufen." },
          401,
          origin
        );
      }

      if (!isSlugAllowed(payload, slug)) {
        return json(
          { error: "Diese Lizenz gilt nicht für dieses Skript." },
          403,
          origin
        );
      }

      const object = await env.PDF_STORE.get(`script:${slug}:${target.key}`, {
        type: "arrayBuffer",
      });
      if (!object) {
        return json({ error: "Skript nicht gefunden." }, 404, origin);
      }

      return new Response(object, {
        status: 200,
        headers: {
          "Content-Type": target.type,
          "Content-Disposition": `attachment; filename="${target.name}"`,
          "Content-Length": String(object.byteLength ?? ""),
          "Cache-Control": "private, no-store",
          ...corsHeaders(origin),
        },
      });
    }

    /* --- PDF ausliefern ---------------------------------------------------- */
    if (url.pathname === "/api/download" && request.method === "GET") {
      if (!env.DOWNLOAD_TOKEN_SECRET) {
        return json({ error: "Server nicht konfiguriert." }, 500, origin);
      }

      const token = url.searchParams.get("token");
      const slug = String(url.searchParams.get("slug") ?? "").trim();

      if (!slug || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
        return json({ error: "Ungültiger Slug." }, 400, origin);
      }

      const payload = await verifyToken(env, token);
      if (!payload) {
        return json(
          { error: "Download-Token ist ungültig oder abgelaufen." },
          401,
          origin
        );
      }

      if (!isSlugAllowed(payload, slug)) {
        return json(
          { error: "Diese Lizenz gilt nicht für dieses PDF." },
          403,
          origin
        );
      }

      const object = await env.PDF_STORE.get(`${slug}.pdf`, {
        type: "arrayBuffer",
      });
      if (!object) {
        return json({ error: "PDF nicht gefunden." }, 404, origin);
      }

      return new Response(object, {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": `attachment; filename="flowmatrix-${slug}.pdf"`,
          "Content-Length": String(object.byteLength ?? ""),
          "Cache-Control": "private, no-store",
          ...corsHeaders(origin),
        },
      });
    }

    return json({ error: "Not found" }, 404, origin);
  },
};
