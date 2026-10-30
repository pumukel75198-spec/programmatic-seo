#!/usr/bin/env node
/**
 * test-api-scripts.mjs
 *
 * Prüft die generierten Python-Starter-Skripte in `public/api-scripts/`
 * auf Funktionsfähigkeit. Drei Stufen:
 *
 *   1. Syntax   – `ast.parse` (kein Bytecode, keine Ausführung)
 *   2. Dry-Run  – `python3 <slug>.py --dry-run` (Request wird nur gebaut)
 *   3. Smoke    – `python3 <slug>.py --smoke` (Endpunkt erreichbar? 2xx–4xx = ok)
 *
 * Optional:
 *   4. Live     – `python3 <slug>.py --live` (echter Call, nur mit `--live`
 *                 und gesetztem Key in der Umgebung)
 *
 * Ausführen:
 *   npm run api-scripts:test             # Syntax + Dry-Run + Smoke
 *   npm run api-scripts:test:offline     # Syntax + Dry-Run (ohne Netzwerk)
 *   npm run api-scripts:test -- --live   # zusätzlich echte Calls (Keys nötig)
 *
 * Nützliche Flags:
 *   --offline          Smoke/Live überspringen
 *   --lenient          Netzwerkfehler als Warnung statt Fehler werten
 *   --only=<slug>      Nur ein Skript testen (mehrfach möglich)
 *   --live             Live-Calls ausführen
 *   --verbose          Ausgabe der Skripte bei Fehlern
 *   --no-generate      Vorhandene Skripte testen, nicht neu generieren
 *   --concurrency=<n>  Parallelität (Default: 6)
 *   --timeout=<sec>    Timeout pro Netzwerk-Test (Default: 12)
 */

import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { promisify } from "node:util";
import { generateAllApiScripts } from "./generate-api-scripts.mjs";

const execFileAsync = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const root = join(__dirname, "..");
const outputDir = process.env.API_SCRIPTS_OUTPUT_DIR
  ? resolve(root, process.env.API_SCRIPTS_OUTPUT_DIR)
  : join(root, "public", "api-scripts");
const manifestFile = join(outputDir, "index.json");
const python = process.env.PYTHON || "python3";

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
/* CLI                                                                        */
/* -------------------------------------------------------------------------- */

const argv = process.argv.slice(2);
const flags = {
  offline: argv.includes("--offline") || process.env.API_SCRIPTS_OFFLINE === "1",
  lenient: argv.includes("--lenient"),
  live: argv.includes("--live"),
  verbose: argv.includes("--verbose"),
  generate: !argv.includes("--no-generate"),
  only: argv
    .filter((arg) => arg.startsWith("--only="))
    .map((arg) => arg.slice("--only=".length)),
  concurrency: Number(
    argv.find((arg) => arg.startsWith("--concurrency="))?.split("=")[1] ?? 6
  ),
  timeout: Number(
    argv.find((arg) => arg.startsWith("--timeout="))?.split("=")[1] ?? 12
  ),
};

/* -------------------------------------------------------------------------- */
/* Execution helpers                                                          */
/* -------------------------------------------------------------------------- */

async function runPython(args, timeoutMs) {
  try {
    const { stdout, stderr } = await execFileAsync(python, args, {
      timeout: timeoutMs,
      maxBuffer: 4 * 1024 * 1024,
      env: process.env,
    });
    return { ok: true, code: 0, stdout, stderr, killed: false };
  } catch (error) {
    return {
      ok: false,
      code: typeof error.code === "number" ? error.code : 1,
      stdout: error.stdout ?? "",
      stderr: error.stderr ?? "",
      killed: Boolean(error.killed),
      signal: error.signal ?? null,
      message: error.message ?? String(error),
    };
  }
}

const syntaxScript =
  "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())";

async function checkSyntax(filePath) {
  const result = await runPython(["-c", syntaxScript, filePath], 15000);
  if (result.ok) return { status: "pass" };
  return {
    status: "fail",
    detail: (result.stderr || result.message || "Syntaxfehler").trim(),
  };
}

