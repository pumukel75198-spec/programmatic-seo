import { describe, it, expect } from "vitest";
import {
  resolveProduct,
  createToken,
  verifyToken,
  isSlugAllowed,
} from "../../worker/download-gate/index.js";

const baseEnv = {
  DOWNLOAD_TOKEN_SECRET: "test-secret",
  LEMON_PRODUCT_MAP: JSON.stringify({
    "variant:123": { type: "single", slugs: ["content-automation"] },
    "product:999": { type: "bundle", slugs: ["*"] },
  }),
};

describe("resolveProduct", () => {
  it("löst ein variant-Mapping auf", () => {
    const product = resolveProduct(baseEnv, { variant_id: 123 });
    expect(product).not.toBeNull();
    expect(product.slugs).toEqual(["content-automation"]);
  });

  it("löst ein product-Mapping auf", () => {
    const product = resolveProduct(baseEnv, { product_id: 999 });
    expect(product.slugs).toEqual(["*"]);
  });

  it("gibt ohne Mapping null zurück", () => {
    expect(resolveProduct(baseEnv, { variant_id: 1 })).toBeNull();
  });

  it("erlaubt mit ALLOW_ALL_ON_VALID alles (Testphase)", () => {
    const product = resolveProduct({ ...baseEnv, ALLOW_ALL_ON_VALID: "1" }, {});
    expect(product.slugs).toEqual(["*"]);
  });
});

describe("Download-Token", () => {
  it("erstellt und verifiziert ein gültiges Token", async () => {
    const { token } = await createToken(baseEnv, {
      licenseKey: "KEY-1",
      product: { key: "variant:123", slugs: ["content-automation"] },
    });
    const payload = await verifyToken(baseEnv, token);
    expect(payload).not.toBeNull();
    expect(payload.s).toEqual(["content-automation"]);
  });

  it("lehnt ein manipuliertes Token ab", async () => {
    const { token } = await createToken(baseEnv, {
      licenseKey: "KEY-1",
      product: { key: "x", slugs: ["*"] },
    });
    expect(await verifyToken(baseEnv, `${token}x`)).toBeNull();
  });

  it("lehnt ein Token mit falschem Secret ab", async () => {
    const { token } = await createToken(baseEnv, {
      licenseKey: "KEY-1",
      product: { key: "x", slugs: ["*"] },
    });
    expect(
      await verifyToken(
        { ...baseEnv, DOWNLOAD_TOKEN_SECRET: "other-secret" },
        token,
      ),
    ).toBeNull();
  });

  it("lehnt leere/ungültige Tokens ab", async () => {
    expect(await verifyToken(baseEnv, "")).toBeNull();
    expect(await verifyToken(baseEnv, "abc.def")).toBeNull();
  });
});

describe("isSlugAllowed", () => {
  it("erlaubt Wildcard-Zugriff", () => {
    expect(isSlugAllowed({ s: "*" }, "anything")).toBe(true);
  });

  it("erlaubt nur gelistete Slugs", () => {
    expect(isSlugAllowed({ s: ["a"] }, "a")).toBe(true);
    expect(isSlugAllowed({ s: ["a"] }, "b")).toBe(false);
  });

  it("lehnt fehlende Werte ab", () => {
    expect(isSlugAllowed(null, "a")).toBe(false);
    expect(isSlugAllowed({ s: ["a"] }, "")).toBe(false);
  });
});
