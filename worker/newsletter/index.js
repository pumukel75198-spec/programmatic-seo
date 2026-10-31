/**
 * Cloudflare Worker: vollautomatische Newsletter-Anmeldung.
 *
 * Ablauf:
 *   1. Frontend postet `{ email, source, consent, website }` an `POST /subscribe`.
 *   2. Der Worker validiert E-Mail + Consent, filtert Bots (Honeypot) und
 *      begrenzt Missbrauch pro IP über KV.
 *   3. Ist `MAILERLITE_API_KEY` gesetzt, wird der Kontakt mit Status
 *      `pending` in die konfigurierte MailerLite-Gruppe geschrieben.
 *      MailerLite versendet dann automatisch die Double-Opt-in-Mail und
 *      später die automatisierten Newsletter – ohne manuellen Eingriff.
 *   4. Ist MailerLite (noch) nicht konfiguriert, wird die Anmeldung
 *      verlustfrei in KV gespeichert. `scripts/sync-newsletter.mjs`
 *      überträgt sie später automatisch, sobald der API-Key existiert.
 *
 * Bindings / Variablen (siehe wrangler.toml + README.md):
 *   - KV-Binding: NEWSLETTER_KV
 *   - Secret:     MAILERLITE_API_KEY   (optional, aber empfohlen)
 *   - Var:        MAILERLITE_GROUP_ID  (optional)
 *   - Var:        ALLOWED_ORIGINS      (kommagetrennt, optional)
 */

const DEFAULT_ORIGINS = [
  "https://flowmatrix.dev",
  "https://www.flowmatrix.dev",
  "https://compliance.flowmatrix.dev",
  "http://localhost:4321",
  "http://localhost:3000",
];

const MAILERLITE_SUBSCRIBERS_URL = "https://connect.mailerlite.com/api/subscribers";

/** Maximale Anmeldungen pro IP und Stunde. */
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW_SECONDS = 60 * 60;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function allowedOrigins(env) {
  const configured = (env.ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  return new Set(configured.length > 0 ? configured : DEFAULT_ORIGINS);
}

function corsHeaders(origin, env) {
  const allowed = allowedOrigins(env);
  const value = origin && allowed.has(origin) ? origin : "https://flowmatrix.dev";
  return {
    "Access-Control-Allow-Origin": value,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(data, status, origin, env, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...corsHeaders(origin, env),
      ...extraHeaders,
    },
  });
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

function normalizeEmail(value) {
  return String(value ?? "").trim().toLowerCase();
}

function isValidEmail(email) {
  return email.length <= 254 && EMAIL_RE.test(email);
}

/** Einfaches, KV-basiertes Rate-Limit pro IP-Hash. */
async function isRateLimited(env, ipHash) {
  if (!env.NEWSLETTER_KV) return false;
  const key = `rate:${ipHash}`;
  const current = Number((await env.NEWSLETTER_KV.get(key)) ?? "0");
  if (current >= RATE_LIMIT_MAX) return true;
  await env.NEWSLETTER_KV.put(key, String(current + 1), {
    expirationTtl: RATE_LIMIT_WINDOW_SECONDS,
  });
  return false;
}

/** Schreibt den Kontakt in MailerLite (Double-Opt-in via `pending`). */
async function subscribeToMailerLite(env, email, source) {
  const apiKey = env.MAILERLITE_API_KEY;
  if (!apiKey) return { configured: false, ok: false };

  const body = {
    email,
    status: "pending",
    fields: {
      source: source || "website",
    },
  };
  if (env.MAILERLITE_GROUP_ID) {
    body.groups = [String(env.MAILERLITE_GROUP_ID)];
  }

  const response = await fetch(MAILERLITE_SUBSCRIBERS_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });

  if (response.ok) return { configured: true, ok: true };

  // 422 = Kontakt existiert bereits. Das ist für den Nutzer kein Fehler.
  if (response.status === 422) return { configured: true, ok: true };

  const detail = await response.text().catch(() => "");
  console.error("MailerLite subscribe failed", response.status, detail);
  return { configured: true, ok: false, status: response.status };
}

/** Speichert die Anmeldung dauerhaft in KV (Fallback + Audit). */
async function storePending(env, email, source, ipHash) {
  if (!env.NEWSLETTER_KV) return;
  const emailHash = await sha256Hex(email);
  const record = {
    email,
    source: source || "website",
    status: "pending",
    createdAt: new Date().toISOString(),
    ipHash,
  };
  await env.NEWSLETTER_KV.put(`sub:${emailHash}`, JSON.stringify(record));
}

async function handleSubscribe(request, env, origin) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ ok: false, error: "invalid_json" }, 400, origin, env);
  }

  // Honeypot: Bots füllen das unsichtbare Feld aus. Wir antworten bewusst
  // mit Erfolg, speichern aber nichts.
  if (payload.website) {
    return json({ ok: true, status: "pending" }, 200, origin, env);
  }

  const email = normalizeEmail(payload.email);
  const source = String(payload.source ?? "website").slice(0, 64);
  const consent = payload.consent === true || payload.consent === "true";

  if (!isValidEmail(email)) {
    return json({ ok: false, error: "invalid_email" }, 400, origin, env);
  }
  if (!consent) {
    return json({ ok: false, error: "consent_required" }, 400, origin, env);
  }

  const ip =
    request.headers.get("CF-Connecting-IP") ??
    request.headers.get("X-Forwarded-For") ??
    "unknown";
  const ipHash = await sha256Hex(ip);

  if (await isRateLimited(env, ipHash)) {
    return json({ ok: false, error: "rate_limited" }, 429, origin, env);
  }

  const mailer = await subscribeToMailerLite(env, email, source);
  await storePending(env, email, source, ipHash);

  if (mailer.configured && !mailer.ok) {
    return json({ ok: false, error: "provider_error" }, 502, origin, env);
  }

  return json(
    {
      ok: true,
      status: "pending",
      // `queued` bedeutet: MailerLite ist noch nicht verbunden, die Adresse
      // ist aber sicher gespeichert und wird automatisch nachgezogen.
      queued: !mailer.configured,
    },
    200,
    origin,
    env
  );
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") ?? "";
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(origin, env),
      });
    }

    if (url.pathname === "/health") {
      return json(
        {
          ok: true,
          mailerLite: Boolean(env.MAILERLITE_API_KEY),
          kv: Boolean(env.NEWSLETTER_KV),
        },
        200,
        origin,
        env
      );
    }

    if (url.pathname === "/subscribe" && request.method === "POST") {
      return handleSubscribe(request, env, origin);
    }

    return json({ ok: false, error: "not_found" }, 404, origin, env);
  },
};
