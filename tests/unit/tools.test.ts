import { describe, it, expect } from "vitest";
import { withAffiliateParams } from "../../src/lib/tools";

describe("withAffiliateParams", () => {
  it("hängt den ref-Parameter an", () => {
    expect(
      withAffiliateParams("https://example.com/path", { ref: "abc" }),
    ).toBe("https://example.com/path?ref=abc");
  });

  it("erhält bestehende Query-Parameter", () => {
    const url = withAffiliateParams("https://example.com/?foo=1", {
      ref: "abc",
    });
    expect(url).toContain("foo=1");
    expect(url).toContain("ref=abc");
  });

  it("überschreibt vorhandene Keys, statt sie zu duplizieren", () => {
    expect(
      withAffiliateParams("https://example.com/?ref=old", { ref: "new" }),
    ).toBe("https://example.com/?ref=new");
  });

  it("erhält Hash-Fragmente", () => {
    expect(
      withAffiliateParams("https://example.com/#section", { ref: "abc" }),
    ).toContain("#section");
  });

  it("gibt ungültige URLs unverändert zurück", () => {
    expect(withAffiliateParams("not a url", { ref: "abc" })).toBe("not a url");
  });

  it("ignoriert leere Parameterwerte", () => {
    expect(withAffiliateParams("https://example.com/", { ref: "" })).toBe(
      "https://example.com/",
    );
  });
});
