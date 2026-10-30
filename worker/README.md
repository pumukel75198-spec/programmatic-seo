# Besucherzähler (Cloudflare Worker + KV)

Globaler, DSGVO-freundlicher Besucherzähler für den Footer der Seite.
Es werden **keine personenbezogenen Daten** (IP, User-Agent, Cookies) gespeichert –
lediglich ein ganzzahliger Gesamtzähler im KV-Key `total`.

## Endpunkte

| Methode | Pfad     | Beschreibung                          |
|---------|----------|---------------------------------------|
| `GET`   | `/count` | Liest den aktuellen Zählerstand.      |
| `POST`  | `/hit`   | Inkrementiert den Zähler um 1.        |
| `OPTIONS` | `*`    | CORS-Preflight.                       |

Antwortformat: `{ "count": 1234 }`

## Einmalige Einrichtung

1. **KV-Namespace anlegen**

   ```bash
   cd worker
   npx wrangler kv namespace create VISITOR_COUNTER
   ```

   Die ausgegebene `id` in [`wrangler.toml`](./wrangler.toml) bei
   `[[kv_namespaces]] → id` eintragen (Platzhalter `REPLACE_WITH_KV_NAMESPACE_ID`).

2. **Worker deployen**

   ```bash
   cd worker
   npx wrangler deploy
   ```

   Notiere die ausgegebene URL, z. B.
   `https://flowmatrix-visitor-counter.<subdomain>.workers.dev`.

3. **Astro-Umgebung konfigurieren**

   In der Produktionsumgebung (Cloudflare Pages → Settings → Environment variables)
   sowie lokal in `.env` setzen:

   ```bash
   PUBLIC_VISITOR_COUNTER_URL=https://flowmatrix-visitor-counter.<subdomain>.workers.dev
   ```

   Ohne gesetzte Variable bleibt der Zähler im Footer automatisch ausgeblendet.

## Verhalten im Frontend

- Beim ersten Seitenaufruf einer Session wird `POST /hit` gesendet und der Zähler erhöht.
- Weitere Aufrufe derselben Session nutzen `GET /count` (kein Doppelzählen).
- Bei Netzwerk-/CORS-Fehlern wird der Zähler ausgeblendet, die Seite bleibt unberührt.

## Hinweis zur Konsistenz

Cloudflare KV ist eventually consistent. Bei sehr hoher Parallelität können einzelne
Inkremente verloren gehen. Für einen reinen Anzeige-Zähler ist das unkritisch.
Für exakte Zählung wäre ein Durable Object die passende Alternative.
