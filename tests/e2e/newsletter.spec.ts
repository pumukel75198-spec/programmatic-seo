import { test, expect } from "@playwright/test";

test.describe("Newsletter-Formular", () => {
  test("zeigt bei fehlendem Consent die Consent-Meldung (nicht E-Mail-Fehler)", async ({
    page,
  }) => {
    await page.goto("/en/");
    const form = page.locator("[data-newsletter-form]").first();
    await form.locator('input[name="email"]').fill("test@example.com");
    // Consent absichtlich NICHT setzen
    await form.locator('button[type="submit"]').click();

    const status = form.locator("[data-newsletter-status]");
    await expect(status).toBeVisible();
    await expect(status).toContainText(/privacy policy/i);
    await expect(status).not.toContainText(/valid email/i);
  });

  test("validiert eine ungültige E-Mail-Adresse", async ({ page }) => {
    await page.goto("/en/");
    const form = page.locator("[data-newsletter-form]").first();
    await form.locator('input[name="email"]').fill("nope");
    await form.locator('input[name="consent"]').check();
    await form.locator('button[type="submit"]').click();

    await expect(form.locator("[data-newsletter-status]")).toContainText(
      /valid email/i,
    );
  });
});
