import { describe, it, expect } from "vitest";
import {
  MIN_ARTICLE_WORDS,
  isDuplicateTitle,
  isRelevant,
  jaccardSimilarity,
  relevanceScore,
  wordCount,
} from "../../scripts/lib/insights-rules.mjs";

describe("relevance gate", () => {
  it("akzeptiert klar nischige API-/Automationsthemen", () => {
    const item = {
      title: "New webhook automation for API workflows",
      summary:
        "A developer platform adds SDK support and rate limits for integrations.",
      category: "Automation",
      feed: "n8n Blog",
    };
    expect(relevanceScore(item)).toBeGreaterThanOrEqual(2);
    expect(isRelevant(item)).toBe(true);
  });

  it("lehnt off-topic Promi-/Allgemein-News ab", () => {
    const item = {
      title: "Celebrity chef opens a new restaurant in Paris",
      summary: "A story about food, travel and television.",
      category: "General",
      feed: "General News",
    };
    expect(isRelevant(item)).toBe(false);
  });

  it("kann per minScore=0 deaktiviert werden", () => {
    expect(isRelevant({ title: "anything" }, 0)).toBe(true);
  });
});

describe("duplicate detection", () => {
  it("erkennt fast identische Titel", () => {
    expect(
      isDuplicateTitle("OpenAI math challenge results", [
        "OpenAI math challenge",
      ]),
    ).toBe(true);
  });

  it("erkennt unterschiedliche Themen als verschieden", () => {
    expect(
      isDuplicateTitle("Stripe webhook retries", [
        "Figma design tokens",
        "Supabase realtime dashboard",
      ]),
    ).toBe(false);
  });

  it("Jaccard-Ähnlichkeit ist symmetrisch", () => {
    const a = "API rate limiting best practices";
    const b = "Best practices for API rate limits";
    expect(jaccardSimilarity(a, b)).toBeCloseTo(jaccardSimilarity(b, a));
  });
});

describe("wordCount", () => {
  it("zählt Wörter unabhängig von Whitespace", () => {
    expect(wordCount("  one   two\nthree ")).toBe(3);
    expect(wordCount("")).toBe(0);
  });

  it("Mindestlänge ist 700 Wörter", () => {
    expect(MIN_ARTICLE_WORDS).toBe(700);
  });
});
