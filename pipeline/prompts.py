"""The only valid system prompts for the FlowMatrix pipeline.

No other module may contain prompt text. Every prompt enforces the binding
standards:

* 100 % English output (text, comments, docstrings, glossary, checklists).
* A variable number of steps (``MIN_STEPS``..``MAX_STEPS``) driven by the real
  technical complexity – never a fixed 5-step template.
* Python standard library only, no randomness, no dummy data, a real data flow
  from step 1 to step N.
* Tool consistency: every listed tool is actually used in the code and has a
  full URL in ``resources``.
* Correct API patterns (urlencode, Supabase headers, Slack "ok", thresholds,
  current OpenAI models).
"""

from __future__ import annotations

from typing import Any

from . import config

WORKFLOW_SYSTEM = (
    "You are a precise senior technical editor and Python engineer. You only "
    "answer with valid JSON. You never invent tools, domains or data. Every "
    "word you produce is in precise technical English."
)

API_SCRIPT_SYSTEM = (
    "You are a principal Python engineer. You write production-ready, "
    "dependency-free Python 3.10+ scripts that use only the standard library. "
    "You return raw Python source code only – no markdown, no explanations. "
    "All comments and docstrings are in English."
)

CODE_REPAIR_SYSTEM = (
    "You are a principal Python engineer. You repair broken Python snippets. "
    "You return raw Python source code only – no markdown, no explanations. "
    "All comments are in English."
)

TOPIC_SYSTEM = (
    "You are a precise technical content strategist. You only answer with "
    "valid JSON. You propose realistic, buildable automation workflows that "
    "use only real, reachable APIs and tools."
)

ALTERNATIVE_SYSTEM = (
    "You are a precise product analyst. You only answer with valid JSON. "
    "All text is in English."
)


