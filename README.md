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
| `npm run insights:generate` | RSS-Feeds einlesen und Insights-Artikel per LLM erzeugen |
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

## Insights automatisch erzeugen

[`scripts/generate-insights.mjs`](scripts/generate-insights.mjs) liest die RSS-/Atom-Feeds aus [`src/data/feeds.json`](src/data/feeds.json), erkennt neue Einträge und lässt über die **OpenRouter-API** eigenständige Artikel schreiben. Das Skript wählt automatisch den thematisch passendsten Workflow aus [`src/data/workflows.json`](src/data/workflows.json) und setzt einen kontextbezogenen internen Link. Die Ergebnisse landen in [`src/data/insights.json`](src/data/insights.json); Astro generiert daraus statische Seiten unter `/insights/[slug]`.

```bash
npm run insights:generate -- --dry-run            # Feeds prüfen, keine API-Calls
npm run insights:generate -- --limit=3            # 3 neue Artikel
npm run insights:generate -- --feed=TechCrunch    # nur einen Feed
npm run insights:generate -- --lang=de            # deutschsprachige Artikel
```

Weitere Optionen: `--max-age-days=14`, `--model=openai/gpt-4o-mini`, `--concurrency=2`. Bereits verarbeitete Quellen werden über ihre URL erkannt und nicht erneut erzeugt. Nach dem Lauf `npm run build` ausführen.

### Mindestbestand & Fallback

Der Feed zeigt immer mindestens **6 Beiträge**. Reichen die generierten Artikel nicht aus, füllt [`src/data/insights-seed.json`](src/data/insights-seed.json) mit kuratierten Evergreen-Artikeln auf. Generierte Artikel haben Vorrang; Seed-Artikel ersetzen nie bestehende Inhalte.

### Automatischer 6-Stunden-Takt

[`.github/workflows/insights.yml`](.github/workflows/insights.yml) läuft per Cron zu **00:00, 06:00, 12:00 und 18:00 Uhr UTC**, generiert bis zu 6 neue Artikel, validiert, baut und committet `src/data/insights.json`. Der anschließende Push löst das bestehende Deploy-Workflow aus.

Voraussetzung im Repository:

- Secret `OPENROUTER_API_KEY` (Settings → Secrets and variables → Actions)
- Optional Variable `OPENROUTER_MODEL` (Default: `openai/gpt-4o-mini`)

Manuell startbar über „Run workflow“ (`workflow_dispatch`).

> Hinweis: Die Insights-Routen liegen bewusst außerhalb der `[lang]`-Struktur. Im statischen Build und in `npm run preview` sind sie unter `/insights/...` erreichbar; der Astro-Dev-Server mit `prefixDefaultLocale` liefert unpräfixierte Routen jedoch mit 404 aus.

## Monetarisierung

### Lemon Squeezy Checkout

[`src/components/LemonButton.astro`](src/components/LemonButton.astro) ist ein wiederverwendbarer, conversion-optimierter Buy-Button. Die Checkout-URL kommt aus der Prop `checkoutUrl` oder aus `PUBLIC_LEMON_CHECKOUT_URL`. Bei gesetzter URL erhält der Link die Klasse `lemonsqueezy-button`; das Overlay-Skript `lemon.js` wird automatisch einmal pro Seite eingebunden.

```astro
---
import LemonButton from "../components/LemonButton.astro";
---

<LemonButton
  label="Get instant access"
  price="One-time purchase"
  productName="FlowMatrix Playbook"
/>
```

Ohne konfigurierte URL rendert die Komponente einen deaktivierten Button („Checkout coming soon“), sodass der Build nie bricht.

### Affiliate-Parameter

Alle Tool-Links laufen über [`src/lib/tools.ts`](src/lib/tools.ts). `getToolLink()` und `linkifyTools()` hängen die Affiliate-Parameter zentral an:

- globaler Default: `PUBLIC_AFFILIATE_REF` (Fallback: `flowmatrix`)
- pro Tool überschreibbar über `affiliateParams`

Bestehende Query-Strings und Hash-Fragmente bleiben erhalten; Parameter werden nicht doppelt angehängt.

### Premium-Workflow-PDFs (4,99 €)

