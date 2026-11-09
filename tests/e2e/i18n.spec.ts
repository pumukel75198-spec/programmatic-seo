import { test, expect } from "@playwright/test";

// The site is English-only by design. The language switcher was removed;
// visitors with another browser language rely on the browser's translation.
test("Website ist Englisch-only und zeigt keinen Sprachwähler", async ({
  page,
}) => {
  await page.goto("/en/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("#language-select")).toHaveCount(0);
});

test("Englische Startseite lädt korrekt", async ({ page }) => {
  const response = await page.goto("/en/");
  expect(response?.status()).toBeLessThan(400);
  await expect(page.locator("h1").first()).toBeVisible();
});
