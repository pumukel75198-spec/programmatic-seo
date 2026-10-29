# FlowMatrix

Ein modernes **Astro + Tailwind CSS**-Projekt für Programmatic SEO mit drei dynamischen Routen-Kategorien, Mehrsprachigkeit und einem dunklen, responsiven UI.

## Features

- ⚡️ **Astro 7** mit statischem Output (SSG)
- 🎨 **Tailwind CSS 4** über die offizielle Vite-Integration
- 🌙 **Dark Mode** als Standard-Design
- 🧭 Drei dynamische Routen: **APIs**, **Alternativen**, **Workflows**
- 🌍 **12 Sprachen** (`en`, `de`, `fr`, `es`, `it`, `pt`, `nl`, `pl`, `sv`, `tr`, `ja`, `zh`) mit lokalisierten Routen
- 🔍 SEO-freundlich: Canonical-URLs, Open-Graph-/Twitter-Meta-Tags, JSON-LD, Sitemap und `robots.txt`
- 🖼️ Automatisch generiertes Open-Graph-Bild aus SVG (`sharp`)
- 📱 Vollständig responsives Layout
- 🧩 Wiederverwendbare Komponenten (`Layout`, `Header`, `Footer`, `ContentCard`, `CategoryCard`, `Badge`, `PageHeader`, `Breadcrumb`, `CTA`, `DetailBox`, `LanguageSwitcher`)

## Projektstruktur

```
programmatic-seo/
├── astro.config.mjs
├── package.json
├── wrangler.toml
├── public/
│   ├── favicon.svg
│   ├── og-default.svg
│   └── og-default.png
├── scripts/
│   ├── generate-og.mjs      # SVG -> PNG für Open Graph
│   └── validate-data.js     # prüft Datendateien und Slugs
└── src/
    ├── components/
    ├── data/
    │   ├── apis.json
    │   ├── alternatives.json
    │   └── workflows.json
    ├── i18n/
    │   ├── content.ts
    │   ├── ui.ts
    │   └── utils.ts
    ├── layouts/
    │   └── Layout.astro
    ├── lib/
    │   ├── content.ts
    │   ├── schema.ts
    │   ├── site.ts
    │   └── tools.ts
    ├── pages/
    │   ├── 404.astro
    │   ├── index.astro
    │   ├── robots.txt.ts
    │   ├── [lang]/
    │   │   ├── index.astro
    │   │   ├── imprint.astro
    │   │   ├── privacy.astro
    │   │   ├── apis/
    │   │   ├── alternatives/
    │   │   └── workflows/
    │   ├── apis/[...slug].astro
    │   ├── alternatives/[...slug].astro
    │   └── workflows/[...slug].astro
    └── styles/
        └── global.css
```

## Befehle

| Befehl              | Beschreibung                                        |
| ------------------- | --------------------------------------------------- |
| `npm install`       | Abhängigkeiten installieren                         |
| `npm run dev`       | Dev-Server unter `http://localhost:4321`            |
| `npm run validate`  | Datendateien und Slug-Eindeutigkeit prüfen          |
| `npm run enrich:alternatives` | Alternativen-Strings per OpenRouter-LLM anreichern |
| `npm run og:generate` | Open-Graph-PNG aus `public/og-default.svg` erzeugen |
| `npm run build`     | Produktions-Build nach `./dist/` (inkl. OG-Bild)    |
| `npm run preview`   | Produktions-Build lokal testen                      |
| `npm run deploy`    | Build erstellen und auf Cloudflare Pages deployen   |

## Inhalte erweitern

Die Inhalte liegen zentral in `src/data/`:

- `apis.json` – API-Einträge
- `alternatives.json` – Alternativen-Vergleiche
- `workflows.json` – Workflow-Anleitungen

Neuen Eintrag hinzufügen, eindeutigen `slug` setzen – die dynamischen Routen (`getStaticPaths`) erzeugen automatisch die passenden Seiten für alle Sprachen. Anschließend `npm run validate` ausführen.

Übersetzungen für UI-Texte und redaktionelle Inhalte liegen in `src/i18n/ui.ts` bzw. `src/i18n/content.ts`.

## Alternativen anreichern

Einige Alternativen-Einträge enthalten in `details.alternatives` nur Tool-Namen als Strings. Das Skript [`scripts/enrich-alternatives.mjs`](scripts/enrich-alternatives.mjs) ergänzt diese über die **OpenRouter-API** um `description`, `pros`, `cons`, `bestFor` und `url` – reiche Datensätze und bestehende Objekte bleiben unangetastet.

```bash
export OPENROUTER_API_KEY="sk-or-..."
npm run enrich:alternatives -- --dry-run          # Vorschau ohne API-Calls
npm run enrich:alternatives -- --limit=3          # nur 3 Datensätze
npm run enrich:alternatives -- --only=mailchimp-alternatives,trello-alternatives
npm run enrich:alternatives                       # alle Kandidaten anreichern
```

Weitere Optionen: `--model=openai/gpt-4o-mini`, `--concurrency=3`, `--no-cache`. Ergebnisse werden in `.cache/enrich-alternatives.json` zwischengespeichert; die Datendatei wird atomar geschrieben. Danach `npm run validate` und `npm run build` ausführen.

## Branding & SEO

Globale Werte (Name, Domain, Twitter-Handle, Standard-OG-Bild) werden zentral in `src/lib/site.ts` gepflegt. Die Produktions-Domain steht zusätzlich in `astro.config.mjs` (`site`) und wird für Canonical-URLs und die Sitemap verwendet.

## Deployment

Das Projekt ist für **Cloudflare Pages** vorbereitet (`wrangler.toml`). Nach dem Login via `wrangler login`:

```bash
npm run deploy:init   # einmalig: Pages-Projekt anlegen
npm run deploy        # Build + Deployment
```
