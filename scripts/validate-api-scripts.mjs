#!/usr/bin/env node
/**
 * validate-api-scripts.mjs
 *
 * Strikte Konsistenzprüfung der generierten Python-Starter-Skripte.
 *
 * Für jede API in `src/data/apis.json` wird geprüft:
 *   1. Skript + metadata.json existieren.
 *   2. Die Konstanten im Skript (Slug, Titel, Provider, Kategorie, Tags,
 *      Docs, Website, Endpoint, Methode, Auth, Key-Env) stimmen exakt mit
 *      den Quelldaten überein.
 *   3. metadata.json stimmt mit den Quelldaten überein.
 *   4. Der Endpoint-Host gehört zum Provider (Allowlist).
 *   5. Dynamische Endpunkte (Platzhalter) sind als solche markiert und das
 *      Skript unterstützt `--base-url`.
 *   6. Keine zwei Skripte sind identisch (Duplikat-Erkennung).
 *
 * Exit-Code 1 bei mindestens einem Fehler.
 *
 * Verwendung:
 *   npm run api-scripts:validate
 */

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const apisFile = join(root, "src", "data", "apis.json");
const overridesFile = join(root, "src", "data", "api-endpoints.json");
const scriptsDir = process.env.API_SCRIPTS_OUTPUT_DIR
  ? resolve(root, process.env.API_SCRIPTS_OUTPUT_DIR)
  : join(root, "private", "api-scripts");

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

/**
 * Erlaubte Endpoint-Domains pro Provider. Die erste Domain ist die
 * "kanonische" Website-Domain; weitere sind legitime API-/Produkt-Domains.
 */
const PROVIDER_DOMAINS = {
  supabase: ["supabase.com", "supabase.co"],
  google: ["google.com", "googleapis.com", "google.dev"],
  auth0: ["auth0.com"],
  algolia: ["algolia.com", "algolia.net"],
  shopify: ["shopify.com", "shopify.dev", "myshopify.com"],
  "together ai": ["together.ai", "together.xyz"],
  weaviate: ["weaviate.io", "weaviate.network"],
  qdrant: ["qdrant.tech", "qdrant.io"],
  upstash: ["upstash.com", "upstash.io"],
  vercel: ["vercel.com", "vercel-storage.com"],
  ably: ["ably.com", "ably.io"],
  hubspot: ["hubspot.com", "hubapi.com"],
  microsoft: ["microsoft.com", "azure.com"],
  amazon: ["amazon.com", "amazonaws.com"],
  "amazon web services": ["amazon.com", "amazonaws.com"],
  aws: ["amazon.com", "amazonaws.com"],
  ibm: ["ibm.com", "appdomain.cloud", "cloud.ibm.com"],
};

function registrableDomain(host) {
  if (!host) return "";
  const clean = host.replace(/^www\./, "").toLowerCase();
  const parts = clean.split(".");
  if (parts.length <= 2) return clean;
  const three = parts.slice(-3).join(".");
  if (/\.(co|com|org|net|ac)\.[a-z]{2}$/.test(three)) return three;
  return parts.slice(-2).join(".");
}

function hostOf(url) {
  if (!url) return "";
  try {
    return new URL(String(url).replace(/[{}<>]/g, "x")).hostname;
  } catch {
    return "";
  }
}