[`scripts/generate-pdfs.mjs`](scripts/generate-pdfs.mjs) erzeugt für jeden Workflow ein PDF in `public/downloads/flowmatrix-<slug>.pdf`:

- Clean Cover mit „FlowMatrix.dev Premium Workflow“
- Übersicht mit Kategorie, Difficulty, Dauer und Use Case
- Ausführliche Step-by-Step-Erklärungen ohne externe Links – alle Informationen stehen direkt im PDF
- Keine Tool- oder Dokumentationslinks; das PDF ist vollständig eigenständig

Das Skript läuft automatisch im `prebuild`-Schritt. Manuell:

```bash
npm run pdf:generate
```

### PDF-Qualitäts-Gatekeeper

[`scripts/validate-pdfs.mjs`](scripts/validate-pdfs.mjs) prüft jedes PDF automatisch vor dem Build:

1. **Inhaltlicher Abgleich** mit `workflows.json` (Titel, Beschreibung, Kategorie, Difficulty, Dauer, Use Case, alle Steps inkl. Actions, Commands, Config, Checkliste und Ergebnis)
2. **Junk-/Halluzinations-Check** (Lorem Ipsum, TODO, Platzhalter, `undefined`, `NaN`, veraltete OpenAI-Endpunkte/-Modelle, `npm init astro`)
3. **Struktur** (mind. 3 Steps, mind. 3 Actions und 2 Checklisten-Punkte pro Step, vollständige Sätze, alle Abschnitte)
4. **Link-Integrität** (Lemon-Squeezy-Checkout-Link und Preis 4,99 €; die Step-Anleitungen selbst enthalten keine externen Links)

Der Check läuft im `prebuild`-Schritt und bricht den Build bei Fehlern mit Exit-Code 1 ab. Manuell:

```bash
npm run pdf:validate
```

### Master-Anleitung pro Step

Jeder Step enthält jetzt:

- `description` – ausführliche Einordnung
- `actions` – konkrete Handlungen mit Klickpfaden/Parametern
- `commands` – echte CLI-/API-/Code-Schnipsel
- `config` – konkrete Umgebungsvariablen/Parameter
- `tools` – interne Zuordnung der benötigten Tools (wird nicht als Link gerendert)
- `checklist` – überprüfbare Punkte
- `expectedResult` – was nach dem Step fertig ist

Fehlende Details lassen sich per LLM ergänzen:

```bash
npm run enrich:workflow-details -- --dry-run
npm run enrich:workflow-details -- --force --only=content-automation
npm run enrich:workflow-details
```

Die Landingpage [`src/pages/[lang]/workflows/[slug].astro`](src/pages/[lang]/workflows/[slug].astro) bindet [`PremiumDownload.astro`](src/components/PremiumDownload.astro) ein:

- Buy-Button mit festem Preis **4,99 €**
- Lemon Squeezy Overlay-Checkout
- Nach erfolgreichem Checkout (`lemon-squeezy:checkout:success`) wird der PDF-Download freigeschaltet und in `localStorage` gemerkt

> Hinweis: Der Unlock ist clientseitig. Für echten Kopierschutz wäre eine serverseitige Verifikation (z. B. Cloudflare Function + Lemon Squeezy API) nötig.

### Umgebungsvariablen

Siehe [`.env.example`](.env.example):

```bash
PUBLIC_LEMON_CHECKOUT_URL=https://your-store.lemonsqueezy.com/checkout/buy/...
PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL=https://your-store.lemonsqueezy.com/checkout/buy/...
PUBLIC_AFFILIATE_REF=flowmatrix
```

## Branding & SEO

Globale Werte (Name, Domain, Twitter-Handle, Standard-OG-Bild) werden zentral in `src/lib/site.ts` gepflegt. Die Produktions-Domain steht zusätzlich in `astro.config.mjs` (`site`) und wird für Canonical-URLs und die Sitemap verwendet.

## Deployment

Das Projekt ist für **Cloudflare Pages** vorbereitet (`wrangler.toml`). Nach dem Login via `wrangler login`:

```bash
npm run deploy:init   # einmalig: Pages-Projekt anlegen
npm run deploy        # Build + Deployment
```
