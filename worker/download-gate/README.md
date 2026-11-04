# Download-Gate Worker

Schützt die Premium-PDFs hinter einer gültigen Lemon-Squeezy-Lizenz.

## Warum?

Vorher lagen die PDFs unter `public/downloads/` und waren ohne Kauf abrufbar.
Der „Unlock" im Frontend war nur `localStorage` bzw. `?purchased=1` und damit
trivial fälschbar. Dieser Worker löst das:

1. PDFs liegen in einem **privaten R2-Bucket** (nicht im öffentlichen Build).
2. Der Käufer bekommt von Lemon Squeezy einen **Lizenzschlüssel**.
3. `POST /api/validate` prüft den Schlüssel gegen die offizielle
   Lemon-Squeezy-License-API.
4. Bei Gültigkeit wird ein **kurzlebiges, HMAC-signiertes Token** (10 Min)
   ausgestellt.
5. `GET /api/download?token=…&slug=…` prüft das Token und liest das PDF aus
   R2. Ohne gültiges Token kein Zugriff.

## Einrichtung

### 1. R2-Bucket anlegen

```bash
npx wrangler r2 bucket create flowmatrix-downloads
```

Der Bucket-Name ist in [`wrangler.toml`](./wrangler.toml) unter
`[[r2_buckets]] → bucket_name` hinterlegt.

### 2. Secrets setzen

```bash
# Zufälliger, langer String (z. B. `openssl rand -hex 32`)
npx wrangler secret put DOWNLOAD_TOKEN_SECRET

# Produkt-Mapping (JSON, siehe unten)
npx wrangler secret put LEMON_PRODUCT_MAP
```

### 3. Produkt-Mapping

`LEMON_PRODUCT_MAP` ordnet Lemon-Squeezy-Produkt-/Varianten-IDs den erlaubten
PDF-Slugs zu. Die IDs findest du im Lemon-Squeezy-Dashboard bzw. in der
Antwort der License-API (`meta.variant_id`, `meta.product_id`).

```json
{
  "variant:123456": { "type": "single", "slugs": ["content-automation"] },
  "product:789012": { "type": "bundle", "slugs": ["*"] },
  "product:345678": { "type": "subscription", "slugs": ["*"] }
}
```

- `slugs: ["*"]` = Zugriff auf **alle** PDFs (Bundle/Abo).
- Ein Einzel-PDF-Produkt listet genau seinen Slug.
- Solange noch keine echten IDs bekannt sind, kann für Tests
  `ALLOW_ALL_ON_VALID = "1"` in `wrangler.toml` gesetzt werden. **Danach
  wieder auf `"0"` stellen.**

### 4. Worker deployen

```bash
cd worker/download-gate
npx wrangler deploy
```

### 5. PDFs nach R2 hochladen

Die PDFs werden lokal nach `private/downloads/` generiert (nicht mehr nach
`public/downloads/`). Upload z. B. mit:

```bash
npm run pdf:upload
```

oder manuell pro Datei:

```bash
npx wrangler r2 object put flowmatrix-downloads/content-automation.pdf \
  --file=private/downloads/flowmatrix-content-automation.pdf \
  --content-type=application/pdf --remote
```

> Hinweis: Der Key im Bucket ist `<slug>.pdf` (ohne `flowmatrix-`-Präfix),
> weil der Worker genau danach sucht.

### 6. Astro-Umgebung

In `.env` bzw. in den GitHub-Actions-Variablen:

```bash
PUBLIC_DOWNLOAD_GATE_URL=https://flowmatrix-download-gate.<subdomain>.workers.dev
```

## Endpunkte

| Methode | Pfad            | Zweck                                    |
| ------- | --------------- | ---------------------------------------- |
| `POST`  | `/api/validate` | Lizenz prüfen, Download-Token ausstellen |
| `GET`   | `/api/download` | PDF mit gültigem Token aus R2 lesen      |
| `GET`   | `/api/health`   | Health-Check                             |

### `POST /api/validate`

```json
{ "licenseKey": "XXXX-XXXX-XXXX-XXXX", "slug": "content-automation" }
```

Antwort bei Erfolg:

```json
{
  "valid": true,
  "product": { "type": "single", "slugs": ["content-automation"] },
  "token": "…",
  "expiresAt": "2026-10-30T17:35:00.000Z",
  "downloadUrl": "https://…/api/download?token=…&slug=content-automation"
}
```

## Sicherheit

- Lizenzschlüssel werden **nicht** gespeichert; nur ein SHA-256-Hash fließt in
  das Token ein.
- Tokens sind HMAC-signiert und laufen nach 10 Minuten ab.
- PDFs sind ohne gültiges Token nicht erreichbar.
- CORS ist auf `flowmatrix.dev` (und lokale Entwicklung) beschränkt.
