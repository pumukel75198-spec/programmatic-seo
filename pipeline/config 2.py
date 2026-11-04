"""Central configuration – the Single Source of Truth for the FlowMatrix pipeline.

Everything that used to be scattered across dozens of .mjs scripts (prices,
import whitelists, blacklisted phrases, paths, PDF layout constants) lives
here. No other module may redefine these values.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "src" / "data"
PUBLIC_DIR = ROOT / "public"
PRIVATE_DIR = ROOT / "private"
DOWNLOADS_DIR = PRIVATE_DIR / "downloads"
API_SCRIPTS_DIR = PRIVATE_DIR / "api-scripts"
KITS_DIR = PRIVATE_DIR / "kits"
API_KITS_DIR = PRIVATE_DIR / "api-kits"
DIST_DIR = ROOT / "dist"
CACHE_DIR = ROOT / ".cache"

APIS_FILE = DATA_DIR / "apis.json"
ALTERNATIVES_FILE = DATA_DIR / "alternatives.json"
WORKFLOWS_FILE = DATA_DIR / "workflows.json"
API_ENDPOINTS_FILE = DATA_DIR / "api-endpoints.json"
PARTNER_FILE = DATA_DIR / "partner.json"
PRICING_FILE = DATA_DIR / "pricing.json"

# --------------------------------------------------------------------------- #
# Pricing (binding – old prices such as 7.99 are forbidden)
# --------------------------------------------------------------------------- #
PRICE_MAP: dict[str, float] = {
    "Beginner": 9.99,
    "Intermediate": 19.99,
    "Advanced": 34.99,
    "Expert": 34.99,
}
SCRIPT_PRICE = 29.99
FORBIDDEN_PRICES = ("7.99",)

# --------------------------------------------------------------------------- #
# Implementation-Kit (PDF + Code .zip)
# --------------------------------------------------------------------------- #
KIT_BADGE = "IMPLEMENTATION KIT (PDF + CODE .ZIP)"
WORKFLOW_KIT_FILES: tuple[str, ...] = (
    "blueprint.pdf",
    "workflow.py",
    ".env.example",
    "mock_data.json",
    "schema.sql",
    "requests.http",
    "AI_IMPLEMENTATION_PROMPT.md",
    "README.md",
)
API_KIT_FILES: tuple[str, ...] = (
    "api_client.py",
    "test_mock.py",
    ".env.example",
    "requests.http",
    "AI_INTEGRATION_PROMPT.md",
    "api-cheatsheet.pdf",
    "README.md",
)


def price_for(difficulty: str | None) -> float:
    key = (difficulty or "").strip().lower()
    for name, price in PRICE_MAP.items():
        if name.lower() == key:
            return price
    return PRICE_MAP["Intermediate"]


def price_label(difficulty: str | None) -> str:
    return f"€{price_for(difficulty):.2f}"


# --------------------------------------------------------------------------- #
# Python import policy for GENERATED code (workflow snippets + API scripts)
# --------------------------------------------------------------------------- #
API_ALLOWED_IMPORTS: frozenset[str] = frozenset(
    {
        "argparse",
        "base64",
        "collections",
        "contextlib",
        "dataclasses",
        "datetime",
        "difflib",
        "email",
        "email.utils",
        "functools",
        "hashlib",
        "hmac",
        "http",
        "http.client",
        "itertools",
        "json",
        "logging",
        "math",
        "os",
        "random",
        "re",
        "socket",
        "ssl",
        "sys",
        "time",
        "typing",
        "unittest",
        "urllib.error",
        "urllib.parse",
        "urllib.request",
        "uuid",
    }
)

FORBIDDEN_IMPORTS: frozenset[str] = frozenset(
    {
        "aiohttp",
        "httpx",
        "numpy",
        "openai",
        "pandas",
        "pydantic",
        "requests",
        "scikit-learn",
        "sklearn",
        "supabase",
    }
)

# Workflow snippets must model a real, deterministic data flow. Randomness is
# explicitly forbidden there (it hides missing data hand-off between steps).
WORKFLOW_FORBIDDEN_IMPORTS: frozenset[str] = FORBIDDEN_IMPORTS | {"random"}

# Full stdlib set (Python 3.10+). Used by the AST gatekeeper.
STDLIB_MODULES: frozenset[str] = frozenset(sys.stdlib_module_names) | {"__future__"}

# --------------------------------------------------------------------------- #
# Content blacklist
# --------------------------------------------------------------------------- #
# Domains the LLM has invented in the past. They are not real and must never
# appear in generated content (the live domain check would reject them anyway,
# but this gives a deterministic, actionable error message).
FAKE_DOMAINS: tuple[str, ...] = (
    "api.socialmedia.com",
    "api.coveragetool.com",
    "competitor2.com",
    "api.yourgateway.com",
)

BLACKLIST_PHRASES: tuple[str, ...] = (
    "scikit-learn",
    "pip install",
    "Dummy",
    "gpt-3.5-turbo",
    "File > New",
    "File > Save",
    "Make a Zap",
    "Adobe XD",
    "api.supabase.io",
    "ChatCompletion.create",
    "Node.js 18",
    "7.99",
    "Prenium Warkflow",
    "Official docs for the API used in THIS step",
)

# Trivial glossary terms that add no didactic value.
TRIVIAL_GLOSSARY_TERMS: frozenset[str] = frozenset(
    {"api", "database", "webhook", "server", "client", "http", "json"}
)

# --------------------------------------------------------------------------- #
# Workflow structure (variable, complexity-driven – no fixed 5-step rule)
# --------------------------------------------------------------------------- #
MIN_STEPS = 3
MAX_STEPS = 8
PREREQUISITES_MIN = 4
GLOSSARY_TERMS_MIN = 4
TROUBLESHOOTING_MIN = 3
MIN_CODE_LINES = 8
MIN_TECHNICAL_EXPLANATION = 120  # characters – didactic depth

FINAL_PREREQUISITE = (
    "Python 3.10 or newer (standard library only) and a terminal"
)

# --------------------------------------------------------------------------- #
# Timestamp + link-validity disclaimer (binding in every PDF and record)
# --------------------------------------------------------------------------- #
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M UTC"

LINK_DISCLAIMER = (
    "Verification & Link Validity Notice: This workflow blueprint was generated "
    "and technically verified on {timestamp}. At the exact time of creation, all "
    "referenced domains, API endpoints, and external resource links were tested "
    "and confirmed reachable. Because third-party APIs and web services evolve "
    "continuously, domains, endpoints, or links inside this document may change "
    "or become unavailable over time."
)

# --------------------------------------------------------------------------- #
# Placeholder base-domain mapping
# --------------------------------------------------------------------------- #
# Code snippets legitimately contain placeholders such as
# ``https://<your-project>.supabase.co``. The live check cannot resolve those,
# so it tests the official main domain instead.
PLACEHOLDER_BASE_DOMAINS: dict[str, str] = {
    "supabase": "https://supabase.com",
    "n8n": "https://n8n.io",
    "openai": "https://openai.com",
    "slack": "https://slack.com",
    "github": "https://github.com",
    "notion": "https://www.notion.so",
    "airtable": "https://airtable.com",
    "stripe": "https://stripe.com",
    "twilio": "https://www.twilio.com",
    "sendgrid": "https://sendgrid.com",
    "mailchimp": "https://mailchimp.com",
    "google": "https://www.google.com",
    "aws": "https://aws.amazon.com",
    "azure": "https://azure.microsoft.com",
    "cloudflare": "https://www.cloudflare.com",
    "posthog": "https://posthog.com",
    "sentry": "https://sentry.io",
    "resend": "https://resend.com",
    "make": "https://www.make.com",
    "zapier": "https://zapier.com",
    "jira": "https://www.atlassian.com",
    "twitter": "https://twitter.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "youtube": "https://www.youtube.com",
}

# --------------------------------------------------------------------------- #
# LLM (OpenRouter)
# --------------------------------------------------------------------------- #
OPENROUTER_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/")
LLM_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
LLM_TIMEOUT = 180
LLM_MAX_ATTEMPTS = 4
MAX_REPLACEMENT_TOPICS = 3

# --------------------------------------------------------------------------- #
# PDF layout constants (dynamic page count – no fixed 10-page blueprint)
# --------------------------------------------------------------------------- #
PAGE_WIDTH = 595.28  # A4 points
PAGE_HEIGHT = 841.89
PDF_MARGIN = 44
CONTENT_WIDTH = PAGE_WIDTH - 2 * PDF_MARGIN
PDF_FOOTER = "FlowMatrix.dev Premium Workflow"  # typo "Prenium Warkflow" fixed

# Dark FlowMatrix palette (hex strings, reportlab-safe).
COLORS = {
    "bg": "#0B1020",
    "panel": "#141B31",
    "panel_alt": "#1B2440",
    "text": "#E8ECF7",
    "muted": "#9AA6C4",
    "brand": "#5468FF",
    "brand_light": "#8FA0FF",
    "emerald": "#3DDC97",
    "code_bg": "#070A14",
    "code_text": "#D7E0FF",
    "border": "#2A3556",
    "white": "#FFFFFF",
}


def load_env() -> None:
    """Load the project .env without overriding existing shell variables."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key() -> str:
    """Return the OpenRouter API key from the environment (loads .env first)."""
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY ist nicht gesetzt.")
    return key
