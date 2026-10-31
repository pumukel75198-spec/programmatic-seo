#!/usr/bin/env node
/**
 * sync-newsletter.mjs
 *
 * Überträgt im Newsletter-Worker zwischengespeicherte Anmeldungen
 * (KV-Präfix `sub:`) automatisch zu MailerLite. Wird von der
 * GitHub Action `newsletter.yaml` ausgeführt, sobald der API-Key existiert.
 *
 * Benötigt:
 *   CLOUDFLARE_API_TOKEN
 *   CLOUDFLARE_ACCOUNT_ID
 *   NEWSLETTER_KV_NAMESPACE_ID
 *   MAILERLITE_API_KEY
 *   MAILERLITE_GROUP_ID
 */

const CF_API = "https://api.cloudflare.com/client/v4";
const MAILERLITE_URL = "https://connect.mailerlite.com/api/subscribers";

const {
  CLOUDFLARE_API_TOKEN,
  CLOUDFLARE_ACCOUNT_ID,
  NEWSLETTER_KV_NAMESPACE_ID,
  MAILERLITE_API_KEY,
  MAILERLITE_GROUP_ID,
} = process.env;

function missing() {
  return [
    ["CLOUDFLARE_API_TOKEN", CLOUDFLARE_API_TOKEN],
    ["CLOUDFLARE_ACCOUNT_ID", CLOUDFLARE_ACCOUNT_ID],
    ["NEWSLETTER_KV_NAMESPACE_ID", NEWSLETTER_KV_NAMESPACE_ID],
    ["MAILERLITE_API_KEY", MAILERLITE_API_KEY],
    ["MAILERLITE_GROUP_ID", MAILERLITE_GROUP_ID],
  ]
    .filter(([, value]) => !value)
    .map(([name]) => name);
}

async function cf(path, options = {}) {
  const response = await fetch(`${CF_API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${CLOUDFLARE_API_TOKEN}`,
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });
  const data = await response.json();
  if (!response.ok || data.success === false) {
    throw new Error(`Cloudflare ${path} → ${response.status}: ${JSON.stringify(data.errors ?? data)}`);
  }
  return data;
}

async function listKeys() {
  const keys = [];
  let cursor = "";
  do {
    const query = new URLSearchParams({ prefix: "sub:", limit: "1000" });
    if (cursor) query.set("cursor", cursor);
    const data = await cf(
      `/accounts/${CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/${NEWSLETTER_KV_NAMESPACE_ID}/keys?${query}`
    );
    keys.push(...(data.result ?? []));
    cursor = data.result_info?.cursor ?? "";
  } while (cursor);
  return keys;
}

async function getValue(key) {
  const response = await fetch(
    `${CF_API}/accounts/${CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/${NEWSLETTER_KV_NAMESPACE_ID}/values/${encodeURIComponent(key)}`,
    { headers: { Authorization: `Bearer ${CLOUDFLARE_API_TOKEN}` } }
  );
  if (!response.ok) throw new Error(`KV get ${key} → ${response.status}`);
  return response.text();
}

async function deleteKey(key) {
  await cf(
    `/accounts/${CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/${NEWSLETTER_KV_NAMESPACE_ID}/values/${encodeURIComponent(key)}`,
    { method: "DELETE" }
  );
}

async function subscribe(email, source) {
  const response = await fetch(MAILERLITE_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${MAILERLITE_API_KEY}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      email,
      status: "pending",
      groups: [String(MAILERLITE_GROUP_ID)],
      fields: { source: source || "website" },
    }),
  });
  // 422 = existiert bereits – ebenfalls als Erfolg behandeln.
  return response.ok || response.status === 422;
}

async function main() {
  const absent = missing();
  if (absent.length > 0) {
    console.warn(`⚠ Sync übersprungen – fehlende Variablen: ${absent.join(", ")}`);
    return;
  }

  const keys = await listKeys();
  if (keys.length === 0) {
    console.log("✔ Keine wartenden Newsletter-Anmeldungen.");
    return;
  }

  let synced = 0;
  for (const { name } of keys) {
    try {
      const record = JSON.parse(await getValue(name));
      if (!record?.email) {
        await deleteKey(name);
        continue;
      }
      const ok = await subscribe(record.email, record.source);
      if (ok) {
        await deleteKey(name);
        synced += 1;
      }
    } catch (error) {
      console.warn(`⚠ ${name}: ${error.message}`);
    }
  }

  console.log(`✔ ${synced}/${keys.length} Anmeldungen zu MailerLite übertragen.`);
}

main().catch((error) => {
  console.error(`✖ ${error.message}`);
  process.exit(1);
});