async function checkDryRun(filePath) {
  const result = await runPython([filePath, "--dry-run", "--timeout", "5"], 15000);
  if (result.ok && String(result.stdout).includes("Dry run")) {
    return { status: "pass" };
  }
  return {
    status: "fail",
    detail: (
      result.stderr ||
      result.stdout ||
      result.message ||
      `Exit-Code ${result.code}`
    ).trim(),
  };
}

async function checkSmoke(filePath) {
  const result = await runPython(
    [filePath, "--smoke", "--timeout", String(flags.timeout)],
    (flags.timeout + 5) * 1000
  );
  if (result.ok) return { status: "pass" };

  const detail = (
    result.stderr ||
    result.stdout ||
    result.message ||
    (result.killed ? "Timeout" : `Exit-Code ${result.code}`)
  ).trim();

  // Netzwerkfehler sind oft transient (DNS, Firewall, Rate-Limit). Mit
  // --lenient werden sie als Warnung statt als Fehler gewertet.
  if (flags.lenient) return { status: "warn", detail };
  return { status: "fail", detail };
}

async function checkLive(filePath, keyEnv) {
  const hasKey = Boolean(process.env[keyEnv]?.trim());
  if (!hasKey) {
    return { status: "skip", detail: `${keyEnv} ist nicht gesetzt` };
  }
  const result = await runPython(
    [filePath, "--live", "--timeout", String(flags.timeout)],
    (flags.timeout + 8) * 1000
  );
  if (result.ok) return { status: "pass" };
  const detail = (
    result.stderr ||
    result.stdout ||
    result.message ||
    `Exit-Code ${result.code}`
  ).trim();
  if (flags.lenient) return { status: "warn", detail };
  return { status: "fail", detail };
}

/* -------------------------------------------------------------------------- */
/* Pool                                                                       */
/* -------------------------------------------------------------------------- */

async function runPool(items, limit, worker) {
  const results = new Array(items.length);
  let cursor = 0;
  const workers = Array.from(
    { length: Math.max(1, Math.min(limit, items.length)) },
    async () => {
      while (true) {
        const index = cursor;
        cursor += 1;
        if (index >= items.length) return;
        results[index] = await worker(items[index], index);
      }
    }
  );
  await Promise.all(workers);
  return results;
}

/* -------------------------------------------------------------------------- */
/* Main                                                                       */
/* -------------------------------------------------------------------------- */

function statusLabel(status) {
  if (status === "pass") return `${c.green}ok${c.reset}`;
  if (status === "warn") return `${c.yellow}warn${c.reset}`;
  if (status === "skip") return `${c.dim}skip${c.reset}`;
  return `${c.red}fail${c.reset}`;
}