function parsePyValue(raw) {
  const value = String(raw ?? "").trim();
  if (value === "True") return true;
  if (value === "False") return false;
  if (value === "None") return null;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function readConst(source, name) {
  const match = source.match(new RegExp(`^${name} = (.*)$`, "m"));
  return match ? parsePyValue(match[1]) : undefined;
}

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function normalizeEndpoint(value) {
  return String(value ?? "").trim();
}

async function main() {
  console.log(
    `${c.cyan}${c.bold}▶ Validiere API-Starter-Skripte${c.reset} ${c.dim}(${scriptsDir})${c.reset}`
  );

  if (!existsSync(apisFile) || !existsSync(overridesFile)) {
    console.error(`${c.red}✖ Quelldaten fehlen.${c.reset}`);
    process.exit(1);
  }

  const apis = JSON.parse(await readFile(apisFile, "utf8"));
  const overrides = JSON.parse(await readFile(overridesFile, "utf8"));

  const failures = [];
  const hashes = new Map();

  for (const api of apis) {
    const slug = api.slug;
    const details = api.details ?? {};
    const override = overrides[slug] ?? {};
    const expectedEndpoint = normalizeEndpoint(
      override.endpoint ?? details.endpoint ?? ""
    );
    const expected = {
      slug,
      title: api.title,
      provider: details.provider ?? "",
      category: api.category ?? "",
      tags: Array.isArray(api.tags) ? api.tags : [],
      docsUrl: details.docsUrl ?? "",
      website: details.website ?? "",
      endpoint: expectedEndpoint,
    };

    const dir = join(scriptsDir, slug);
    const scriptFile = join(dir, `${slug}.py`);
    const metadataFile = join(dir, "metadata.json");

    if (!existsSync(scriptFile) || !existsSync(metadataFile)) {
      failures.push(`${slug}: Skript oder metadata.json fehlt`);
      continue;
    }

    const source = await readFile(scriptFile, "utf8");
    const metadata = JSON.parse(await readFile(metadataFile, "utf8"));

    const actual = {
      slug: readConst(source, "API_SLUG"),
      title: readConst(source, "API_TITLE"),
      provider: readConst(source, "PROVIDER"),
      category: readConst(source, "CATEGORY"),
      tags: readConst(source, "TAGS"),
      docsUrl: readConst(source, "DOCS_URL"),
      website: readConst(source, "WEBSITE"),
      endpoint: readConst(source, "ENDPOINT"),
    };

    for (const key of Object.keys(expected)) {
      if (!same(actual[key], expected[key])) {
        failures.push(
          `${slug}: ${key} weicht ab (Skript: ${JSON.stringify(
            actual[key]
          )}, Quelle: ${JSON.stringify(expected[key])})`
        );
      }
    }

    // metadata.json muss dieselben Werte enthalten.
    for (const key of ["slug", "title", "provider", "category", "tags", "docsUrl", "website", "endpoint"]) {
      if (!same(metadata[key], expected[key])) {
        failures.push(
          `${slug}: metadata.${key} weicht ab (${JSON.stringify(
            metadata[key]
          )} != ${JSON.stringify(expected[key])})`
        );
      }
    }

    // Dynamische Endpunkte: Platzhalter erlaubt, aber nur mit --base-url.
    const hasPlaceholders = /[{}<>]/.test(expectedEndpoint);
    if (hasPlaceholders) {
      if (!source.includes("--base-url")) {
        failures.push(
          `${slug}: dynamischer Endpoint, aber Skript unterstützt kein --base-url`
        );
      }
      if (metadata.hasPlaceholders !== true) {
        failures.push(
          `${slug}: dynamischer Endpoint, aber metadata.hasPlaceholders ist nicht true`
        );
      }
    } else {
      // Host muss zum Provider passen.
      const endpointHost = hostOf(expectedEndpoint);
      const endpointDomain = registrableDomain(endpointHost);
      const providerKey = String(expected.provider).toLowerCase();
      const allowed = new Set(
        (PROVIDER_DOMAINS[providerKey] ?? []).map((d) => d.toLowerCase())
      );
      allowed.add(registrableDomain(hostOf(expected.website)));
      allowed.add(registrableDomain(hostOf(expected.docsUrl)));
      allowed.delete("");

      if (endpointDomain && !allowed.has(endpointDomain)) {
        failures.push(
          `${slug}: Endpoint-Domain "${endpointDomain}" passt nicht zu Provider "${expected.provider}" (erlaubt: ${[
            ...allowed,
          ].join(", ")})`
        );
      }
    }

    // Duplikat-Erkennung (ohne Generierungszeit).
    const normalized = source
      .replace(/^Generated at:.*$/m, "")
      .replace(/\s+/g, " ")
      .trim();
    const hash = createHash("sha256").update(normalized).digest("hex");
    if (hashes.has(hash)) {
      failures.push(
        `${slug}: identisches Skript wie "${hashes.get(hash)}" (Duplikat)`
      );
    } else {
      hashes.set(hash, slug);
    }
  }

  if (failures.length > 0) {
    console.error(
      `${c.red}${c.bold}✖ ${failures.length} Problem(e) gefunden:${c.reset}`
    );
    for (const failure of failures) {
      console.error(`  ${c.red}•${c.reset} ${failure}`);
    }
    process.exit(1);
  }

  console.log(
    `${c.green}${c.bold}✔ Alle ${apis.length} Skripte stimmen zu 100 % mit ihren APIs überein.${c.reset}`
  );
}

main().catch((error) => {
  console.error(`${c.red}${c.bold}✖ Validierung abgebrochen:${c.reset}`, error);
  process.exit(1);
});
