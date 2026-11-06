# FlowMatrix

Ein **Astro + Tailwind CSS**-Projekt für Programmatic SEO mit drei dynamischen
Routen-Kategorien, Mehrsprachigkeit und einem dunklen, responsiven UI.

## Features

- ⚡️ **Astro 7** mit statischem Output (SSG)
- 🎨 **Tailwind CSS 4** über die offizielle Vite-Integration
- 🌙 **Dark Mode** als Standard-Design
- 🧭 Drei dynamische Routen: **APIs**, **Alternativen**, **Workflows**
- 🌍 **2 Sprachen** (`en`, `de`) mit lokalisierten Routen
- 🔍 SEO-freundlich: Canonical-URLs, Open-Graph/Twitter, JSON-LD, Sitemap, `robots.txt`
- 🖼️ Automatisch generiertes Open-Graph-Bild aus SVG (`sharp`)

## Projektstruktur

```
programmatic-seo/
├── pipeline/                 # EINZIGE Content-/PDF-/QS-Pipeline
│   ├── config.py             # Preise, Import-Whitelist, Blacklist, Pfade
│   ├── schemas.py            # Strikte Pydantic-Modelle
│   ├── prompts.py            # Einzige System-Prompts
│   ├── llm_client.py         # OpenRouter (Standardbibliothek)
│   ├── validator.py          # Harter Gatekeeper (AST/Englisch/Tools/Domains)
│   ├── pdf_renderer.py       # Dynamischer PDF-Renderer (variable Seitenzahl)
│   ├── bundle_builder.py     # Implementation-Kits (.zip, PDF + Code)
│   └── run_batch.py          # Einziger Entry Point
├── scripts/                  # Nur noch Build-Infra, Insights, Newsletter
├── src/
│   ├── data/                 # apis.json, alternatives.json, workflows.json
│   ├── i18n/, layouts/, lib/, pages/, components/
├── worker/                   # download-gate, newsletter, visitor-counter
├── public/
└── astro.config.mjs
```

## Befehle

| Befehl                                             | Beschreibung                                                |
| -------------------------------------------------- | ----------------------------------------------------------- |
| `npm install`                                      | Abhängigkeiten installieren                                 |
| `npm run dev`                                      | Dev-Server unter `http://localhost:4321`                    |
| `npm run build`                                    | Produktions-Build nach `./dist/`                            |
| `npm run preview`                                  | Produktions-Build lokal testen                              |
| `npm run pipeline:run -- <args>`                   | Unified Pipeline (`.venv/bin/python -m pipeline.run_batch`) |
| `npm run generate:batch -- --workflows 3 --apis 4` | Content-Batch über die Pipeline                             |
| `npm run insights:generate`                        | RSS-Feeds einlesen und Insights per LLM erzeugen            |
| `npm run og:generate`                              | Open-Graph-PNG aus `public/og-default.svg` erzeugen         |
| `npm run deploy`                                   | Build + Deployment nach Cloudflare Pages                    |

## Inhalte erzeugen – die einzige Pipeline

Alle Workflows, APIs, Alternativen, PDFs und API-Skripte werden ausschließlich
über [`pipeline/run_batch.py`](pipeline/run_batch.py) erzeugt, validiert und
bereitgestellt. Setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -r pipeline/requirements.txt
```

Lauf:

```bash
# Test: 1 Workflow + 1 API-Skript (ohne Build/Upload/Deploy)
.venv/bin/python -m pipeline.run_batch \
  --only-workflow automated-api-error-reporting \
  --only-api sentry-performance-api \
  --skip-build --skip-upload --skip-deploy

# Batch: 3 Workflows, 4 APIs, 2 Alternativen
.venv/bin/python -m pipeline.run_batch --workflows 3 --apis 4 --alternatives 2
```

**Verbindliche Regeln** (siehe [`pipeline/README.md`](pipeline/README.md)):

- Preise: Beginner **9,99 €**, Intermediate **19,99 €**, Advanced/Expert **34,99 €**, API-Skript **29,99 €**; `7.99` ist verboten.
- PDFs: **dynamische Seitenzahl** (Cover, Overview, Setup+Glossary, N Steps, Checklist, Troubleshooting+Resources). Die Step-Anzahl richtet sich nach der echten Komplexität (3–8), nicht nach einer festen Vorgabe; `Page X of Y` wird nach dem Rendern berechnet.
- **100 % Englisch** in allen generierten PDFs und API-Skripten (Text, Kommentare, Docstrings, Glossar, Checklisten, Troubleshooting).
- Generierter Code: **nur Python-Standardbibliothek** (AST-geprüft); `random` und Dummy-Daten sind in Workflow-Snippets verboten, stattdessen echter Datenfluss von Step 1 bis N.
- **Live-Domainprüfung**: Jede Domain/URL wird live geprüft (HEAD/GET, 8 s Timeout, SSL). Platzhalter wie `https://<your-project>.supabase.co` werden auf ihre offizielle Basis-Domain abgebildet. Ist eine Domain nicht erreichbar, wird der Workflow verworfen und automatisch ein neues Thema generiert.
- **Tool-Konsistenz**: Jedes gelistete Tool muss in den Steps vorkommen und eine vollständige URL in `resources` haben.
- **Zeitstempel & Disclaimer**: Jeder Datensatz speichert `created_and_verified_at` (`YYYY-MM-DD HH:MM UTC`); das PDF zeigt ihn auf Cover und Overview und enthält den Link-Validitäts-Hinweis.
- Self-Healing: Validator-Fehler gehen als Feedback an das LLM (max. 3 Versuche); defekte Snippets werden isoliert repariert. Danach wird verworfen – niemals gespeichert, hochgeladen oder deployed.

## Insights

[`scripts/generate-insights.mjs`](scripts/generate-insights.mjs) liest
[`src/data/feeds.json`](src/data/feeds.json), erzeugt Artikel über OpenRouter und
schreibt [`src/data/insights.json`](src/data/insights.json). Der Seed-Bestand
liegt in `insights-seed.json`.

## Monetarisierung

- Lemon-Squeezy-Checkout über `PUBLIC_LEMON_*`-Variablen.
- Affiliate-Parameter zentral in [`src/lib/tools.ts`](src/lib/tools.ts).
- Premium-Workflow-PDFs: 4,99 / 12,99 / 21,99 €.
- API-Skripte: 19,99 €.
- Download-Gate-Worker prüft Lizenzschlüssel und streamt PDFs aus R2.

### Umgebungsvariablen

Siehe [`.env.example`](.env.example). Wichtig:

```bash
PUBLIC_LEMON_CHECKOUT_URL=...
PUBLIC_LEMON_WORKFLOW_CHECKOUT_BEGINNER=...
PUBLIC_LEMON_WORKFLOW_CHECKOUT_INTERMEDIATE=...
PUBLIC_LEMON_WORKFLOW_CHECKOUT_ADVANCED=...
PUBLIC_LEMON_WORKFLOW_CHECKOUT_EXPERT=...
PUBLIC_AFFILIATE_REF=flowmatrix
```

## Deployment

```bash
npm run deploy:init   # einmalig: Pages-Projekt anlegen
npm run deploy        # Build + Deployment
```

Die Produktions-Domain steht in `astro.config.mjs` (`site`) und
`src/lib/site.ts`.
