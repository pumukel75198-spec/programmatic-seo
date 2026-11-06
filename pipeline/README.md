# FlowMatrix Unified Pipeline

Single Source of Truth for content generation, validation and delivery.
Everything runs through `pipeline/run_batch.py` – there is no alternative code
path or legacy fallback. All old JS generators, PDF layouts, validators and
batch scripts have been removed.

## Modules

| File                | Responsibility                                                                                                                                      |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `config.py`         | Paths, binding prices, import whitelist, blacklist, variable step bounds, timestamp/disclaimer, placeholder→base-domain map                         |
| `schemas.py`        | Strict Pydantic models (variable step count, `resources`, `created_and_verified_at`)                                                                |
| `prompts.py`        | The only valid LLM system prompts (100 % English, didactic depth, tool consistency, correct API patterns)                                           |
| `llm_client.py`     | OpenRouter client (standard library, retries, backoff)                                                                                              |
| `validator.py`      | Hard gatekeeper: AST per step + concatenated, stdlib imports, mock execution, blacklist, dummy/random ban, tool consistency, live HTTP reachability |
| `pdf_renderer.py`   | The only PDF layout – dynamic, content-driven page count, H1 title, timestamp, link disclaimer                                                      |
| `bundle_builder.py` | Builds the `<slug>-kit.zip` Implementation Kits (workflow + API)                                                                                    |
| `run_batch.py`      | Single entry point: generate → validate → retry → store → PDF → kit → R2 → build → deploy, with automatic topic replacement on domain failure       |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r pipeline/requirements.txt
```

## Run

```bash
# Test one workflow + one API script, no build/upload/deploy
.venv/bin/python -m pipeline.run_batch \
  --only-workflow social-listening \
  --only-api sentry-performance-api \
  --skip-build --skip-upload --skip-deploy

# Full batch (3 workflows, 4 APIs, 2 alternatives) incl. build + deploy
.venv/bin/python -m pipeline.run_batch --workflows 3 --apis 4 --alternatives 2
```

## Binding rules

- **100 % English** in every generated PDF and API script (text, comments,
  docstrings, glossary, checklists, troubleshooting).
- **Variable step and page count** – driven by real technical complexity
  (`MIN_STEPS`..`MAX_STEPS`, no fixed 5-step / 10-page rule). `Page X of Y` is
  computed dynamically after rendering.
- Prices: Beginner `€9.99`, Intermediate `€19.99`, Advanced/Expert `€34.99`,
  API script `€29.99`. `7.99` is forbidden everywhere.
- Every workflow and API script also ships as an **Implementation Kit**
  (`<slug>-kit.zip`) with `blueprint.pdf`, `workflow.py`, `.env.example`,
  `mock_data.json`, `schema.sql`, `requests.http`,
  `AI_IMPLEMENTATION_PROMPT.md` and `README.md` (API kits: `api_client.py`,
  `test_mock.py`, `.env.example`, `requests.http`,
  `AI_INTEGRATION_PROMPT.md`, `api-cheatsheet.pdf`, `README.md`).
- Generated code uses the Python standard library only (AST-checked).
  `random` is forbidden in workflow snippets; a real data flow from step 1 to
  step N is required.
- **Live domain check**: every domain/URL is tested (HEAD/GET, 8 s timeout,
  SSL verification). Placeholders such as `https://<your-project>.supabase.co`
  are mapped to their official base domain. If any domain is unreachable, the
  workflow is discarded and a brand-new topic is generated automatically.
- **Tool consistency**: every listed tool must be used in the steps and have a
  full URL in `resources`.
- **Timestamp + disclaimer**: every record stores `created_and_verified_at`
  (`YYYY-MM-DD HH:MM UTC`); the PDF prints it on the cover and overview and
  includes the link-validity notice.
- A failed gate never reaches JSON storage, R2 or Cloudflare Pages.
- Self-healing: validator errors are fed back to the LLM (max 3 attempts);
  broken snippets are repaired in isolation before a full regeneration.
