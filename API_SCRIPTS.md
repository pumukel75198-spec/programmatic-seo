# API Starter Scripts

Every API listed on [flowmatrix.dev](https://flowmatrix.dev) ships with a
downloadable, dependency-free Python starter script. The scripts are generated
automatically from [`src/data/apis.json`](./src/data/apis.json) and published as
static files under `public/api-scripts/`.

## What gets generated

For each API (`<slug>`):

```
public/api-scripts/<slug>/<slug>.py      executable starter script
public/api-scripts/<slug>/README.md      short usage guide
public/api-scripts/<slug>/metadata.json  machine-readable metadata
public/api-scripts/index.json            manifest of all scripts
public/api-scripts/README.md             overview page
```

Each script exposes three modes:

| Mode | Network | Credentials | Purpose |
| --- | --- | --- | --- |
| `--dry-run` (default) | no | no | Print method, endpoint and headers without sending anything. |
| `--smoke` | yes | no | Check that the endpoint answers (2xx–4xx = reachable). |
| `--live` | yes | yes (`KEY_ENV`) | Send a real request. |

The scripts only use the Python standard library (Python 3.8+), so users can
download and run them without installing dependencies.

## Commands

```bash
# Regenerate every script (also runs automatically in `prebuild`)
npm run api-scripts:generate

# Syntax + dry-run (no network) – safe for CI and offline work
npm run api-scripts:test:offline

# Syntax + dry-run + endpoint smoke test (network required)
npm run api-scripts:test

# Include real calls (requires the matching API keys in the environment)
npm run api-scripts:test -- --live

# Isolate a single script
npm run api-scripts:test -- --only=openai-whisper-api --verbose
```

Useful flags for the test harness:

- `--offline` – skip the network smoke test.
- `--lenient` – treat network errors as warnings (useful on flaky networks).
- `--concurrency=<n>` – parallel checks (default: 6).
- `--timeout=<sec>` – per-request timeout (default: 12).
- `--no-generate` – test the existing files without regenerating them.

## Adding or fixing an endpoint

`src/data/apis.json` is the source of truth. Some legacy entries have no
`details.endpoint`, and some endpoints contain placeholders such as
`{project-ref}`. Add an override in
[`src/data/api-endpoints.json`](./src/data/api-endpoints.json):

```json
{
  "my-api-slug": {
    "endpoint": "https://api.example.com/v1/things",
    "method": "GET",
    "auth": "bearer",
    "keyEnv": "EXAMPLE_API_KEY",
    "headers": { "Accept": "application/json" }
  }
}
```

Supported `auth` styles: `bearer`, `header` (with `authHeader`), `token`,
`basic`, `query` (with `authParam`), `url-token`, `bot`, `aws-sigv4`, `digest`
and `none`.

- Endpoints without placeholders are included in the smoke test.
- Endpoints with placeholders (`{...}` or `<...>`) are generated but skipped by
  the smoke test, because the real host/value depends on the user's account.
- APIs that require request signing (AWS SigV4, Digest) are generated with a
  warning; use the official SDK for `--live`.

## CI

[`.github/workflows/api-scripts-test.yaml`](./.github/workflows/api-scripts-test.yaml)
runs the offline checks on every push/PR that touches the API data or scripts,
and the full smoke test weekly and on manual dispatch.

## Security

- Secrets are never written to the generated files. Scripts read the key from
  the environment variable named in `KEY_ENV`.
- `--dry-run` masks credentials in the printed headers.
- The smoke test sends no credentials.
