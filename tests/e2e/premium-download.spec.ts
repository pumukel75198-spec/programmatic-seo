import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Der Workflow-Slug wird dynamisch aus den Daten gelesen, damit der Test nicht
 * bricht, sobald ein einzelner Workflow umbenannt oder entfernt wird.
 */
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const workflows = JSON.parse(
  readFileSync(path.join(__dirname, "../../src/data/workflows.json"), "utf8"),
) as Array<{ slug: string }>;
const workflowSlug = workflows[0].slug;
const workflowUrl = `/en/workflows/${workflowSlug}/`;

test.describe("Premium-Download", () => {
  test("zeigt den Premium-Bereich auf einer Workflow-Seite", async ({
    page,
  }) => {
    await page.goto(workflowUrl);

    const section = page.locator("[data-premium-download]").first();
    await expect(section).toBeVisible();

    // Bei konfiguriertem Download-Gate erscheint das Lizenz-Formular.
    await expect(section.locator("[data-license-form]")).toBeVisible();
  });

  test("Lizenz-Formular validiert eine leere Eingabe", async ({ page }) => {
    await page.goto(workflowUrl);

    const section = page.locator("[data-premium-download]").first();
    const form = section.locator("[data-license-form]");
    await expect(form).toBeVisible();

    // Absenden ohne Schlüssel -> Fehlermeldung, kein Netzwerk-Download.
    await form.locator('button[type="submit"]').click();
    await expect(section.locator("[data-license-error]")).toBeVisible();
  });
});
