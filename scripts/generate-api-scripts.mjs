#!/usr/bin/env node
/**
 * generate-api-scripts.mjs
 *
 * Erzeugt für jede API aus `src/data/apis.json` ein eigenständiges,
 * herunterladbares Python-Starter-Skript in `public/api-scripts/<slug>/`.
 *
 * Warum Python?
 *   - Läuft ohne zusätzliche Abhängigkeiten (nur Standardbibliothek).
 *   - Ideal für Einsteiger und als Copy-&-Paste-Vorlage.
 *   - `--dry-run`, `--smoke` und `--live` sind direkt im Skript eingebaut.
 *
 * Ausgabe pro API:
 *   public/api-scripts/<slug>/<slug>.py      ausführbares Skript
 *   public/api-scripts/<slug>/README.md      Kurzanleitung
 *   public/api-scripts/<slug>/metadata.json  maschinenlesbare Metadaten
 *
 * Zusätzlich global:
 *   public/api-scripts/index.json            Manifest aller Skripte
 *   public/api-scripts/README.md             Übersicht
 *
 * Endpoint-Overrides (für APIs ohne `details.endpoint`) liegen in
 * `src/data/api-endpoints.json`.
 *
 * Ausführen:
 *   node scripts/generate-api-scripts.mjs
 *   npm run api-scripts:generate
 */

