# Programmatic SEO Hub

Ein modernes **Astro + Tailwind CSS**-Projekt für Programmatic SEO mit drei dynamischen Routen-Kategorien und einem dunklen, responsiven UI.

## Features

- ⚡️ **Astro 7** mit statischem Output (SSG)
- 🎨 **Tailwind CSS 4** über die offizielle Vite-Integration
- 🌙 **Dark Mode** als Standard-Design
- 🧭 Drei dynamische Routen: **APIs**, **Alternativen**, **Workflows**
- 🔍 SEO-freundlich: Canonical-URLs, Open-Graph- und Twitter-Meta-Tags
- 📱 Vollständig responsives Layout
- 🧩 Wiederverwendbare Komponenten (`Layout`, `Header`, `Footer`, `ContentCard`, `CategoryCard`, `Badge`, `PageHeader`)

## Projektstruktur

```
programmatic-seo/
├── astro.config.mjs
├── package.json
├── public/
└── src/
    ├── components/
    │   ├── Badge.astro
    │   ├── CategoryCard.astro
    │   ├── ContentCard.astro
    │   ├── Footer.astro
    │   ├── Header.astro
    │   └── PageHeader.astro
    ├── data/
    │   ├── apis.ts
    │   ├── alternativen.ts
    │   └── workflows.ts
    ├── layouts/
    │   └── Layout.astro
    ├── pages/
    │   ├── 404.astro
    │   ├── index.astro
    │   ├── apis/
    │   │   ├── index.astro
    │   │   └── [slug].astro
    │   ├── alternativen/
    │   │   ├── index.astro
    │   │   └── [slug].astro
    │   └── workflows/
    │       ├── index.astro
    │       └── [slug].astro
    └── styles/
        └── global.css
```

## Befehle

| Befehl            | Beschreibung                                  |
| ----------------- | --------------------------------------------- |
| `npm install`     | Abhängigkeiten installieren                   |
| `npm run dev`     | Dev-Server unter `http://localhost:4321`      |
| `npm run build`   | Produktions-Build nach `./dist/`              |
| `npm run preview` | Produktions-Build lokal testen                |

## Inhalte erweitern

Die Inhalte liegen zentral in `src/data/`:

- `apis.ts` – Einträge vom Typ `ApiEntry`
- `alternativen.ts` – Einträge vom Typ `AlternativeEntry`
- `workflows.ts` – Einträge vom Typ `WorkflowEntry`

Neuen Eintrag hinzufügen, `slug` setzen – die dynamische Route (`getStaticPaths`) erzeugt automatisch die passende Seite.

## Vor dem Deployment

Passe in `astro.config.mjs` die `site`-URL auf deine Produktions-Domain an. Das sorgt für korrekte Canonical-URLs und ist Voraussetzung für eine spätere Sitemap-Integration.
