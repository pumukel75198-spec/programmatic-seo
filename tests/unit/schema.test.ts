import { describe, it, expect } from "vitest";
import {
  websiteSchema,
  organizationSchema,
  breadcrumbSchema,
  productSchema,
  softwareApplicationSchema,
} from "../../src/lib/schema";
import type { ApiEntry } from "../../src/lib/content";

describe("websiteSchema", () => {
  it("erzeugt ein WebSite-Schema mit SearchAction", () => {
    const schema = websiteSchema();
    expect(schema["@type"]).toBe("WebSite");
    expect(String(schema.url)).toMatch(/^https:\/\//);
    expect(schema.potentialAction).toBeTruthy();
  });
});

describe("organizationSchema", () => {
  it("erzeugt ein Organization-Schema mit absolutem Logo", () => {
    const schema = organizationSchema();
    expect(schema["@type"]).toBe("Organization");
    const logo = schema.logo as { url: string };
    expect(logo.url).toMatch(/^https:\/\//);
  });
});

describe("breadcrumbSchema", () => {
  it("nummeriert die Positionen fortlaufend ab 1", () => {
    const schema = breadcrumbSchema([
      { name: "Home", url: "/" },
      { name: "APIs", url: "/en/apis/" },
    ]);
    const items = schema.itemListElement as Array<{
      position: number;
      item: string;
    }>;
    expect(items[0].position).toBe(1);
    expect(items[1].position).toBe(2);
    expect(items[0].item).toMatch(/^https:\/\//);
  });
});

describe("productSchema (Lemon-Squeezy-Offer)", () => {
  it("enthält Preis, Währung und Checkout-URL", () => {
    const schema = productSchema({
      name: "Premium PDF",
      description: "Test",
      url: "/en/workflows/test/",
      price: "9.99",
      checkoutUrl: "https://flowmatrix.lemonsqueezy.com/checkout/buy/abc",
    });
    const offers = schema.offers as {
      price: string;
      priceCurrency: string;
      url: string;
      availability: string;
    };
    expect(offers.price).toBe("9.99");
    expect(offers.priceCurrency).toBe("EUR");
    expect(offers.url).toContain("lemonsqueezy.com");
    expect(offers.availability).toBe("https://schema.org/InStock");
  });
});

describe("softwareApplicationSchema", () => {
  it("erzeugt ein SoftwareApplication-Schema ohne offers", () => {
    const api = {
      slug: "test-api",
      title: "Test API",
      description: "A test API",
      category: "Testing",
      tags: ["test"],
      details: {
        provider: "Test Inc",
        website: "https://example.com",
        features: ["Feature A"],
        pricing: "Free",
      },
    } as unknown as ApiEntry;

    const schema = softwareApplicationSchema(api, "en");
    expect(schema["@type"]).toBe("SoftwareApplication");
    expect(schema.offers).toBeUndefined();
    expect(String(schema.url)).toContain("/en/apis/test-api/");
  });
});
