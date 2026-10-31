# Newsletter Worker

Vollautomatische E-Mail-Erfassung für FlowMatrix und die Compliance-Subdomain.
Der Worker nimmt Anmeldungen entgegen, filtert Bots, begrenzt Missbrauch und
schreibt Kontakte in MailerLite (Double-Opt-in). Ohne MailerLite-Key werden
Anmeldungen verlustfrei in Cloudflare KV zwischengespeichert und später
automatisch synchronisiert.

## Endpunkte

| Methode | Pfad         | Zweck                                      |
| ------- | ------------ | ------------------------------------------ |
| `POST`  | `/subscribe` | Anmeldung `{ email, consent, source }`     |
| `GET`   | `/health`    | Status (MailerLite/KV konfiguriert?)       |

## Einrichtung

```bash
cd worker/newsletter

# 1. KV-Namespace anlegen und ID in wrangler.toml eintragen
npx wrangler kv namespace create NEWSLETTER_KV

# 2. MailerLite-API-Key als Secret setzen
npx wrangler secret put MAILERLITE_API_KEY

# 3. Gruppen-ID in wrangler.toml eintragen (MAILERLITE_GROUP_ID)

# 4. Deployen
npx wrangler deploy
```

Danach in beiden Astro-Projekten `PUBLIC_NEWSLETTER_URL` auf die Worker-URL
setzen, z. B. `https://flowmatrix-newsletter.pumukel75198.workers.dev`.

## MailerLite-Automationen (einmalig, danach vollautomatisch)

1. **Double-Opt-in** in der Gruppe aktivieren: MailerLite sendet die
   Bestätigungsmail automatisch.
2. **Welcome-Automation** anlegen: Trigger „Subscriber joins group“ →
   Willkommensmail mit den beliebtesten Workflows.
3. **RSS-zu-E-Mail-Automation** (optional): MailerLite kann den
   FlowMatrix-RSS-Feed (`https://flowmatrix.dev/insights/rss.xml`) abonnieren
   und neue Artikel automatisch als Newsletter versenden.

Alternativ übernimmt `scripts/send-newsletter.mjs` den Versand vollständig
über die MailerLite-Campaign-API (siehe GitHub Action `newsletter.yaml`).

## Fallback ohne MailerLite

Anmeldungen landen unter `sub:<sha256(email)>` in KV. Sobald der API-Key
gesetzt ist, überträgt `scripts/sync-newsletter.mjs` alle wartenden Kontakte
automatisch – ohne manuellen Eingriff.
