# www → non-www Redirect (Cloudflare Worker)

Leitet `https://www.flowmatrix.dev/*` permanent (**HTTP 301**) auf
`https://flowmatrix.dev/*` um. Pfad und Query-String bleiben erhalten.

Damit gibt es nur noch einen kanonischen Host und keine doppelten
Host-Signale für Suchmaschinen.

## Deploy

```bash
cd worker/www-redirect
npx wrangler deploy
```

Die Route `www.flowmatrix.dev/*` wird über [`wrangler.toml`](./wrangler.toml)
automatisch registriert.

## Prüfen

```bash
curl -I "https://www.flowmatrix.dev/en/?test=1"
# HTTP/2 301
# location: https://flowmatrix.dev/en/?test=1
```
