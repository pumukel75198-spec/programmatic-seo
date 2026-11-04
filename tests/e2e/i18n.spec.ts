import { test, expect } from "@playwright/test";

test("Sprachwechsel EN -> DE aktualisiert URL und lang-Attribut", async ({
  page,
}) => {
  await page.goto("/en/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");

  await page.selectOption("#language-select", "de");

  await expect(page).toHaveURL(/\/de\//);
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
});
