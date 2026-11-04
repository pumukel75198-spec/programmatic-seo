import { describe, it, expect } from "vitest";
import { buildSearchIndex } from "../../src/lib/search-index";
import { apis, alternatives, workflows } from "../../src/lib/content";

describe("buildSearchIndex", () => {
  it("kombiniert alle Inhalte (APIs + Alternativen + Workflows)", () => {
    const index = buildSearchIndex("en");
    expect(index.length).toBe(
      apis.length + alternatives.length + workflows.length,
    );
  });

  it("enthält nur gültige Typen", () => {
    const index = buildSearchIndex("en");
    for (const item of index) {
      expect(["api", "alternative", "workflow"]).toContain(item.type);
    }
  });

  it("erzeugt lokalisierte URLs", () => {
    const en = buildSearchIndex("en");
    const de = buildSearchIndex("de");
    expect(en.every((item) => item.url.startsWith("/en/"))).toBe(true);
    expect(de.every((item) => item.url.startsWith("/de/"))).toBe(true);
  });

  it("liefert immer ein tags-Array", () => {
    const index = buildSearchIndex("en");
    expect(index.every((item) => Array.isArray(item.tags))).toBe(true);
  });
});
