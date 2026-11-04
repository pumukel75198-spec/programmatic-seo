import { test, expect } from "@playwright/test";

test.describe("Intent-Suche", () => {
  test("liefert Ergebnisse für einen Suchbegriff", async ({ page }) => {
    await page.goto("/en/discover/");

    const input = page.locator("#intent-search");
    await expect(input).toBeVisible();

    await input.fill("stripe");

    // Ergebnisse erscheinen asynchron (Debounce + Rendering).
    await expect(page.locator("#intent-results a").first()).toBeVisible({
      timeout: 5000,
    });
  });

  test("zeigt den Startzustand ohne Suchbegriff", async ({ page }) => {
    await page.goto("/en/discover/");
    await expect(page.locator("#intent-start")).toBeVisible();
  });
});
