import { describe, it, expect } from "vitest";
import {
  normalizeDifficulty,
  getWorkflowTier,
  getWorkflowPriceValue,
} from "../../src/lib/pricing";

describe("pricing", () => {
  it("normalisiert beliebige Schreibweisen", () => {
    expect(normalizeDifficulty("beginner")).toBe("Beginner");
    expect(normalizeDifficulty("ADVANCED")).toBe("Advanced");
    expect(normalizeDifficulty(" Expert ")).toBe("Expert");
  });

  it("fällt bei unbekannten Werten auf Intermediate zurück", () => {
    expect(normalizeDifficulty("unknown")).toBe("Intermediate");
    expect(normalizeDifficulty(null)).toBe("Intermediate");
    expect(normalizeDifficulty(undefined)).toBe("Intermediate");
  });

  it("liefert eine gültige Preisstufe", () => {
    const tier = getWorkflowTier("Beginner");
    expect(tier.price).toBeGreaterThan(0);
    expect(tier.label).toContain("€");
    expect(tier.envKey).toBeTruthy();
  });

  it("formatiert den Preis mit zwei Nachkommastellen", () => {
    expect(getWorkflowPriceValue("Beginner")).toMatch(/^\d+\.\d{2}$/);
  });
});
