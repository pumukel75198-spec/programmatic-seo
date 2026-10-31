/**
 * Preis-Leiter für Premium-Workflow-PDFs.
 *
 * Die Preise hängen an der Schwierigkeit (`details.difficulty`) des Workflows.
 * Ein zentrales JSON (`src/data/pricing.json`) ist die einzige Quelle der
 * Wahrheit – auch die PDF-Generierung und die Validatoren lesen daraus, damit
 * Website, PDF und Schema niemals auseinanderlaufen.
 */
import pricingData from "../data/pricing.json";

export type Difficulty = "Beginner" | "Intermediate" | "Advanced" | "Expert";

export interface WorkflowTier {
  price: number;
  label: string;
  envKey: string;
}

export interface PricingConfig {
  currency: string;
  defaultTier: Difficulty;
  workflowTiers: Record<Difficulty, WorkflowTier>;
  script: { price: number; label: string };
}

export const pricing = pricingData as PricingConfig;

/** Normalisiert beliebige Difficulty-Schreibweisen auf einen bekannten Tier. */
export function normalizeDifficulty(value?: string | null): Difficulty {
  const v = (value ?? "").trim().toLowerCase();
  if (v === "beginner") return "Beginner";
  if (v === "advanced") return "Advanced";
  if (v === "expert") return "Expert";
  return "Intermediate";
}

/** Liefert die Preisstufe für eine Difficulty (mit sicherem Default). */
export function getWorkflowTier(difficulty?: string | null): WorkflowTier {
  const key = normalizeDifficulty(difficulty);
  return pricing.workflowTiers[key] ?? pricing.workflowTiers[pricing.defaultTier];
}

/** Numerischer Preis als String für JSON-LD (z. B. "7.99"). */
export function getWorkflowPriceValue(difficulty?: string | null): string {
  return getWorkflowTier(difficulty).price.toFixed(2);
}
