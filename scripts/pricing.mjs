/**
 * Gemeinsame Preis-Logik für die Node-Skripte (PDF-Generierung + Validierung).
 *
 * Liest dieselbe `src/data/pricing.json` wie das Frontend, damit Website,
 * PDF und Schema immer denselben Preis pro Schwierigkeitsstufe zeigen.
 */
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

export const pricingFile = join(root, "src", "data", "pricing.json");

export async function loadPricing() {
  if (!existsSync(pricingFile)) {
    throw new Error(`Datei nicht gefunden: ${pricingFile}`);
  }
  return JSON.parse(await readFile(pricingFile, "utf8"));
}

export function normalizeDifficulty(value) {
  const v = String(value ?? "").trim().toLowerCase();
  if (v === "beginner") return "Beginner";
  if (v === "advanced") return "Advanced";
  if (v === "expert") return "Expert";
  return "Intermediate";
}

export function tierFor(pricing, difficulty) {
  const key = normalizeDifficulty(difficulty);
  return (
    pricing?.workflowTiers?.[key] ??
    pricing?.workflowTiers?.[pricing?.defaultTier] ??
    { price: 0, label: "", envKey: "" }
  );
}

/**
 * Checkout-URL für eine Preisstufe. Reihenfolge:
 *   1. tier-spezifische Env-Variable
 *   2. generische Workflow-Checkout-URL
 *   3. generische Lemon-Checkout-URL
 *   4. konfigurierte URL aus monetization.json
 */
export function tierCheckout(pricing, difficulty, fallback = "") {
  const tier = tierFor(pricing, difficulty);
  return (
    process.env[tier.envKey]?.trim() ||
    process.env.PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL?.trim() ||
    process.env.PUBLIC_LEMON_CHECKOUT_URL?.trim() ||
    fallback ||
    ""
  );
}
