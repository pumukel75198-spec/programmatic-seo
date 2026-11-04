import { test, expect } from "@playwright/test";

test.describe("Premium-Download", () => {
  test("zeigt den Premium-Bereich auf einer Workflow-Seite", async ({
    page,
  }) => {
    await page.goto("/en/workflows/content-automation/");

    const section = page.locator("[data-premium-download]").first();
    await expect(section).toBeVisible();

    // Bei konfiguriertem Download-Gate erscheint das Lizenz-Formular.
    await expect(section.locator("[data-license-form]")).toBeVisible();
  });

  test("Lizenz-Formular validiert eine leere Eingabe", async ({ page }) => {
    await page.goto("/en/workflows/content-automation/");

    const section = page.locator("[data-premium-download]").first();
    const form = section.locator("[data-license-form]");
    await expect(form).toBeVisible();

    // Absenden ohne Schlüssel -> Fehlermeldung, kein Netzwerk-Download.
    await form.locator('button[type="submit"]').click();
    await expect(section.locator("[data-license-error]")).toBeVisible();
  });
});
