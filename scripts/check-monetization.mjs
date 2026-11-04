/**
 * check-monetization.mjs
 *
 * Fails the deploy when no real Lemon Squeezy checkout URL is configured.
 * This prevents shipping a site whose premium CTAs are silently disabled.
 *
 * Usage:
 *   npm run monetization:check
 *   node scripts/check-monetization.mjs --warn   (warn only, exit 0)
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const warnOnly = process.argv.includes("--warn");

async function loadEnv() {
  const raw = await readFile(join(root, ".env"), "utf8").catch(() => "");
  const values = {};
  for (const line of raw.split("\n")) {
    const match = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (match) values[match[1]] = match[2].trim();
  }
  return values;
}

const envFile = await loadEnv();
const value = (key) => (process.env[key] ?? envFile[key] ?? "").trim();

const PLACEHOLDER_MARKERS = [
  "your-store.lemonsqueezy.com",
  "your_store",
  "your-",
  "your_",
  "xxxxxxxx-",
  "variant_id",
  "checkout/buy/your",
];

function valid(name, raw) {
  if (!raw) return `${name} is empty`;
  const lower = raw.toLowerCase();
  if (PLACEHOLDER_MARKERS.some((marker) => lower.includes(marker))) {
    return `${name} still contains a placeholder`;
  }
  try {
    const url = new URL(raw);
    if (!["http:", "https:"].includes(url.protocol)) {
      return `${name} is not an HTTP(S) URL`;
    }
  } catch {
    return `${name} is not a valid URL`;
  }
  return "";
}

const generic = value("PUBLIC_LEMON_CHECKOUT_URL");
const workflow = value("PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL");
const tiers = [
  "PUBLIC_LEMON_WORKFLOW_CHECKOUT_BEGINNER",
  "PUBLIC_LEMON_WORKFLOW_CHECKOUT_INTERMEDIATE",
  "PUBLIC_LEMON_WORKFLOW_CHECKOUT_ADVANCED",
  "PUBLIC_LEMON_WORKFLOW_CHECKOUT_EXPERT",
];
const script = value("PUBLIC_LEMON_SCRIPT_CHECKOUT_URL");
const playbook = value("PUBLIC_LEMON_PLAYBOOK_CHECKOUT_URL");

const problems = [];

if (!tiers.some((key) => value(key)) && !workflow && !generic) {
  problems.push(
    "No workflow checkout configured. Set all four tier URLs " +
      `(${tiers.join(", ")}) or PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL.`,
  );
}

for (const key of [...tiers, "PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL"]) {
  const raw = value(key);
  if (!raw) continue;
  const error = valid(key, raw);
  if (error) problems.push(error);
}

if (!script && !generic) {
  problems.push(
    "No script checkout configured. Set PUBLIC_LEMON_SCRIPT_CHECKOUT_URL " +
      "(or PUBLIC_LEMON_CHECKOUT_URL).",
  );
} else {
  const error = valid("PUBLIC_LEMON_SCRIPT_CHECKOUT_URL", script || generic);
  if (error) problems.push(error);
}

if (!playbook && !generic) {
  problems.push(
    "No playbook checkout configured. Set PUBLIC_LEMON_PLAYBOOK_CHECKOUT_URL " +
      "(or PUBLIC_LEMON_CHECKOUT_URL).",
  );
} else {
  const error = valid(
    "PUBLIC_LEMON_PLAYBOOK_CHECKOUT_URL",
    playbook || generic,
  );
  if (error) problems.push(error);
}

if (problems.length > 0) {
  const message = [
    "[monetization] Premium checkout is not deployable:",
    ...problems.map((problem) => `  - ${problem}`),
    "",
    "Configure the variables in GitHub → Settings → Variables (or .env locally).",
    "Run with --warn to downgrade this to a warning.",
  ].join("\n");

  if (warnOnly) {
    console.warn(message);
    process.exit(0);
  }
  console.error(message);
  process.exit(1);
}

console.log("[monetization] Checkout configuration OK.");
