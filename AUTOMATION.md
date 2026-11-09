# Vollautomatische Pipeline

Alle Inhalte, Deployments, Newsletter und Indexierung laufen ohne manuellen
Eingriff. Die Content-Generierung läuft ausschließlich über die Unified Pipeline
[`pipeline/run_batch.py`](pipeline/run_batch.py).

## Was automatisch läuft

| Zeitplan               | Workflow                | Ergebnis                                                                                                                                               |
| ---------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| alle 3 Tage, 06:00 UTC | `generate-content.yaml` | Batch über die Unified Pipeline (APIs/Alternatives/Workflows, PDFs, Python-Skripte), harte Validierung, R2-Upload, Build, Deploy, IndexNow, Newsletter |
| Mo & Do, 06:00 Berlin  | `insights.yml`          | 2 neue, relevanzgeprüfte Insights (≥ 700 Wörter), Volltext-Archiv, Build, Deploy, IndexNow                                                             |
| montags 08:00 UTC      | `newsletter.yaml`       | wartende Anmeldungen zu MailerLite, automatischer Versand                                                                                              |
| bei jedem Push         | `deploy.yaml`           | Typecheck, Format, Unit-Tests, Build, E2E, Deploy, IndexNow                                                                                            |

## Einmalige Einrichtung

### 1. Python-Pipeline in CI

`generate-content.yaml` installiert automatisch:

```bash
pip install -r pipeline/requirements.txt
python -m pipeline.run_batch --workflows 4 --apis 4 --alternatives 3 --skip-deploy
```

### 2. Newsletter-Worker deployen

```bash
cd worker/newsletter
npx wrangler kv namespace create NEWSLETTER_KV
# ID in wrangler.toml eintragen
npx wrangler secret put MAILERLITE_API_KEY
npx wrangler deploy
```

### 3. GitHub-Secrets und -Variablen setzen

**Secrets:** `OPENROUTER_API_KEY`, `CLOUDFLARE_API_TOKEN`,
`CLOUDFLARE_ACCOUNT_ID`, `MAILERLITE_API_KEY`

**Variablen:** `PUBLIC_NEWSLETTER_URL`, `NEWSLETTER_KV_NAMESPACE_ID`,
`MAILERLITE_GROUP_ID`, `MAILERLITE_FROM_EMAIL`, `MAILERLITE_FROM_NAME`,
`PUBLIC_LEMON_*_CHECKOUT_URL`

### 4. MailerLite-Automationen (einmalig)

1. Double-Opt-in in der Gruppe aktivieren.
2. Welcome-Automation: Trigger „Subscriber joins group“.
3. Optional: RSS-Automation auf `https://flowmatrix.dev/insights/rss.xml`.

## Harte Gates

Kein Inhalt erreicht JSON, R2 oder Cloudflare Pages, wenn
[`pipeline/validator.py`](pipeline/validator.py) nicht 100 % besteht:

- `ast.parse()` + `sys.stdlib_module_names` für jeden Codeblock
- Mock-Execution der API-Skripte
- Blacklist (u. a. „File > New“, „Make a Zap“, „Adobe XD“, „7.99“)
- Dubletten-Schutz
- Live-Erreichbarkeit aller verlinkten Domains
- Self-Healing (max. 3 Versuche), sonst verwerfen und loggen

## Manuelle Befehle (nur bei Bedarf)

```bash
.venv/bin/python -m pipeline.run_batch --workflows 3
npm run newsletter:preview   # HTML-Vorschau ohne Versand
npm run newsletter:send      # sofort versenden
npm run newsletter:sync      # KV → MailerLite
npm run indexnow             # URLs manuell melden
```