async function main() {
  console.log(
    `${c.cyan}${c.bold}▶ Teste API-Starter-Skripte${c.reset} ${c.dim}(${python})${c.reset}`
  );

  // Python-Verfügbarkeit prüfen.
  const version = await runPython(["--version"], 10000);
  if (!version.ok) {
    console.error(
      `${c.red}✖ ${python} nicht gefunden. Installiere Python 3.8+ oder setze PYTHON.${c.reset}`
    );
    process.exit(1);
  }
  console.log(`  ${c.dim}${String(version.stdout || version.stderr).trim()}${c.reset}`);

  let manifest;
  if (flags.generate) {
    const generated = await generateAllApiScripts({ quiet: true });
    manifest = generated.manifest;
  } else {
    if (!existsSync(manifestFile)) {
      console.error(
        `${c.red}✖ Manifest fehlt: ${manifestFile}. Ohne --no-generate wird es erzeugt.${c.reset}`
      );
      process.exit(1);
    }
    manifest = JSON.parse(await readFile(manifestFile, "utf8"));
  }

  let entries = manifest.entries ?? [];
  if (flags.only.length > 0) {
    const wanted = new Set(flags.only);
    entries = entries.filter((entry) => wanted.has(entry.slug));
    if (entries.length === 0) {
      console.error(
        `${c.red}✖ Kein Skript passt zu --only=${flags.only.join(",")}${c.reset}`
      );
      process.exit(1);
    }
  }

  console.log(
    `  ${entries.length} Skripte · ${flags.offline ? "offline" : "mit Netzwerk"} · ` +
      `Parallelität ${flags.concurrency}${flags.live ? " · live" : ""}`
  );
  console.log("");

  const results = await runPool(entries, flags.concurrency, async (entry) => {
    const filePath = join(outputDir, entry.slug, entry.scriptFile);
    const result = { slug: entry.slug, checks: {} };

    if (!existsSync(filePath)) {
      result.checks.syntax = { status: "fail", detail: "Datei fehlt" };
      return result;
    }

    result.checks.syntax = await checkSyntax(filePath);
    result.checks.dry = await checkDryRun(filePath);

    if (flags.offline) {
      result.checks.smoke = { status: "skip", detail: "offline" };
    } else if (!entry.testable?.smoke) {
      result.checks.smoke = {
        status: "skip",
        detail: entry.hasPlaceholders
          ? "dynamischer Endpoint (Platzhalter)"
          : "kein Endpoint",
      };
    } else {
      result.checks.smoke = await checkSmoke(filePath);
    }

    if (flags.live) {
      if (!entry.testable?.live) {
        result.checks.live = {
          status: "skip",
          detail: "nicht live-testbar",
        };
      } else {
        result.checks.live = await checkLive(filePath, entry.keyEnv);
      }
    }

    return result;
  });

  /* --- Report ------------------------------------------------------------ */

  const totals = { pass: 0, fail: 0, warn: 0, skip: 0 };
  const failures = [];

  for (const result of results) {
    const parts = [];
    let entryFailed = false;
    let entryWarned = false;

    for (const [name, check] of Object.entries(result.checks)) {
      parts.push(`${name}: ${statusLabel(check.status)}`);
      totals[check.status] += 1;
      if (check.status === "fail") entryFailed = true;
      if (check.status === "warn") entryWarned = true;
    }

    const icon = entryFailed
      ? `${c.red}✖${c.reset}`
      : entryWarned
        ? `${c.yellow}!${c.reset}`
        : `${c.green}✓${c.reset}`;

    console.log(`  ${icon} ${result.slug.padEnd(42)} ${parts.join(" · ")}`);

    if (entryFailed) {
      failures.push(result);
      for (const [name, check] of Object.entries(result.checks)) {
        if (check.status === "fail" && check.detail) {
          console.log(`      ${c.red}${name}: ${check.detail}${c.reset}`);
        }
      }
    }

    if (flags.verbose && entryWarned) {
      for (const [name, check] of Object.entries(result.checks)) {
        if (check.status === "warn" && check.detail) {
          console.log(`      ${c.yellow}${name}: ${check.detail}${c.reset}`);
        }
      }
    }
  }

  console.log("");
  console.log(
    `${c.bold}Ergebnis:${c.reset} ` +
      `${c.green}${totals.pass} ok${c.reset} · ` +
      `${c.yellow}${totals.warn} warn${c.reset} · ` +
      `${c.dim}${totals.skip} skip${c.reset} · ` +
      `${c.red}${totals.fail} fehlgeschlagen${c.reset}`
  );

  if (failures.length > 0) {
    console.error(
      `${c.red}${c.bold}✖ ${failures.length} Skript(e) fehlgeschlagen.${c.reset}`
    );
    if (!flags.verbose) {
      console.error(
        `${c.dim}  Tipp: --verbose zeigt Warnungen, --only=<slug> isoliert ein Skript.${c.reset}`
      );
    }
    process.exit(1);
  }

  console.log(
    `${c.green}${c.bold}✔ Alle Skripte haben Syntax- und Dry-Run-Prüfung bestanden.${c.reset}` +
      (flags.offline
        ? ` ${c.dim}(Smoke-Test übersprungen)${c.reset}`
        : ` ${c.dim}(Smoke-Test für erreichbare Endpunkte ausgeführt)${c.reset}`)
  );
}

main().catch((error) => {
  console.error(`${c.red}${c.bold}✖ Testlauf abgebrochen:${c.reset}`, error);
  process.exit(1);
});