def _tools_block(available_tools: list[dict[str, Any]]) -> str:
    if not available_tools:
        return "—"
    lines = []
    for tool in available_tools:
        parts = [f"- {tool.get('name')}"]
        if tool.get("slug"):
            parts.append(f"slug: {tool['slug']}")
        if tool.get("provider"):
            parts.append(f"provider: {tool['provider']}")
        if tool.get("description"):
            parts.append(f"description: {tool['description']}")
        if tool.get("endpoint"):
            parts.append(
                f"endpoint (BASE – append a concrete resource path): "
                f"{tool['endpoint']}"
            )
        if tool.get("url") or tool.get("affiliateUrl"):
            parts.append(f"docs: {tool.get('url') or tool.get('affiliateUrl')}")
        if tool.get("authentication"):
            parts.append(f"auth: {tool['authentication']}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _alternatives_block(alternatives: list[dict[str, Any]]) -> str:
    if not alternatives:
        return "—"
    return "\n".join(
        f"- {item.get('title')} (slug: {item.get('slug')}): "
        f"{item.get('description')}"
        for item in alternatives
    )


def _domain_of(url: str | None) -> str:
    if not url:
        return "—"
    try:
        from urllib.parse import urlparse

        return urlparse(str(url)).hostname or "—"
    except Exception:  # noqa: BLE001
        return "—"


def _api_building_blocks(available_tools: list[dict[str, Any]]) -> str:
    if not available_tools:
        return "—"
    lines = []
    for tool in available_tools:
        lines.append(
            f"- {tool.get('name')} | slug: {tool.get('slug')} | "
            f"endpoint domain: {_domain_of(tool.get('endpoint'))} | "
            f"docs domain: {_domain_of(tool.get('url'))}"
        )
    return "\n".join(lines)


def _curated_block(workflow: dict[str, Any]) -> str:
    details = workflow.get("details") or {}
    api_slugs = ", ".join(details.get("api_slugs") or []) or "—"
    alternative_slugs = ", ".join(details.get("alternative_slugs") or []) or "—"
    return (
        f"Curated API slugs (exactly these, no others): {api_slugs}\n"
        f"Curated alternative slugs (context only): {alternative_slugs}"
    )


def build_workflow_prompt(
    workflow: dict[str, Any],
    steps: list[dict[str, Any]],
    available_tools: list[dict[str, Any]],
    feedback: str | None = None,
    related_alternatives: list[dict[str, Any]] | None = None,
    step_assignment: str | None = None,
    deterministic_block: str | None = None,
) -> str:
    details = workflow.get("details", {})
    step_list = "\n".join(
        f"{i + 1}. {step.get('title')}\n   Current: {step.get('description') or '(none)'}"
        for i, step in enumerate(steps)
    )
    feedback_block = (
        f"\nVALIDATOR CORRECTIONS (must be fixed):\n{feedback}\n"
        if feedback
        else ""
    )
    assignment_block = (
        "\nBINDING STEP ASSIGNMENT (selected by the pipeline – follow it exactly)\n"
        f"{step_assignment}\n"
        if step_assignment
        else ""
    )
    deterministic_meta = (
        "\nDETERMINISTIC METADATA (already written by Python into the record – "
        "do NOT output, change or contradict it)\n"
        f"{deterministic_block}\n"
        if deterministic_block
        else ""
    )

    return f"""You are a senior technical editor. Produce a complete, end-to-end master guide that lets a buyer rebuild the automation exactly, from A to Z.

WORKFLOW
Title: {workflow.get('title')}
Slug: {workflow.get('slug')}
Category: {workflow.get('category')}
Description: {workflow.get('description')}
Difficulty: {details.get('difficulty') or '—'}
Duration: {details.get('duration') or '—'}
Tools in this workflow: {', '.join(details.get('tools') or []) or '—'}
{_curated_block(workflow)}

MANDATORY API BUILDING BLOCKS (every one MUST be used in at least one step)
{_api_building_blocks(available_tools)}
{assignment_block}{deterministic_meta}
EXISTING STEP OUTLINE
{step_list}

AVAILABLE TOOLS (the ONLY allowed APIs – use their exact endpoints and docs URLs)
{_tools_block(available_tools)}

RELATED ALTERNATIVES (context for the business use case only – never copy their domains)
{_alternatives_block(related_alternatives or [])}
{feedback_block}
TASK
Return a complete, practical guide for EVERY step. ALL text MUST be in precise technical English – no German words, no umlauts, no ß. Answer with valid JSON in exactly this structure:

{{
  "prerequisites": [
    "Concrete, free prerequisite 1",
    "Concrete, free prerequisite 2",
    "Concrete, free prerequisite 3",
    "{config.FINAL_PREREQUISITE}"
  ],
  "glossary": [
    {{ "term": "Advanced concept", "definition": "One-sentence English explanation." }},
    {{ "term": "Advanced concept", "definition": "One-sentence English explanation." }},
    {{ "term": "Advanced concept", "definition": "One-sentence English explanation." }},
    {{ "term": "Advanced concept", "definition": "One-sentence English explanation." }}
  ],
  "troubleshooting": [
    {{ "problem": "Common problem 1", "solution": "Concrete fix" }},
    {{ "problem": "Common problem 2", "solution": "Concrete fix" }},
    {{ "problem": "Common problem 3", "solution": "Concrete fix" }}
  ],
  "resources": [
    {{ "label": "Tool or API name", "url": "https://full-official-url.example" }}
  ],
  "steps": [
    {{
      "title": "Exact title as above",
      "description": "Detailed description (2–4 sentences).",
      "technical_explanation": "MUST cover: (1) architecture role – why this step exists and which data it consumes from the previous step; (2) API contract – exact endpoint, HTTP method, required headers, request payload and JSON response shape; (3) edge cases – rate limits, pagination, empty arrays, type conversion. At least 300 characters and 3 sentences.",
      "code_snippet": "Runnable Python 3 code, at least 10 non-empty lines, standard library only, with precise English inline comments explaining WHY each line is written that way.",
      "mock_response": "A JSON object representing the expected API response for this step's code. Use realistic sample data.",
      "actions": ["Concrete technical action 1", "Concrete technical action 2", "Concrete technical action 3"],
      "commands": [{{ "label": "Short title", "language": "bash", "code": "real command" }}],
      "config": [{{ "key": "PARAMETER_NAME", "value": "concrete value or <placeholder>", "description": "What the parameter is for" }}],
      "tools": ["ToolName from the list that is actually used in this step's code"],
      "checklist": ["Verifiable point 1", "Verifiable point 2"],
      "expectedResult": "One sentence describing what is finished after this step.",
      "links": [{{ "label": "Real documentation name (e.g. X API Search Docs)", "url": "https://real-docs-url" }}]
    }}
  ]
}}

HARD RULES
- STEP COUNT: choose the number of steps the topic genuinely requires, between {config.MIN_STEPS} and {config.MAX_STEPS}. A compact workflow may need 3–4 steps; a complex advanced workflow may need 6–8. Do NOT pad and do NOT abbreviate. Every necessary intermediate step (fetch, parse, transform, persist, alert) must be fully explained until the system is complete and rebuildable.
- "prerequisites": at least {config.PREREQUISITES_MIN} entries. The LAST entry MUST be exactly: "{config.FINAL_PREREQUISITE}". Do not add any entry after it. EXACT COVERAGE AT "BEFORE YOU START": Every tool from "Tools in this workflow" (including Slack Webhooks, OpenAI API, etc.) MUST have its own dedicated bullet point here. Example for tools [n8n, OpenAI API, Supabase, Slack]: ["An n8n account and a webhook URL", "An OpenAI API key", "A Supabase project and service-role key", "A Slack incoming webhook URL", "{config.FINAL_PREREQUISITE}"].
- "glossary": at least {config.GLOSSARY_TERMS_MIN} ADVANCED terms with "term" and "definition". FORBIDDEN trivial terms (never use them): API, Database, Webhook, Server, Client, HTTP, JSON. If you need the webhook concept, use "Incoming Webhook Signature Verification" instead of "Webhook". Explain concepts actually used in this workflow (e.g. Bearer Token Authentication, Rate-Limit Backoff, PostgREST Upsert, Z-Score Spike Detection, Token-Bucket Pagination).
- "troubleshooting": at least {config.TROUBLESHOOTING_MIN} objects with "problem" and "solution".
- "resources": one entry per tool/API used, with the FULL official URL (https://...). Every tool in the workflow MUST appear here, and the label MUST exactly match the tool name (e.g. "X API", "OpenAI API", "Supabase", "Slack").
- "code_snippet": MANDATORY in EVERY step, at least 10 non-empty lines (blank lines do NOT count). Count the lines before answering and add real statements, not comment filler. Every step MUST import the modules it uses (`json`, `urllib.request`, `urllib.parse`, `http.client`, etc. - specifically `import urllib.parse` whenever `urllib.parse.urlencode` is used) at the TOP of that step's snippet, so the concatenated script runs from step 1. Each step MUST end with a top-level call that executes its function and assigns the result (e.g. `mentions = fetch_mentions()`), so the concatenated script runs end-to-end.
- "code_snippet": DEFENSIVE CODING: Always use `.get('key', default_value)` when accessing dictionary keys from API responses. Never assume a key exists. This prevents KeyError during the dry-run. Apply this to EVERY dict access, including nested access such as `data.get('cohorts', [])`, `payload.get('assets', [])` or `response.get('id', '')`.
- "code_snippet": API USAGE: You MUST build at least one dedicated step with a real `urllib.request` call for EVERY provided API. Each API must be explicitly called in the code.
- "code_snippet": Python standard library ONLY. FORBIDDEN: requests, openai, supabase, httpx, aiohttp, pydantic, pandas, scikit-learn, sklearn, sentry_sdk and ANY other SDK/third-party package. NEVER tell the reader to run "pip install".
- "code_snippet": FORBIDDEN: "import random", "random.uniform", "# Dummy", "Dummy", and overwriting variables from previous steps. Use a real, deterministic data flow: step 1 defines a structure (e.g. `mentions = fetch_mentions()`), step 2 consumes exactly that variable (e.g. `analyzed = analyze_sentiment(mentions)`), step 3 consumes `analyzed`, and so on. The concatenation of all step snippets MUST form one coherent, runnable script.
- "code_snippet": syntactically valid Python – correct brackets, quotes and indentation. Check every snippet for balanced brackets before answering.
- "technical_explanation": MANDATORY, at least 300 characters / 3+ sentences covering architecture role, API contract and edge cases.
- "actions": 3–6 concrete technical actions. No UI click paths.
- "checklist": 2–4 verifiable points.
- "links": EVERY step MUST contain at least one entry. Use ONLY the official documentation link of the API that is programmed in THIS specific step (maximum 1 link). Use the REAL documentation name (e.g. `"X API Search Docs: https://..."`). UNDER `LINKS`, NEVER use the literal sentence `"Official docs for the API used in THIS step"` or similar leak phrases, but always the actual name and URL. For a pure Python step without an API call (e.g. `collections.Counter`), link to the exact official Python standard library documentation (e.g. `https://docs.python.org/3/library/collections.html`). Never copy the same links into every step.
- TOOL CONSISTENCY: the tools listed in the workflow, the tools in "prerequisites", the APIs actually called in the code and the "resources" list MUST match 100 %. Never list a tool (e.g. n8n) that does not appear in the code. Never call an API in the code that is missing from the tool list.
- GROUNDING RULE: the ONLY allowed API hosts and endpoints are those listed under AVAILABLE TOOLS. Every code URL MUST use one of those exact endpoints (or a documented path variant of it). Never invent a domain such as api.enrichmentservice.com or use a placeholder host such as api.example.com. The tools in "tools" MUST be a subset of AVAILABLE TOOLS, and each "links" entry MUST point to that tool's docs URL.
- MANDATORY API USAGE: You MUST use EVERY API listed under MANDATORY API BUILDING BLOCKS in at least one step. Reference each API by its brand name, slug or domain in the step code and in the step "tools" list. Never omit a curated API.
- BINDING STEP ASSIGNMENT: When a BINDING STEP ASSIGNMENT block is present, the statement "Step N MUST call ..." is a hard contract. Step N must contain a real `urllib.request` call to exactly that API endpoint (or a documented path below it), its `tools` list must contain exactly that API name for that step, and its code must mention the assigned API host. Do not move, merge or rename assigned steps. The final step may be a pure-Python aggregation step without an API call.
- DETERMINISTIC METADATA: `api_slugs`, `tools`, `before_you_start`, `resources`, `price` and `created_and_verified_at` are owned by the Python pipeline. You must not invent or change them; return the editorial fields requested in the TASK JSON structure only.
- NO UNGROUNDED APIS: if a step needs a capability that is not covered by AVAILABLE TOOLS, implement it with the Python standard library (e.g. regex for email syntax, socket for DNS/MX checks, collections/difflib for clustering). NEVER invent a new API host or service for that capability.
- BASE URL RULE: an endpoint marked BASE is only a prefix. NEVER call it bare (e.g. never call https://api.stripe.com/v1). Always append a real documented resource path such as /v1/customers or /v1/invoices.
- CREDENTIALS: every secret and every project-specific endpoint MUST be read through `os.environ.get("NAME")` – never hardcode `YOUR_X_API_TOKEN`, `YOUR_OPENAI_API_KEY`, `YOUR_SUPABASE_KEY` or `YOUR_SLACK_WEBHOOK_URL` in runnable code. Use UPPER_SNAKE_CASE names such as `X_API_TOKEN`, `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SLACK_WEBHOOK_URL`; the kit's `.env.example` is generated from these names. Keep public API hosts (`https://api.x.com`, `https://api.openai.com`) as constants.
  * The Supabase URL MUST come from `os.environ.get("SUPABASE_URL")`; never hardcode `https://your-supabase-instance.supabase.co`. Use a concrete table name (e.g. `trends`), never `your_table`.
- ZERO-VARIANCE GUARD: before computing a Z-score, guard against fewer than 2 values and a standard deviation of zero (`if len(sentiments) < 2 or stdev == 0: return`). Never divide by zero.
- OPENAI NUMERIC CONTRACT: when OpenAI output is converted with `float(...)`, the user message MUST literally contain `Respond ONLY with a float between -1.0 and 1.0`, and the conversion must handle `ValueError`.
- CORRECT API PATTERNS & STRICT TYPE SAFETY:
  * GET search endpoints (e.g. `/2/tweets/search/recent`) MUST use real query parameters via `urllib.parse.urlencode({{'query': ...}})`. Import `urllib.parse` explicitly in the code block whenever `urllib.parse.urlencode` is used.
  * NEVER pass `headers=` to `urllib.request.urlopen()`. Build the request explicitly: `request = urllib.request.Request(url, data=..., headers=headers)` and call `urllib.request.urlopen(request)`. `urlopen(url, headers=...)` is a runtime `TypeError`.
  * Whenever `float(content)` converts OpenAI output, the OpenAI user message MUST literally contain `Respond ONLY with a float between -1.0 and 1.0`.
  * CLEAN DATA EXTRACTION IN STEP 1: When an API (such as X API `/2/tweets/search/recent`) returns a list of dictionaries (`[{{'id': '1', 'text': '...'}}]`), step 1 MUST directly extract the text strings (`[item['text'] for item in data['data']]`), so subsequent steps do not throw a `TypeError`.
  * STRICT TYPE SAFETY BETWEEN STEPS: If a step (such as OpenAI Sentiment Analysis) produces data that is mathematically calculated in a later step (e.g. with `statistics.mean()` or `statistics.stdev()`), the prompt in code MUST request a number (`"Respond ONLY with a float between -1.0 and 1.0"`) and explicitly convert the result via `float(...)`.
  * The sentiment step MUST return structured records. Build each record as a separate variable, then append it:
    `record = {{'text': mention, 'sentiment': float(content)}}`
    `records.append(record)`
    The clustering step then groups the `text` fields, and the alert step uses the `sentiment` floats. Never discard the mention text.
  * The alert step MUST iterate over the structured records (`for record in analyzed:`), compute the Z-score from `record['sentiment']`, and call `send_alert(record['text'], z_score)`. Never call `send_alert` with only the sentiment float.
  * Supabase payload keys MUST be stable and match the generated `schema.sql` (e.g. `keyword` + `mentions`). Never define `count` in the schema while sending `mentions` in the payload.
  * NEVER put dict literals, colons or complex expressions inside f-strings. Use f-strings only for simple text such as `f"Sentiment: {{sentiment}}"`.
  * Supabase REST requests MUST send both `{{'apikey': SUPABASE_KEY}}` and `{{'Authorization': f'Bearer {{SUPABASE_KEY}}'}}`; POST/Upsert inserts MUST set `{{'Prefer': 'return=representation'}}` and check `if response.status not in (200, 201, 204):` instead of just `!= 200` before parsing.
  * Slack webhooks return the plain text "ok", NOT JSON. Never call `json.loads()` on a Slack webhook response; check `response.status == 200` and `response.read().decode('utf-8')`.
  * Alert steps MUST compute a real threshold (e.g. `if spike_count >= THRESHOLD:`) instead of blindly sending a message.
  * Every step MUST carry at least one real documentation link. Pure Python steps (e.g. `collections.Counter`, `statistics.stdev`) MUST link to the exact Python standard library page.
  * Use current OpenAI models (`gpt-4o-mini` or `gpt-4o`). `gpt-3.5-turbo` is forbidden.
- Use ONLY real, reachable domains. FORBIDDEN invented domains: api.socialmedia.com, api.coveragetool.com, competitor2.com, api.yourgateway.com.
- If a step uses n8n, use an n8n webhook placeholder: "https://<your-n8n-instance>/webhook/<name>". Do not invent a generic API domain.
- FORBIDDEN phrases: "scikit-learn", "pip install", "Dummy", "gpt-3.5-turbo", "File > New", "File > Save", "Make a Zap", "Adobe XD", "api.supabase.io", "ChatCompletion.create", "Node.js 18", "7.99".
- No placeholders like "TODO", "Lorem Ipsum", "undefined".
- No markdown code fences, no text outside the JSON."""


def build_api_script_prompt(
    api: dict[str, Any],
    endpoint: str | None,
    feedback: str | None = None,
) -> str:
    details = api.get("details", {})
    feedback_block = (
        f"\nVALIDATOR CORRECTIONS (must be fixed):\n{feedback}\n"
        if feedback
        else ""
    )
    return f"""Generate a complete, production-ready Python 3.10+ script for the following API.

API
Slug: {api.get('slug')}
Title: {api.get('title')}
Description: {api.get('description')}
Category: {api.get('category')}
Provider: {details.get('provider') or '—'}
Documentation: {details.get('docsUrl') or details.get('website') or '—'}
Endpoint: {endpoint or details.get('endpoint') or '—'}
Authentication: {details.get('authentication') or '—'}
{feedback_block}
MANDATORY ARCHITECTURE
0. Define EXACTLY these TOP-LEVEL functions (never inside a class):
   - `def request_json(url, method="GET", payload=None, headers=None, timeout=15, max_retries=3):` – the robust HTTP helper with HTTPError/URLError handling and exponential backoff.
   - `def fetch_<resource>(...):` – a resource-specific end-to-end function that calls `request_json`.
   - `def main():` – the CLI entry point.
   The validator requires at least 2 top-level functions.
1. Python standard library ONLY: urllib.request, urllib.parse, urllib.error, http.client, json, os, sys, time, datetime, hmac, hashlib, base64, typing, dataclasses, logging, argparse. NO third-party imports.
2. Configuration exclusively via os.environ.get (e.g. API_KEY, BASE_URL). NEVER hardcode keys.
3. A robust HTTP helper `request_json(...)` with:
   - a timeout,
   - correctly set auth headers,
   - error handling for urllib.error.HTTPError and urllib.error.URLError,
   - exponential backoff on 429 and 5xx (e.g. time.sleep(2 ** attempt)).
4. At least 2 to 3 practical end-to-end functions (e.g. fetch data, create/filter a resource, validate a webhook/response) – each with type hints and an English docstring.
5. An executable `if __name__ == "__main__":` block that demonstrates a complete run.
6. A file-header docstring with title, provider, docs and usage notes – in English.

ALL comments and docstrings MUST be in precise technical English. Use current OpenAI models (`gpt-4o-mini`/`gpt-4o`); `gpt-3.5-turbo` is forbidden. Never instruct the reader to run "pip install".

Answer with the raw Python source code ONLY. No markdown fences, no explanatory text."""


def build_code_repair_prompt(
    step: dict[str, Any],
    feedback: str | None = None,
) -> str:
    """Focused repair prompt for a single broken code snippet.

    Regenerating the whole workflow for one SyntaxError wastes tokens and
    usually reintroduces the same mistake. This prompt fixes only the snippet.
    """
    return f"""The following Python code snippet is broken and must be repaired.

TITLE: {step.get('title') or '—'}
DESCRIPTION: {step.get('description') or '—'}

VALIDATOR ERROR:
{feedback or 'unknown'}

CURRENT CODE:
{step.get('code_snippet') or ''}

HARD RULES
- Return ONLY the corrected Python source code (no markdown fences, no text before/after).
- Use only the Python standard library. Never introduce a new external API, SDK or domain.
- Use 'gpt-4o-mini' or 'gpt-4o'. 'gpt-4' and 'gpt-3.5-turbo' are forbidden.
- If OpenAI output is converted with float(), include the literal instruction 'Respond ONLY with a float between -1.0 and 1.0'.
- Python standard library only: urllib.request, urllib.error, urllib.parse, http.client, json, os, sys, time, datetime, hmac, hashlib, base64, typing, dataclasses, logging, argparse, re, math, collections, difflib.
- FORBIDDEN third-party imports (requests, openai, supabase, httpx, aiohttp, pydantic, pandas, scikit-learn, sklearn, gspread, oauth2client, schedule, sentry_sdk, …).
- FORBIDDEN: "import random", "random.uniform", "# Dummy", "Dummy".
- At least 8 non-empty lines.
- Syntactically valid: correct brackets, quotes and indentation.
- Keep the technical intent of the snippet and use only real, reachable domains.
- All comments in English."""


def build_traceback_repair_prompt(
    step: dict[str, Any],
    traceback_text: str,
    step_index: int,
    assigned_api: str | None = None,
    attempt: int = 1,
) -> str:
    """Repair one snippet using the exact runtime traceback from the dry-run."""
    return f"""The workflow dry-run failed. Repair ONLY the Python snippet below.

STEP NUMBER: {step_index}
TITLE: {step.get('title') or '—'}
DESCRIPTION: {step.get('description') or '—'}
ASSIGNED API: {assigned_api or '— (pure Python aggregation step)'}
REPAIR ATTEMPT: {attempt}

EXACT PYTHON TRACEBACK FROM THE DRY-RUN:
{traceback_text}

CURRENT BROKEN CODE:
{step.get('code_snippet') or ''}

HARD RULES
- Return ONLY the corrected Python source code (no markdown fences, no text before/after).
- Fix the exact line/exception shown in the traceback. Do not remove the failing API call.
- DEFENSIVE JSON: every access to a parsed JSON object MUST use `.get('key', default)`. Never use `obj['key']`.
- TYPE SAFETY: if a value is fed into `float()`, `statistics.mean()`, `statistics.stdev()` or arithmetic, guarantee it is numeric. Convert with a guarded `float(...)` inside try/except where the API may return text.
- ZERO-VARIANCE GUARD: before dividing by a standard deviation, check `if len(values) < 2 or stdev == 0: return`.
- The snippet MUST end with a top-level statement that calls its function and assigns the result (e.g. `records = fetch_records()`), so the concatenated workflow executes.
- The snippet MUST import every module it uses at the TOP (`json`, `urllib.request`, `urllib.parse`, `os`, `statistics`, ...).
- Use ONLY the assigned API endpoint host; never invent a new domain. Standard library only (urllib.request, urllib.error, urllib.parse, http.client, json, os, sys, time, datetime, hmac, hashlib, base64, typing, dataclasses, logging, argparse, re, math, collections, difflib, statistics).
- FORBIDDEN: requests, openai, supabase, httpx, aiohttp, pydantic, pandas, scikit-learn, sklearn, `import random`, "Dummy", "pip install".
- Use `gpt-4o-mini` or `gpt-4o`, never `gpt-4` or `gpt-3.5-turbo`.
- At least 10 non-empty lines. Syntactically valid Python with correct brackets and indentation.
- Keep every existing English comment where possible and all comments in English."""


def build_technical_explanation_repair_prompt(step: dict[str, Any]) -> str:
    """Expand a too-short technical explanation for one step."""
    return f"""Rewrite the technical explanation for the following workflow step.

TITLE: {step.get('title') or '—'}
DESCRIPTION: {step.get('description') or '—'}
CURRENT EXPLANATION:
{step.get('technical_explanation') or ''}

REQUIREMENTS
- At least 300 characters and at least 3 full sentences.
- Cover all three aspects:
  1. Architecture role: why this step exists and which data it consumes from the previous step.
  2. API contract: exact endpoint, HTTP method, required headers, request payload shape and JSON response shape.
  3. Edge cases: rate limits, pagination, empty arrays and type conversion.
- 100 % technical English. No German words, no umlauts.
- Do not change or repeat the code.

Answer with valid JSON only:
{{"technical_explanation": "..."}}"""


def build_curated_topic_prompt(
    apis: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    existing_titles: list[str],
) -> str:
    """Ask for ONE workflow topic that is grounded on the given batch records.

    The pipeline owns the grounding: the returned topic may describe the
    business use case, but the workflow will only ever reference the API and
    alternative slugs listed here.
    """
    api_lines = []
    for api in apis:
        details = api.get("details") or {}
        api_lines.append(
            f"- slug: {api.get('slug')} | title: {api.get('title')} | "
            f"category: {api.get('category')} | use case: {details.get('useCase') or '—'} | "
            f"endpoint: {details.get('endpoint') or '—'} | "
            f"docs: {details.get('docsUrl') or details.get('website') or '—'}"
        )
    alt_lines = [
        f"- slug: {alt.get('slug')} | title: {alt.get('title')} | "
        f"category: {alt.get('category')}"
        for alt in alternatives
    ]
    titles = "\n".join(f"- {title}" for title in existing_titles[:80]) or "—"
    return f"""Design ONE realistic automation workflow that uses ALL of the following real APIs together.

APIs (every one must be used in the workflow):
{chr(10).join(api_lines) or '—'}

ALTERNATIVES (business context only – never copy their domains):
{chr(10).join(alt_lines) or '—'}

Do NOT reuse any of these existing workflow titles:
{titles}

Return valid JSON in exactly this structure:
{{
  "slug": "kebab-case-slug",
  "title": "Clear English title",
  "description": "2–3 English sentences describing the outcome.",
  "category": "A short category label such as AI & LLM, Developer Tools, Data & Databases, Content & SEO, Finance & Payments",
  "tags": ["tag1", "tag2", "tag3"],
  "difficulty": "Beginner | Intermediate | Advanced | Expert",
  "duration": "e.g. 45–60 minutes",
  "use_case": "One English sentence describing the business value.",
  "steps": [
    {{ "title": "Step title", "description": "One English sentence." }}
  ]
}}

RULES
- 3 to {config.MAX_STEPS} steps, driven by real complexity.
- The workflow MUST call every listed API in at least one step.
- Use only the listed APIs and their real endpoints/docs. No invented domains.
- All text in English."""


def build_new_topic_prompt(
    existing_titles: list[str],
    available_tools: list[str],
) -> str:
    """Ask the LLM for a brand-new, buildable workflow topic.

    Used when a workflow is discarded because one of its domains is not
    reachable: the pipeline replaces it with a fresh topic instead of shipping
    broken links.
    """
    titles = "\n".join(f"- {title}" for title in existing_titles[:60]) or "—"
    tools = ", ".join(available_tools) or "—"
    return f"""Propose ONE new, realistic automation workflow topic that can be built with real, reachable APIs.

Do NOT reuse any of these existing titles:
{titles}

Prefer these tools (you may use a subset): {tools}

Answer with valid JSON in exactly this structure:
{{
  "slug": "kebab-case-slug",
  "title": "Clear English title",
  "description": "2–3 English sentences describing the outcome.",
  "category": "One of: Developer Tools, Marketing & Analytics, Data & Automation, Productivity",
  "tags": ["tag1", "tag2", "tag3"],
  "difficulty": "Beginner | Intermediate | Advanced | Expert",
  "duration": "e.g. 30–45 minutes",
  "tools": ["RealToolName"],
  "useCase": "One English sentence describing the business value.",
  "steps": [
    {{ "title": "Step title", "description": "One English sentence." }}
  ]
}}

RULES
- 3 to {config.MAX_STEPS} steps, driven by real complexity.
- Only real, reachable tools and APIs. No invented domains.
- All text in English."""


def build_alternative_prompt(
    alternative: dict[str, Any],
    feedback: str | None = None,
) -> str:
    details = alternative.get("details", {})
    feedback_block = (
        f"\nVALIDATOR CORRECTIONS (must be fixed):\n{feedback}\n"
        if feedback
        else ""
    )
    return f"""Create an alternatives dataset in ENGLISH.

Slug: {alternative.get('slug')}
Title: {alternative.get('title')}
Category: {alternative.get('category')}
Original: {details.get('original') or '—'}
{feedback_block}
Answer with valid JSON only:
{{
  "description": "2–3 sentences describing what this alternatives page covers.",
  "tags": ["tag1", "tag2", "tag3"],
  "alternatives": [
    {{
      "name": "Product name",
      "description": "One sentence.",
      "pros": ["Advantage 1", "Advantage 2"],
      "cons": ["Drawback 1", "Drawback 2"],
      "bestFor": "Target audience"
    }}
  ]
}}
RULES: at least 3 alternatives, all text in English, no invented tools."""
