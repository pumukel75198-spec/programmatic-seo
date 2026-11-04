/**
 * UI labels for the Intent-Finder (/discover).
 *
 * Kept separate from the global translation map so the discover feature can
 * ship without touching every legacy locale. Falls back to English.
 */
export interface DiscoverLabels {
  eyebrow: string;
  title: string;
  description: string;
  placeholder: string;
  searchLabel: string;
  examplesLabel: string;
  examples: string[];
  typeAll: string;
  typeApi: string;
  typeAlternative: string;
  typeWorkflow: string;
  resultsLabel: string;
  startTitle: string;
  startText: string;
  emptyTitle: string;
  emptyText: string;
  browseApis: string;
  browseAlternatives: string;
  browseWorkflows: string;
  clear: string;
  open: string;
  hint: string;
}

export const discoverLabels: Record<string, DiscoverLabels> = {
  en: {
    eyebrow: "Intent finder",
    title: "Find the right API, alternative or workflow",
    description:
      "Describe what you want to build. We search APIs, alternatives and workflows at once and show the best matches – no filters required.",
    placeholder: "e.g. stripe alternative, newsletter automation, image API …",
    searchLabel: "Search FlowMatrix",
    examplesLabel: "Try one of these",
    examples: [
      "stripe alternative",
      "newsletter automation",
      "image generation API",
      "notion alternative",
    ],
    typeAll: "All",
    typeApi: "APIs",
    typeAlternative: "Alternatives",
    typeWorkflow: "Workflows",
    resultsLabel: "results for",
    startTitle: "What do you want to build?",
    startText:
      "Start typing or pick an example. Results update instantly and cover all three categories.",
    emptyTitle: "No matches yet",
    emptyText:
      "Try a broader term, a tool name or a use case. You can also browse the full categories.",
    browseApis: "Browse all APIs",
    browseAlternatives: "Browse all alternatives",
    browseWorkflows: "Browse all workflows",
    clear: "Clear search",
    open: "Details",
    hint: "Press Enter to open the top result",
  },
  de: {
    eyebrow: "Intent-Finder",
    title: "Finde die passende API, Alternative oder Workflow",
    description:
      "Beschreibe, was du bauen möchtest. Wir durchsuchen APIs, Alternativen und Workflows gleichzeitig und zeigen die besten Treffer – ohne Filterpflicht.",
    placeholder: "z. B. Stripe-Alternative, Newsletter-Automation, Bild-API …",
    searchLabel: "FlowMatrix durchsuchen",
    examplesLabel: "Zum Ausprobieren",
    examples: [
      "Stripe-Alternative",
      "Newsletter-Automation",
      "Bild-API",
      "Notion-Alternative",
    ],
    typeAll: "Alle",
    typeApi: "APIs",
    typeAlternative: "Alternativen",
    typeWorkflow: "Workflows",
    resultsLabel: "Treffer für",
    startTitle: "Was möchtest du bauen?",
    startText:
      "Tippe los oder wähle ein Beispiel. Die Treffer aktualisieren sich sofort und umfassen alle drei Kategorien.",
    emptyTitle: "Noch keine Treffer",
    emptyText:
      "Versuche einen allgemeineren Begriff, einen Tool-Namen oder einen Anwendungsfall. Du kannst auch die Kategorien durchstöbern.",
    browseApis: "Alle APIs ansehen",
    browseAlternatives: "Alle Alternativen ansehen",
    browseWorkflows: "Alle Workflows ansehen",
    clear: "Suche löschen",
    open: "Details",
    hint: "Enter öffnet den besten Treffer",
  },
};