import { readFile, writeFile, mkdir, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const root = join(__dirname, "..");

const apisFile = join(root, "src", "data", "apis.json");
const overridesFile = join(root, "src", "data", "api-endpoints.json");
const outputDir = process.env.API_SCRIPTS_OUTPUT_DIR
  ? resolve(root, process.env.API_SCRIPTS_OUTPUT_DIR)
  : join(root, "private", "api-scripts");

const DEFAULT_HEADERS = { Accept: "application/json" };

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const isNonEmptyString = (value) =>
  typeof value === "string" && value.trim() !== "";

/** JSON value -> valid Python literal (None/True/False instead of null/true/false). */
function pyLiteral(value) {
  if (value === null || value === undefined) return "None";
  if (typeof value === "boolean") return value ? "True" : "False";
  if (typeof value === "number" || typeof value === "bigint") {
    return String(value);
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return `[${value.map((item) => pyLiteral(item)).join(", ")}]`;
  }
  if (typeof value === "object") {
    const entries = Object.entries(value).map(
      ([key, val]) => `${JSON.stringify(key)}: ${pyLiteral(val)}`
    );
    return `{${entries.join(", ")}}`;
  }
  return "None";
}

/** Make a string safe for a Python docstring. */
function docText(value) {
  return String(value ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/"""/g, "'''")
    .replace(/\s+/g, " ")
    .trim();
}

function slugToEnv(provider, fallback) {
  const base = String(provider || fallback || "API")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return `${base || "API"}_API_KEY`;
}

/**
 * Leitet den Auth-Stil aus dem Freitext `details.authentication` ab.
 * Overrides in api-endpoints.json haben Vorrang.
 */
function detectAuth(raw) {
  const value = String(raw ?? "").toLowerCase();
  if (!value || value === "—" || value === "none") {
    return { style: "none", header: "", param: "" };
  }
  if (value.includes("aws")) return { style: "aws-sigv4", header: "", param: "" };
  if (value.includes("account sid") || value.includes("basic")) {
    return { style: "basic", header: "", param: "" };
  }
  if (value.includes("bot token in url")) {
    return { style: "url-token", header: "", param: "" };
  }
  if (value.includes("bot token")) return { style: "bot", header: "", param: "" };
  if (value.includes("x-api-key")) {
    return { style: "header", header: "x-api-key", param: "" };
  }
  if (value.includes("api key") && value.includes("query")) {
    return { style: "query", header: "", param: "key" };
  }
  if (
    value.includes("bearer") ||
    value.includes("access token") ||
    value.includes("api token") ||
    value.includes("secret key") ||
    value.includes("personal access token") ||
    value.includes("oauth") ||
    value.includes("api key") ||
    value.includes("token")
  ) {
    return { style: "bearer", header: "", param: "" };
  }
  return { style: "bearer", header: "", param: "" };
}

function hasPlaceholders(endpoint) {
  return typeof endpoint === "string" && /[{}<>]/.test(endpoint);
}

/* -------------------------------------------------------------------------- */
/* Python template                                                            */
/* -------------------------------------------------------------------------- */

const PY_TEMPLATE = `#!/usr/bin/env python3
"""
__DOC_TITLE__ – example API client.

__DOC_DESCRIPTION__

Provider: __DOC_PROVIDER__
Docs:     __DOCS_URL__

Generated by FlowMatrix.dev – https://flowmatrix.dev
Generated at: __GENERATED_AT__

Usage
-----
  python __SCRIPT_FILE__ --dry-run     Show the request without sending it (default).
  python __SCRIPT_FILE__ --smoke       Check that the endpoint is reachable (no key needed).
  python __SCRIPT_FILE__ --live        Send a real request (requires __KEY_ENV__).

Environment
-----------
  __KEY_ENV__   API key or token used for --live.

This script only uses the Python standard library (Python 3.8+).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_SLUG = __SLUG_CONST__
API_TITLE = __TITLE_CONST__
CATEGORY = __CATEGORY_CONST__
TAGS = __TAGS_CONST__
PROVIDER = __PROVIDER_CONST__
DOCS_URL = __DOCS_CONST__
WEBSITE = __WEBSITE_CONST__
ENDPOINT = __ENDPOINT_CONST__
METHOD = __METHOD_CONST__
AUTH_STYLE = __AUTH_STYLE_CONST__
AUTH_HEADER = __AUTH_HEADER_CONST__
AUTH_PARAM = __AUTH_PARAM_CONST__
KEY_ENV = __KEY_ENV_CONST__
DEFAULT_HEADERS = __HEADERS_CONST__
DEFAULT_BODY = __BODY_CONST__
SUPPORTED_LIVE = __SUPPORTED_LIVE_CONST__


def mask_headers(headers):
    """Hide credentials when printing a request."""
    secret_keys = {
        "authorization",
        "x-api-key",
        "xi-api-key",
        "api-key",
        "ocp-apim-subscription-key",
        "x-shopify-access-token",
        "x-algolia-api-key",
    }
    masked = {}
    for key, value in headers.items():
        masked[key] = "***" if key.lower() in secret_keys and value else value
    return masked


def build_headers(api_key):
    headers = dict(DEFAULT_HEADERS)
    if not api_key:
        return headers
    if AUTH_STYLE == "bearer":
        headers["Authorization"] = "Bearer " + api_key
    elif AUTH_STYLE == "bot":
        headers["Authorization"] = "Bot " + api_key
    elif AUTH_STYLE == "header":
        headers[AUTH_HEADER or "x-api-key"] = api_key
    elif AUTH_STYLE == "token":
        headers[AUTH_HEADER or "Authorization"] = "Token " + api_key
    elif AUTH_STYLE == "basic":
        encoded = base64.b64encode(api_key.encode("utf-8")).decode("ascii")
        headers["Authorization"] = "Basic " + encoded
    # "query" and "url-token" are handled in resolve_endpoint().
    return headers


def resolve_endpoint(api_key):
    if not ENDPOINT:
        return None
    endpoint = ENDPOINT
    if "{token}" in endpoint and api_key:
        endpoint = endpoint.replace("{token}", urllib.parse.quote(api_key, safe=""))
    if AUTH_STYLE == "query" and api_key:
        separator = "&" if "?" in endpoint else "?"
        endpoint = endpoint + separator + urllib.parse.urlencode(
            {AUTH_PARAM or "key": api_key}
        )
    return endpoint


def unresolved_placeholders(endpoint):
    if not endpoint:
        return []
    return [marker for marker in ("{", "<") if marker in endpoint]


def main():
    parser = argparse.ArgumentParser(
        description="Example client for " + API_TITLE
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the request only (default)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="check endpoint reachability without sending credentials",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="send a real request (requires " + KEY_ENV + ")",
    )
    parser.add_argument(
        "--method",
        default=METHOD,
        help="HTTP method (default: %(default)s)",
    )
    parser.add_argument("--data", default=None, help="JSON request body")
    parser.add_argument(
        "--base-url",
        default=None,
        help="override the endpoint (required for dynamic endpoints with placeholders)",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="timeout in seconds"
    )
    args = parser.parse_args()

    api_key = os.environ.get(KEY_ENV, "").strip() or None
    endpoint = resolve_endpoint(api_key)
    if args.base_url:
        endpoint = args.base_url.strip()
    body = args.data if args.data is not None else DEFAULT_BODY

    print("API:      " + API_TITLE)
    print("Slug:     " + API_SLUG)
    print("Provider: " + PROVIDER)
    print("Category: " + CATEGORY)
    print("Docs:     " + (DOCS_URL or WEBSITE or "-"))
    print("Endpoint: " + (endpoint or "(not configured)"))
    print("Method:   " + args.method)
    print("Auth:     " + AUTH_STYLE + " (env: " + KEY_ENV + ")")

    if args.dry_run or (not args.smoke and not args.live):
        headers = build_headers(api_key)
        print("Headers:  " + json.dumps(mask_headers(headers), ensure_ascii=False))
        if body is not None:
            rendered = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            print("Body:     " + rendered)
        print("Dry run: no request sent. Use --smoke or --live.")
        return 0

    if not endpoint:
        print("ERROR: No endpoint configured for this API.")
        print("Add one in src/data/api-endpoints.json and regenerate the scripts.")
        return 2

    placeholders = unresolved_placeholders(endpoint)
    if placeholders:
        print("ERROR: Endpoint still contains placeholders: " + endpoint)
        print("Edit this script or add an override in src/data/api-endpoints.json.")
        return 2

    method = args.method
    data = None

    if args.smoke:
        # A plain GET without credentials is enough to prove that the host
        # answers. 2xx-4xx means "reachable", 5xx or a network error means "no".
        method = "GET"
        body = None
    else:
        if not SUPPORTED_LIVE:
            print("WARNING: " + AUTH_STYLE + " requires request signing and is not")
            print("         implemented in this starter script. Use the official SDK.")
            print("         Sending a plain request without a signature.")
        if not api_key:
            print("ERROR: " + KEY_ENV + " is not set. Export it before using --live.")
            return 2
        if body is not None:
            data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")

    headers = build_headers(api_key)
    if data is not None:
        headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(
        endpoint, data=data, headers=headers, method=method
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            payload = response.read(800).decode("utf-8", "replace")
            print("HTTP " + str(response.status))
            print(payload)
            return 0
    except urllib.error.HTTPError as error:
        payload = error.read(800).decode("utf-8", "replace")
        print("HTTP " + str(error.code))
        print(payload)
        if args.smoke:
            return 0 if 200 <= error.code < 500 else 1
        return 0 if 200 <= error.code < 300 else 1
    except Exception as error:  # noqa: BLE001
        print("ERROR: " + str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
`;

/* -------------------------------------------------------------------------- */
/* Build                                                                      */
/* -------------------------------------------------------------------------- */

function buildScript(api, override) {
  const details = api.details ?? {};
  const endpointOverride =
    override.endpoint !== undefined ? override.endpoint : details.endpoint;
  const endpoint = isNonEmptyString(endpointOverride)
    ? endpointOverride.trim()
    : null;

  const detected = detectAuth(details.authentication);
  const authStyle = override.auth ?? detected.style;
  const authHeader = override.authHeader ?? detected.header;
  const authParam = override.authParam ?? detected.param;
  const keyEnv =
    override.keyEnv ?? slugToEnv(details.provider, api.slug);
  const method = (override.method ?? "GET").toUpperCase();
  const headers = { ...DEFAULT_HEADERS, ...(override.headers ?? {}) };
  const body = override.body ?? null;

  const placeholders = hasPlaceholders(endpoint);
  const smokeTestable = !!endpoint && !placeholders;
  const liveTestable =
    !!endpoint &&
    !hasPlaceholders(endpoint.replace("{token}", "x")) &&
    !["aws-sigv4", "digest"].includes(authStyle);
  const supportedLive = !["aws-sigv4", "digest"].includes(authStyle);

  const generatedAt = new Date().toISOString();
  const scriptFile = `${api.slug}.py`;

  const replacements = {
    __DOC_TITLE__: docText(api.title),
    __DOC_DESCRIPTION__: docText(api.description),
    __DOC_PROVIDER__: docText(details.provider || "Unknown"),
    __DOCS_URL__: docText(details.docsUrl || details.website || "-"),
    __GENERATED_AT__: generatedAt,
    __SCRIPT_FILE__: scriptFile,
    __KEY_ENV__: keyEnv,
    __SLUG_CONST__: pyLiteral(api.slug),
    __TITLE_CONST__: pyLiteral(api.title),
    __CATEGORY_CONST__: pyLiteral(api.category ?? ""),
    __TAGS_CONST__: pyLiteral(Array.isArray(api.tags) ? api.tags : []),
    __PROVIDER_CONST__: pyLiteral(details.provider ?? ""),
    __DOCS_CONST__: pyLiteral(details.docsUrl ?? ""),
    __WEBSITE_CONST__: pyLiteral(details.website ?? ""),
    __ENDPOINT_CONST__: pyLiteral(endpoint),
    __METHOD_CONST__: pyLiteral(method),
    __AUTH_STYLE_CONST__: pyLiteral(authStyle),
    __AUTH_HEADER_CONST__: pyLiteral(authHeader ?? ""),
    __AUTH_PARAM_CONST__: pyLiteral(authParam ?? ""),
    __KEY_ENV_CONST__: pyLiteral(keyEnv),
    __HEADERS_CONST__: pyLiteral(headers),
    __BODY_CONST__: pyLiteral(body),
    __SUPPORTED_LIVE_CONST__: pyLiteral(supportedLive),
  };

  let script = PY_TEMPLATE;
  for (const [token, value] of Object.entries(replacements)) {
    script = script.split(token).join(value);
  }

  const metadata = {
    slug: api.slug,
    title: api.title,
    description: api.description,
    category: api.category ?? "",
    tags: Array.isArray(api.tags) ? api.tags : [],
    provider: details.provider ?? "",
    website: details.website ?? "",
    docsUrl: details.docsUrl ?? "",
    endpoint,
    method,
    authStyle,
    authHeader: authHeader ?? "",
    authParam: authParam ?? "",
    keyEnv,
    supportedLive,
    hasEndpoint: !!endpoint,
    hasPlaceholders: placeholders,
    testable: { smoke: smokeTestable, live: liveTestable },
    note: override.note ?? "",
    scriptFile,
    scriptUrl: `/api-scripts/${api.slug}/${scriptFile}`,
    readmeUrl: `/api-scripts/${api.slug}/README.md`,
    generatedAt,
  };

  return { script, metadata };
}

function buildReadme(meta) {
  const lines = [];
  lines.push(`# ${meta.title} – Starter Script`);
  lines.push("");
  lines.push(
    "Generated by [FlowMatrix.dev](https://flowmatrix.dev). A minimal, dependency-free Python client."
  );
  lines.push("");
  lines.push(`- **Provider:** ${meta.provider || "—"}`);
  lines.push(`- **Category:** ${meta.category || "—"}`);
  lines.push(`- **Endpoint:** \`${meta.endpoint || "not configured"}\``);
  lines.push(`- **Method:** \`${meta.method}\``);
  lines.push(
    `- **Auth:** \`${meta.authStyle}\` via \`${meta.keyEnv}\`${
      meta.authHeader ? ` (header \`${meta.authHeader}\`)` : ""
    }`
  );
  lines.push(`- **Docs:** ${meta.docsUrl || meta.website || "—"}`);
  lines.push("");
  lines.push("## Quick start");
  lines.push("");
  lines.push("```bash");
  lines.push(`# 1) Inspect the request (no network)`);
  lines.push(`python3 ${meta.scriptFile} --dry-run`);
  lines.push("");
  lines.push(`# 2) Check that the endpoint is reachable (no key needed)`);
  lines.push(`python3 ${meta.scriptFile} --smoke`);
  lines.push("");
  lines.push(`# 3) Send a real request`);
  lines.push(`export ${meta.keyEnv}="your-key"`);
  lines.push(`python3 ${meta.scriptFile} --live --data '{"example":"value"}'`);
  lines.push("```");
  lines.push("");
  lines.push("## Notes");
  lines.push("");
  lines.push("- Requires Python 3.8+ and only uses the standard library.");
  if (!meta.hasEndpoint) {
    lines.push(
      "- **No endpoint configured yet.** Add one in `src/data/api-endpoints.json` and regenerate."
    );
  } else if (meta.hasPlaceholders) {
    lines.push(
      `- The endpoint contains placeholders (e.g. \`{...}\`). Replace them before using \`--live\`.`
    );
  }
  if (!meta.supportedLive) {
    lines.push(
      "- This API needs request signing (AWS SigV4 / Digest). Use the official SDK for production calls."
    );
  }
  if (meta.note) {
    lines.push(`- ${meta.note}`);
  }
  lines.push("");
  lines.push("## Test status");
  lines.push("");
  lines.push(
    `- Smoke test (reachability): ${meta.testable.smoke ? "yes" : "skipped (dynamic endpoint)"}`
  );
  lines.push(
    `- Live test (with key): ${meta.testable.live ? "yes" : "requires manual setup"}`
  );
  lines.push("");
  return lines.join("\n");
}

function buildIndexReadme(manifest) {
  const lines = [];
  lines.push("# API Starter Scripts");
  lines.push("");
  lines.push(
    `This directory contains ${manifest.count} auto-generated Python starter scripts, one per API listed on [FlowMatrix.dev](https://flowmatrix.dev).`
  );
  lines.push("");
  lines.push(
    `- Scripts with a reachable endpoint: **${manifest.testable.smoke}**`
  );
  lines.push(
    `- Scripts requiring manual endpoint setup: **${manifest.count - manifest.testable.smoke}**`
  );
  lines.push("");
  lines.push("Each folder contains the script, a README and metadata:");
  lines.push("");
  lines.push("```");
  lines.push(`api-scripts/<slug>/<slug>.py`);
  lines.push(`api-scripts/<slug>/README.md`);
  lines.push(`api-scripts/<slug>/metadata.json`);
  lines.push("```");
  lines.push("");
  lines.push("Machine-readable manifest: [`index.json`](./index.json).");
  lines.push("");
  lines.push(
    "Regenerate with `npm run api-scripts:generate` and verify with `npm run api-scripts:test`."
  );
  lines.push("");
  return lines.join("\n");
}

/* -------------------------------------------------------------------------- */
/* Main                                                                       */
/* -------------------------------------------------------------------------- */

export async function loadInputs() {
  if (!existsSync(apisFile)) {
    throw new Error(`Datei nicht gefunden: ${apisFile}`);
  }
  const apis = JSON.parse(await readFile(apisFile, "utf8"));
  if (!Array.isArray(apis)) {
    throw new Error("apis.json muss ein Array sein.");
  }
  let overrides = {};
  if (existsSync(overridesFile)) {
    try {
      overrides = JSON.parse(await readFile(overridesFile, "utf8"));
    } catch (error) {
      throw new Error(`api-endpoints.json ist kein gültiges JSON: ${error.message}`);
    }
  }
  // Drop the comment key – it is documentation, not an API slug.
  delete overrides._comment;
  return { apis, overrides };
}

export async function generateAllApiScripts({ quiet = false } = {}) {
  const { apis, overrides } = await loadInputs();

  await rm(outputDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });

  const entries = [];
  let withoutEndpoint = 0;
  let dynamic = 0;

  for (const api of apis) {
    if (!api?.slug) continue;
    const override = overrides[api.slug] ?? {};
    const { script, metadata } = buildScript(api, override);

    const dir = join(outputDir, api.slug);
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, metadata.scriptFile), script, "utf8");
    await writeFile(join(dir, "README.md"), buildReadme(metadata), "utf8");
    await writeFile(
      join(dir, "metadata.json"),
      `${JSON.stringify(metadata, null, 2)}\n`,
      "utf8"
    );

    if (!metadata.hasEndpoint) withoutEndpoint += 1;
    else if (metadata.hasPlaceholders) dynamic += 1;

    entries.push(metadata);

    if (!quiet) {
      const status = !metadata.hasEndpoint
        ? `${c.yellow}no endpoint${c.reset}`
        : metadata.hasPlaceholders
          ? `${c.yellow}dynamic${c.reset}`
          : metadata.testable.smoke
            ? `${c.green}smoke ok${c.reset}`
            : `${c.dim}generated${c.reset}`;
      console.log(`  ✓ ${api.slug.padEnd(42)} ${status}`);
    }
  }

  const manifest = {
    generatedAt: new Date().toISOString(),
    count: entries.length,
    testable: {
      smoke: entries.filter((entry) => entry.testable.smoke).length,
      live: entries.filter((entry) => entry.testable.live).length,
    },
    entries,
  };

  await writeFile(
    join(outputDir, "index.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8"
  );
  await writeFile(join(outputDir, "README.md"), buildIndexReadme(manifest), "utf8");

  if (!quiet) {
    console.log("");
    console.log(
      `${c.green}${c.bold}✔ ${entries.length} API-Skripte erzeugt${c.reset} ${c.dim}(${outputDir})${c.reset}`
    );
    console.log(
      `  ${c.green}${manifest.testable.smoke}${c.reset} per Smoke-Test prüfbar, ` +
        `${c.yellow}${dynamic}${c.reset} mit dynamischem Endpoint, ` +
        `${c.yellow}${withoutEndpoint}${c.reset} ohne Endpoint.`
    );
  }

  return { manifest, outputDir };
}

async function main() {
  console.log(
    `${c.cyan}${c.bold}▶ Generiere API-Starter-Skripte${c.reset} ${c.dim}(Python)${c.reset}`
  );
  await generateAllApiScripts();
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(__filename)) {
  main().catch((error) => {
    console.error(`${c.red}${c.bold}✖ Generierung fehlgeschlagen:${c.reset}`, error);
    process.exit(1);
  });
}
