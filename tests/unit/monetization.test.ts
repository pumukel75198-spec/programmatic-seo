import { describe, it, expect, vi, afterEach } from "vitest";
import {
  normalizeCheckoutUrl,
  resolveWorkflowCheckout,
  resolveScriptCheckout,
  resolveDownloadGate,
} from "../../src/lib/monetization";

describe("normalizeCheckoutUrl (Lemon-Squeezy-Schutz)", () => {
  it("gibt leere Werte leer zurück", () => {
    expect(normalizeCheckoutUrl("")).toBe("");
    expect(normalizeCheckoutUrl(null)).toBe("");
    expect(normalizeCheckoutUrl(undefined)).toBe("");
  });

  it("filtert Platzhalter-URLs heraus (keine toten Kauf-Buttons)", () => {
    expect(
      normalizeCheckoutUrl(
        "https://your-store.lemonsqueezy.com/checkout/buy/xxx",
      ),
    ).toBe("");
    expect(
      normalizeCheckoutUrl(
        "https://store.lemonsqueezy.com/checkout/buy/xxxxxxxx-xxxx",
      ),
    ).toBe("");
    expect(normalizeCheckoutUrl("https://example.com/variant_id")).toBe("");
  });

  it("lässt echte Checkout-URLs unverändert", () => {
    const url = "https://flowmatrix.lemonsqueezy.com/checkout/buy/abc-123";
    expect(normalizeCheckoutUrl(url)).toBe(url);
  });

  it("trimmt Whitespace", () => {
    expect(normalizeCheckoutUrl("  https://real.example/checkout  ")).toBe(
      "https://real.example/checkout",
    );
  });
});

describe("resolveWorkflowCheckout", () => {
  it("bevorzugt eine explizite URL", () => {
    expect(
      resolveWorkflowCheckout("Beginner", "https://real.example/checkout"),
    ).toBe("https://real.example/checkout");
  });

  it("filtert Platzhalter auch bei expliziter URL", () => {
    expect(
      resolveWorkflowCheckout(
        "Beginner",
        "https://your-store.lemonsqueezy.com/x",
      ),
    ).toBe("");
  });
});

describe("resolveScriptCheckout", () => {
  it("bevorzugt eine explizite URL", () => {
    expect(resolveScriptCheckout("https://real.example/script")).toBe(
      "https://real.example/script",
    );
  });

  it("filtert Platzhalter", () => {
    expect(resolveScriptCheckout("https://your-store.lemonsqueezy.com/x")).toBe(
      "",
    );
  });
});

describe("resolveDownloadGate", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("entfernt den abschließenden Slash", () => {
    vi.stubEnv("PUBLIC_DOWNLOAD_GATE_URL", "https://gate.example/");
    expect(resolveDownloadGate()).toBe("https://gate.example");
  });

  it("gibt ohne Env einen leeren String zurück", () => {
    vi.stubEnv("PUBLIC_DOWNLOAD_GATE_URL", "");
    expect(resolveDownloadGate()).toBe("");
  });
});
