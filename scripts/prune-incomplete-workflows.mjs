#!/usr/bin/env node
/**
 * prune-incomplete-workflows.mjs
 *
 * Entfernt Workflows, die nach der Detail-Anreicherung unvollständig sind
 * (fehlende actions/checklist/expectedResult). Solche Einträge würden die
 * PDF-Qualitätsprüfung blockieren und den gesamten Batch scheitern lassen.
 *
 * Die entfernten Einträge werden zur Nachvollziehbarkeit in
 * `src/data/workflows-incomplete.json` gesichert.
 *
 * Verwendung:
 *   node scripts/prune-incomplete-workflows.mjs
 *   node scripts/prune-incomplete-workflows.mjs --dry-run
 */

import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const workflowsFile = join(root, "src", "data", "workflows.json");
const incompleteFile = join(root, "src", "data", "workflows-incomplete.json");

const dryRun = process.argv.includes("--dry-run");

function isComplete(workflow) {
  const steps = (workflow.details?.steps ?? []).filter(
    (step) => step && typeof step === "object"
  );
  if (steps.length === 0) return false;
  return steps.every(
    (step) =>
      Array.isArray(step.actions) &&
      step.actions.length >= 3 &&
      Array.isArray(step.checklist) &&
      step.checklist.length >= 2 &&
      typeof step.expectedResult === "string" &&
      step.expectedResult.trim() !== ""
  );
}

async function main() {
  if (!existsSync(workflowsFile)) {
    console.error(`✖ Datei nicht gefunden: ${workflowsFile}`);
    process.exit(1);
  }

  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));
  const complete = workflows.filter(isComplete);
  const incomplete = workflows.filter((workflow) => !isComplete(workflow));

  if (incomplete.length === 0) {
    console.log("✔ Alle Workflows sind vollständig – nichts zu bereinigen.");
    return;
  }

  console.log(
    `▶ ${incomplete.length} unvollständige Workflow(s) gefunden: ${incomplete
      .map((workflow) => workflow.slug)
      .join(", ")}`
  );

  if (dryRun) {
    console.log("  (dry-run – keine Änderungen geschrieben)");
    return;
  }

  // Bestehende Sicherung laden und ergänzen, damit nichts verloren geht.
  let archived = [];
  if (existsSync(incompleteFile)) {
    try {
      archived = JSON.parse(await readFile(incompleteFile, "utf8"));
      if (!Array.isArray(archived)) archived = [];
    } catch {
      archived = [];
    }
  }
  const archivedSlugs = new Set(archived.map((workflow) => workflow.slug));
  for (const workflow of incomplete) {
    if (!archivedSlugs.has(workflow.slug)) archived.push(workflow);
  }

  await writeFile(
    incompleteFile,
    `${JSON.stringify(archived, null, 2)}\n`,
    "utf8"
  );
  await writeFile(
    workflowsFile,
    `${JSON.stringify(complete, null, 2)}\n`,
    "utf8"
  );

  console.log(
    `✔ ${incomplete.length} unvollständige Workflow(s) entfernt und in workflows-incomplete.json gesichert.`
  );
}

main().catch((error) => {
  console.error("✖ Bereinigung fehlgeschlagen:", error);
  process.exit(1);
});
