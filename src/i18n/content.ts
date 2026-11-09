/**
 * Localization helpers for the pSEO data.
 *
 * The site is English-only by design. These helpers are intentionally no-ops
 * that return the base English records; they keep the page templates and the
 * search index unchanged while removing the old German override layer.
 */
import type { AlternativeEntry, ApiEntry, WorkflowEntry } from "../lib/content";

export type ContentKind = "apis" | "alternatives" | "workflows";

/** No non-English overrides exist; only English is a built locale. */
export function hasOverride(
  _kind: ContentKind,
  _slug: string,
  code: string,
): boolean {
  return code === "en";
}

export function localizeApi(api: ApiEntry, _lang: string): ApiEntry {
  return api;
}

export function localizeAlternative(
  entry: AlternativeEntry,
  _lang: string,
): AlternativeEntry {
  return entry;
}

export function localizeWorkflow(
  workflow: WorkflowEntry,
  _lang: string,
): WorkflowEntry {
  return workflow;
}
