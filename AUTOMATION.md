# Vollautomatische Pipeline

Alle Inhalte, Deployments, Newsletter und Indexierung laufen ohne manuellen
Eingriff. Dieses Dokument beschreibt, was automatisch passiert und welche
einmaligen Einrichtungsschritte nötig sind.

## Was automatisch läuft

| Zeitplan | Workflow | Ergebnis |
| --- | --- | --- |
| alle 3 Tage, 06:00 UTC | `generate-content.yaml` | ~10 neue APIs/Alternatives/Workflows, PDFs, Python-Skripte, Validierung, KV-Upload, Build, Deploy, IndexNow |
| täglich 06:00 & 18:00 Berlin | `insights.yml` | 2 neue Insights aus kuratierten Feeds, Build, Deploy, IndexNow |
| täglich 07:00 UTC | `auto-blog.yaml` (Compliance) | 1 neuer Compliance-/AI-Act-Artikel, Build, Deploy |
| montags 08:00 UTC | `newsletter.yaml` | wartende Anmeldungen zu MailerLite, automatischer Newsletter-Versand |
| bei jedem Push | `deploy.yaml` | Validierung, Build, Deploy, IndexNow |

## Einmalige Einrichtung

### 1. Newsletter-Worker deployen

```bash
cd worker/newsletter
npx wrangler kv namespace create NEWSLETTER_KV
# ID in wrangler.toml eintragen
npx wrangler secret put MAILERLITE_API_KEY
# MAILERLITE_GROUP_ID in wrangler.toml eintragen
npx wrangler deploy
```

### 2. GitHub-Secrets und -Variablen setzen

**Secrets** (Settings → Secrets and variables → Actions):

| Name | Zweck |
| --- | --- |
| `OPENROUTER_API_KEY` | Content-Generierung (bereits vorhanden) |
| `CLOUDFLARE_API_TOKEN` | Deploy + KV (bereits vorhanden) |
| `CLOUDFLARE_ACCOUNT_ID` | Deploy + KV (bereits vorhanden) |
| `MAILERLITE_API_KEY` | Newsletter-Versand und Kontakt-Sync |

**Variablen:**

| Name | Beispiel |
| --- | --- |
| `PUBLIC_NEWSLETTER_URL` | `https://flowmatrix-newsletter.<subdomain>.workers.dev` |
| `NEWSLETTER_KV_NAMESPACE_ID` | ID aus Schritt 1 |
| `MAILERLITE_GROUP_ID` | Gruppen-ID aus MailerLite |
| `MAILERLITE_FROM_EMAIL` | verifizierte Absenderadresse |
| `MAILERLITE_FROM_NAME` | `FlowMatrix` |
| `PUBLIC_LEMON_*_CHECKOUT_URL` | echte Lemon-Squeezy-URLs (optional) |

### 3. MailerLite-Automationen (einmalig)

1. Double-Opt-in in der Gruppe aktivieren.
2. Welcome-Automation: Trigger „Subscriber joins group“.
3. Optional: RSS-Automation auf `https://flowmatrix.dev/insights/rss.xml`.

Danach werden Bestätigungs- und Willkommensmails automatisch versendet.
Eingehende Antworten landen im MailerLite-Postfach und müssen nicht manuell
beantwortet werden; die Automationen laufen unabhängig davon weiter.

## Fallback ohne MailerLite

Anmeldungen werden im Newsletter-Worker unter `sub:<sha256(email)>` in KV
gespeichert. Sobald `MAILERLITE_API_KEY` gesetzt ist, überträgt
`scripts/sync-newsletter.mjs` sie beim nächsten Newsletter-Lauf automatisch.

## Manuelle Befehle (nur bei Bedarf)

```bash
npm run newsletter:preview   # HTML-Vorschau ohne Versand
npm run newsletter:send      # sofort versenden
npm run newsletter:sync      # KV → MailerLite
npm run indexnow             # URLs manuell melden
```
