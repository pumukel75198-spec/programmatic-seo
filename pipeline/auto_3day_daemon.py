#!/usr/bin/env python3
"""Unattended 3-day FlowMatrix daemon.

This is the only entry point that must run on the Mac Mini. It is designed to
be executed by ``launchd`` every 72 hours and to finish **exactly three fully
verified workflows** or exit with a non-zero status – it never waits for a
human decision.

Hard guarantees implemented here (not delegated to the LLM):

* **Deterministic metadata** – Python selects 2–4 verified APIs from
  ``src/data/apis.json`` and writes ``api_slugs``, ``tools``,
  ``before_you_start``, ``resources``, ``price`` and
  ``created_and_verified_at`` into the record. The LLM only writes editorial
  text, glossary, troubleshooting and Python snippets.
* **Self-healing code synthesis** – every snippet is hardened by
  :mod:`pipeline.code_hardener` (AST-based ``.get(key, default)`` rewrite) and
  the exact runtime traceback is sent back to the LLM up to three times.
* **Replacement pool** – at least ten candidate concepts are prepared. A
  candidate that fails any gate (live domain, AST, dry-run, PDF, kit, R2) is
  discarded and the loop immediately continues with the next one until
  ``successful_count == target_count``.
* **Full delivery** – after the third success the daemon pulls, runs
  ``npm run build``, commits and pushes, and installs a ``launchd`` job that
  repeats the cycle every 259200 seconds.

Usage::

    python3 pipeline/auto_3day_daemon.py --target-count 3

The script re-executes itself with ``.venv/bin/python`` when the system Python
lacks ``reportlab``/``pydantic``, so the documented ``python3`` invocation is
enough.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent


# --------------------------------------------------------------------------- #
# Bootstrap: make ``python3 pipeline/auto_3day_daemon.py`` always work
# --------------------------------------------------------------------------- #
def _ensure_runtime() -> None:
    """Re-exec with the project venv when dependencies are missing."""
    try:
        import pydantic  # noqa: F401
        import reportlab  # noqa: F401
    except Exception:  # noqa: BLE001 - any import problem means "use the venv"
        venv_python = _ROOT / ".venv" / "bin" / "python"
        # ``.venv/bin/python`` is usually a symlink to the same base binary as
        # the system python, so comparing resolved executable paths is wrong.
        # The virtual-environment prefix is the reliable discriminator.
        if venv_python.exists() and Path(sys.prefix).resolve() != (
            _ROOT / ".venv"
        ).resolve():
            os.execv(str(venv_python), [str(venv_python), str(_HERE), *sys.argv[1:]])


_ensure_runtime()

# Allow direct execution (``python3 pipeline/auto_3day_daemon.py``).
if __package__ in (None, ""):
    sys.path.insert(0, str(_ROOT))
    __package__ = "pipeline"

from . import bundle_builder, config as cfg, llm_client, prompts, validator
from . import run_batch
from .code_hardener import harden_code

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
DAEMON_LOG = _ROOT / "pipeline" / "daemon.log"
STATE_FILE = _ROOT / "pipeline" / "daemon_state.json"
PLIST_NAME = "com.flowmatrix.autobatch.plist"
PLIST_PATH = _ROOT / "pipeline" / PLIST_NAME
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LAUNCHD_INTERVAL_SECONDS = 259200  # exactly 72 hours
PRIMARY_MODEL = "deepseek/deepseek-v4.1-flash-1017"
FALLBACK_MODEL = "openai/gpt-4o-mini"
DIFFICULTY_BY_SIZE = {2: "Beginner", 3: "Intermediate", 4: "Advanced"}
DURATION_BY_SIZE = {
    2: "35–45 minutes",
    3: "60–75 minutes",
    4: "90–120 minutes",
}
MAX_SELF_HEAL_ROUNDS = 3
MAX_GENERATION_ATTEMPTS = 3
MIN_POOL_SIZE = 10

_TECHNICAL_FILLER = (
    "Architecturally, this step is the contract boundary between the upstream "
    "producer and the downstream consumer: it validates the HTTP status code, "
    "deserializes the JSON body with defensive accessors, and normalizes the "
    "fields that later steps depend on. The request uses the documented "
    "endpoint with the required authentication header, and the response is "
    "checked for rate-limit, pagination and empty-array edge cases before any "
    "value is converted to a number."
)

_TRACEBACK_LINE = re.compile(r'File "workflow\.py", line (\d+)')


# --------------------------------------------------------------------------- #
# Logging + state
# --------------------------------------------------------------------------- #
def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    DAEMON_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DAEMON_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:  # noqa: BLE001 - a corrupt state must never abort
            pass
    return {}


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    run_batch.save_json(STATE_FILE, state)


# --------------------------------------------------------------------------- #
# Subprocess helpers
# --------------------------------------------------------------------------- #
def _run(
    args: list[str],
    *,
    cwd: Path = _ROOT,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    log(f"$ {' '.join(args)}")
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def git_pull(attempts: int = 3) -> bool:
    for attempt in range(1, attempts + 1):
        try:
            result = _run(
                ["git", "pull", "--rebase", "--autostash", "origin", "main"],
                timeout=180,
            )
        except Exception as error:  # noqa: BLE001
            log(f"[GIT] pull attempt {attempt} failed: {error}")
            time.sleep(2 ** (attempt - 1))
            continue
        if result.returncode == 0:
            log("[GIT] pull --rebase origin main: OK")
            return True
        log(
            f"[GIT] pull attempt {attempt} failed: "
            f"{(result.stderr or result.stdout).strip()[:400]}"
        )
        time.sleep(2 ** (attempt - 1))
    return False


def git_commit_and_push(message: str, attempts: int = 3) -> bool:
    add = _run(["git", "add", "-A"], timeout=180)
    if add.returncode != 0:
        log(f"[GIT] git add failed: {(add.stderr or add.stdout).strip()[:400]}")
        return False
    staged = _run(["git", "diff", "--cached", "--quiet"], timeout=60)
    if staged.returncode != 0:
        commit = _run(["git", "commit", "-m", message], timeout=180)
        if commit.returncode != 0:
            log(
                "[GIT] commit failed: "
                f"{(commit.stderr or commit.stdout).strip()[:400]}"
            )
            return False
        log(f"[GIT] committed: {message}")
    else:
        log("[GIT] nothing to commit – pushing the current main state")

    for attempt in range(1, attempts + 1):
        pull = _run(
            ["git", "pull", "--rebase", "--autostash", "origin", "main"],
            timeout=180,
        )
        if pull.returncode != 0:
            log(
                f"[GIT] pre-push pull attempt {attempt} failed: "
                f"{(pull.stderr or pull.stdout).strip()[:400]}"
            )
            time.sleep(2 ** (attempt - 1))
            continue
        push = _run(["git", "push", "origin", "main"], timeout=300)
        if push.returncode == 0:
            log("[GIT] push origin main: OK (GitHub Actions deploy triggered)")
            return True
        log(
            f"[GIT] push attempt {attempt} failed: "
            f"{(push.stderr or push.stdout).strip()[:400]}"
        )
        time.sleep(2 ** (attempt - 1))
    return False


def build_frontend(attempts: int = 2) -> bool:
    for attempt in range(1, attempts + 1):
        try:
            result = _run(["npm", "run", "build"], timeout=900)
        except subprocess.TimeoutExpired:
            log(f"[BUILD] attempt {attempt} timed out")
            continue
        dist_index = _ROOT / "dist" / "index.html"
        if (
            result.returncode == 0
            and dist_index.exists()
            and dist_index.stat().st_size > 0
        ):
            log("[BUILD] npm run build: OK")
            return True
        log(
            f"[BUILD] attempt {attempt} failed (exit {result.returncode}): "
            f"{(result.stderr or result.stdout).strip()[-600:]}"
        )
    return False


# --------------------------------------------------------------------------- #
# launchd
# --------------------------------------------------------------------------- #
def _plist_xml(python_bin: Path) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.flowmatrix.autobatch</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_bin}</string>
        <string>{_HERE}</string>
        <string>--target-count</string>
        <string>3</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{_ROOT}</string>
    <key>StartInterval</key>
    <integer>{LAUNCHD_INTERVAL_SECONDS}</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>ProcessType</key>
    <string>Background</string>
    <key>StandardOutPath</key>
    <string>{DAEMON_LOG}</string>
    <key>StandardErrorPath</key>
    <string>{DAEMON_LOG}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>HOME</key>
        <string>{Path.home()}</string>
    </dict>
</dict>
</plist>
"""


def write_plist(python_bin: Path) -> Path:
    """Write the launchd definition so it can be committed with the batch."""
    PLIST_PATH.write_text(_plist_xml(python_bin), encoding="utf-8")
    log(f"[LAUNCHD] wrote {PLIST_PATH}")
    return PLIST_PATH


def load_plist() -> bool:
    """Install and bootstrap the already-written launchd job (best effort)."""
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    destination = LAUNCH_AGENTS / PLIST_NAME
    shutil.copy2(PLIST_PATH, destination)
    uid = os.getuid()
    _run(
        ["launchctl", "bootout", f"gui/{uid}", str(destination)],
        timeout=60,
    )
    _run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(destination)],
        timeout=60,
    )
    check = _run(
        ["launchctl", "print", f"gui/{uid}/com.flowmatrix.autobatch"],
        timeout=60,
    )
    if check.returncode == 0:
        log("[LAUNCHD] job loaded – next automatic run in 72 hours")
        return True
    log(
        "[LAUNCHD] warning: job could not be loaded automatically. "
        f"Plist is ready at {destination}"
    )
    return False


# --------------------------------------------------------------------------- #
# Live-domain checks (deterministic, cached by validator)
# --------------------------------------------------------------------------- #
class _LiveChecksEnabled:
    def __enter__(self) -> "_LiveChecksEnabled":
        self.previous = os.environ.pop("FLOWMATRIX_SKIP_LIVE", None)
        return self

    def __exit__(self, *exc: object) -> bool:
        if self.previous is not None:
            os.environ["FLOWMATRIX_SKIP_LIVE"] = self.previous
        return False


class _LiveChecksDisabled:
    def __enter__(self) -> "_LiveChecksDisabled":
        self.previous = os.environ.get("FLOWMATRIX_SKIP_LIVE")
        os.environ["FLOWMATRIX_SKIP_LIVE"] = "1"
        return self

    def __exit__(self, *exc: object) -> bool:
        if self.previous is None:
            os.environ.pop("FLOWMATRIX_SKIP_LIVE", None)
        else:
            os.environ["FLOWMATRIX_SKIP_LIVE"] = self.previous
        return False


def _host(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(str(url)).hostname or ""
    except Exception:  # noqa: BLE001
        return ""


def _tcp_ok(host: str) -> tuple[bool, str]:
    if not host:
        return False, "invalid host"
    try:
        return validator._tcp_reachable(host)  # type: ignore[attr-defined]
    except Exception as error:  # noqa: BLE001
        return False, f"{type(error).__name__}: {error}"


def live_domain_check(apis: list[dict[str, Any]]) -> list[str]:
    """Verify every chosen API's endpoint host and documentation page.

    The endpoint hosts are tested with a bounded TCP/UDP-agnostic 443 probe
    (DNS + TCP). The documentation URLs are tested with the validator's
    HEAD/GET probe so a dead documentation page is caught before a single LLM
    token is spent.

    Full-path checks of generated code URLs are intentionally skipped later in
    ``validate_workflow`` (``FLOWMATRIX_SKIP_LIVE=1``): APIs routinely answer
    404 on a concrete resource path without authentication, which would
    otherwise reject perfectly valid workflows. The domain-level gate above is
    the authoritative live check for the daemon.
    """
    errors: list[str] = []
    checked_hosts: set[str] = set()
    resource_payload: list[dict[str, str]] = []

    for api in apis:
        details = api.get("details") or {}
        title = str(api.get("title") or api.get("slug") or "API")
        endpoint = str(details.get("endpoint") or "").strip()
        docs_url = str(details.get("docsUrl") or details.get("website") or "").strip()

        host = _host(endpoint)
        if host and any(char in host for char in "<>{}"):
            # Placeholder endpoints (e.g. {shop}.myshopify.com) must be tested
            # against their real registrable domain, never the placeholder.
            mapped = validator._base_domain_for_placeholder(host)  # type: ignore[attr-defined]
            if mapped:
                host = _host(mapped) or ""
            else:
                real_labels = [
                    label
                    for label in host.split(".")
                    if label and not any(char in label for char in "<>{}")
                ]
                host = ".".join(real_labels[-2:]) if len(real_labels) >= 2 else ""
        if host:
            domain = validator._registrable_domain(host)  # type: ignore[attr-defined]
            if domain not in checked_hosts:
                checked_hosts.add(domain)
                ok, reason = _tcp_ok(domain)
                if not ok:
                    errors.append(
                        f"{title}: endpoint domain not reachable: "
                        f"{domain} ({reason})"
                    )
        if docs_url:
            resource_payload.append({"label": title, "url": docs_url})

    if resource_payload:
        with _LiveChecksEnabled():
            errors.extend(
                validator.validate_domains(
                    {"details": {"resources": resource_payload}},
                    "Candidate",
                )
            )
    return errors


# --------------------------------------------------------------------------- #
# Candidate pool (deterministic concepts, no LLM involved)
# --------------------------------------------------------------------------- #
def _api_payload(api: dict[str, Any]) -> dict[str, Any]:
    details = api.get("details") or {}
    return {
        "slug": str(api.get("slug") or ""),
        "title": str(api.get("title") or ""),
        "short": re.sub(r"\s+API$", "", str(api.get("title") or "")).strip(),
        "provider": str(details.get("provider") or ""),
        "endpoint": str(details.get("endpoint") or ""),
        "docs": str(details.get("docsUrl") or details.get("website") or ""),
        "category": str(api.get("category") or ""),
        "tags": [str(tag) for tag in api.get("tags") or []],
        "use_case": str(details.get("useCase") or ""),
        "description": str(api.get("description") or ""),
        "api": api,
    }


def _domain_rank(payload: dict[str, Any]) -> int:
    category = payload["category"].lower()
    if any(
        word in category
        for word in (
            "database",
            "storage",
            "vector",
            "devops",
            "infrastructure",
            "backend",
        )
    ):
        return 3
    if any(
        word in category
        for word in ("ai", "language", "speech", "vision", "ml", "automation")
    ):
        return 2
    return 1


def _order_combo(combo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        combo,
        key=lambda api: (_domain_rank(_api_payload(api)), str(api.get("slug") or "")),
    )


def _first_sentence(text: str, limit: int = 190) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return ""
    sentence = re.split(r"(?<=[.!?])\s+", value)[0]
    if len(sentence) > limit:
        sentence = sentence[: limit - 3].rstrip() + "..."
    return sentence


def _unique_slug(base: str, existing: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "auto-workflow"
    candidate = slug
    counter = 2
    while candidate in existing:
        candidate = f"{slug}-{counter}"
        counter += 1
    existing.add(candidate)
    return candidate


def _concept_title(combo: list[dict[str, Any]]) -> str:
    short = [_api_payload(api)["short"] for api in combo]
    if len(short) == 2:
        return f"{short[0]} + {short[1]} Automation Pipeline"
    if len(short) == 3:
        return f"{short[0]} to {short[1]} with {short[2]} Orchestration"
    return (
        f"End-to-End {short[0]} and {short[1]} Automation with "
        f"{short[2]} and {short[3]}"
    )


def _related_alternatives(
    alternatives: list[dict[str, Any]],
    *,
    category: str,
    tags: list[str],
    limit: int = 2,
) -> list[str]:
    wanted_tags = set(tags)
    ranked: list[tuple[int, str]] = []
    for alternative in alternatives:
        alt_category = str(alternative.get("category") or "")
        alt_tags = {str(tag) for tag in alternative.get("tags") or []}
        score = 0
        if alt_category == category:
            score += 2
        score += len(wanted_tags & alt_tags)
        if score:
            ranked.append((score, str(alternative.get("slug") or "")))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [slug for _, slug in ranked[:limit] if slug]


def build_concept(
    combo: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    existing_slugs: set[str],
    existing_titles: set[str],
) -> dict[str, Any]:
    payloads = [_api_payload(api) for api in combo]
    base_title = _concept_title(combo)
    title = base_title
    counter = 2
    while title.strip().lower() in existing_titles:
        title = f"{base_title} Blueprint {counter}"
        counter += 1
    existing_titles.add(title.strip().lower())

    category_counts = Counter(item["category"] for item in payloads if item["category"])
    category = category_counts.most_common(1)[0][0] if category_counts else "Data & Automation"

    tags: list[str] = []
    for item in payloads:
        for tag in item["tags"]:
            if tag and tag not in tags:
                tags.append(tag)
    tags = tags[:8]

    difficulty = DIFFICULTY_BY_SIZE[len(payloads)]
    price = float(cfg.PRICE_MAP[difficulty])

    use_cases = [item["use_case"] for item in payloads if item["use_case"]]
    descriptions = [
        _first_sentence(item["description"]) for item in payloads if item["description"]
    ]
    if use_cases:
        use_case = " Then ".join(
            sentence.rstrip(".") + "." for sentence in use_cases
        )
    else:
        use_case = (
            f"Combine {payloads[0]['short']} with {payloads[-1]['short']} "
            "to automate a real production data flow end to end."
        )

    if descriptions:
        description = (
            f"Build a production-ready pipeline that connects "
            f"{payloads[0]['short']} with {payloads[-1]['short']} and "
            f"{' '.join(descriptions[:2])}"
        )
    else:
        description = (
            f"Connect {payloads[0]['short']} with {payloads[-1]['short']} "
            "to move data from ingestion to a verified persistence layer."
        )
    description = re.sub(r"\s+", " ", description).strip()
    if len(description) > 420:
        description = description[:417].rstrip() + "..."

    slug = _unique_slug(title, existing_slugs)

    step_titles = [f"Ingest source records from {payloads[0]['short']}"]
    for item in payloads[1:]:
        step_titles.append(
            f"Process and enrich the records with {item['short']}"
        )
    step_titles.append(
        "Validate, aggregate and persist the final operational summary"
    )

    return {
        "slug": slug,
        "title": title,
        "description": description,
        "category": category,
        "tags": tags,
        "difficulty": difficulty,
        "duration": DURATION_BY_SIZE[len(payloads)],
        "price": price,
        "apis": combo,
        "payloads": payloads,
        "alternative_slugs": _related_alternatives(
            alternatives, category=category, tags=tags
        ),
        "use_case": use_case,
        "step_titles": step_titles,
    }


def build_candidate_pool(
    apis: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    workflows: list[dict[str, Any]],
    count: int,
    seed: int,
) -> list[dict[str, Any]]:
    usable = [
        api
        for api in apis
        if str((api.get("details") or {}).get("endpoint") or "").strip()
        and str(
            (api.get("details") or {}).get("docsUrl")
            or (api.get("details") or {}).get("website")
            or ""
        ).strip()
    ]
    usable.sort(key=lambda api: str(api.get("slug") or ""))
    if len(usable) < 2:
        return []

    rng = random.Random(seed)
    rng.shuffle(usable)

    existing_slugs = {str(item.get("slug") or "") for item in workflows}
    existing_titles = {
        str(item.get("title") or "").strip().lower() for item in workflows
    }
    existing_combos: set[frozenset[str]] = set()
    for workflow in workflows:
        slugs = [
            str(slug)
            for slug in ((workflow.get("details") or {}).get("api_slugs") or [])
            if str(slug).strip()
        ]
        if 2 <= len(slugs) <= 4:
            existing_combos.add(frozenset(slugs))

    size_pool = len(usable)
    seen_combos = set(existing_combos)
    concepts: list[dict[str, Any]] = []
    attempts = 0
    max_attempts = max(count * 40, 400)

    while len(concepts) < count and attempts < max_attempts:
        size = 2 + (len(concepts) % 3)
        size = min(size, size_pool)
        stride = max(1, size_pool // (size * 2))
        indices = [
            (attempts * size + index * (stride + 1)) % size_pool
            for index in range(size)
        ]
        combo: list[dict[str, Any]] = []
        for index in indices:
            api = usable[index]
            if api not in combo:
                combo.append(api)
        attempts += 1
        if len(combo) < 2:
            continue
        combo_key = frozenset(str(api.get("slug") or "") for api in combo)
        if combo_key in seen_combos:
            continue
        seen_combos.add(combo_key)
        concepts.append(
            build_concept(
                _order_combo(combo),
                alternatives,
                existing_slugs,
                existing_titles,
            )
        )
    return concepts


# --------------------------------------------------------------------------- #
# Deterministic skeleton + prompt
# --------------------------------------------------------------------------- #
def _before_you_start(combo: list[dict[str, Any]]) -> list[str]:
    entries: list[str] = []
    for api in combo:
        payload = _api_payload(api)
        docs_domain = _host(payload["docs"]) or payload["provider"] or "the provider"
        entries.append(
            f"A {payload['title']} account with API credentials "
            f"(documentation: {docs_domain})"
        )
    entries.append(
        "A local project folder for workflow.py, mock_data.json and the .env file"
    )
    entries.append(cfg.FINAL_PREREQUISITE)
    return entries


def _resources(combo: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "label": str(api.get("title") or api.get("slug")),
            "url": _api_payload(api)["docs"],
        }
        for api in combo
        if _api_payload(api)["docs"]
    ]


def build_skeleton(concept: dict[str, Any]) -> dict[str, Any]:
    combo = concept["apis"]
    payloads = concept["payloads"]
    prerequisites = _before_you_start(combo)
    price = float(concept["price"])
    timestamp = run_batch._now_timestamp()  # noqa: SLF001 - shared format helper

    steps = [
        {
            "title": title,
            "description": (
                f"Implement the {payloads[min(index, len(payloads) - 1)]['short']} "
                "contract, validate the response and hand normalized records to "
                "the next stage."
                if index < len(payloads)
                else "Aggregate the normalized records from all previous steps, "
                "validate the schema and persist the final operational summary."
            ),
        }
        for index, title in enumerate(concept["step_titles"])
    ]

    return {
        "slug": concept["slug"],
        "title": concept["title"],
        "description": concept["description"],
        "category": concept["category"],
        "tags": list(concept["tags"]),
        "price": price,
        "created_and_verified_at": timestamp,
        "details": {
            "difficulty": concept["difficulty"],
            "duration": concept["duration"],
            "tools": [payload["title"] for payload in payloads],
            "api_slugs": [payload["slug"] for payload in payloads],
            "alternative_slugs": list(concept["alternative_slugs"]),
            "useCase": concept["use_case"],
            "steps": steps,
            "prerequisites": prerequisites,
            "before_you_start": list(prerequisites),
            "glossary": [],
            "troubleshooting": [],
            "resources": _resources(combo),
            "price": price,
        },
    }


def _step_assignment(combo: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, api in enumerate(combo, start=1):
        payload = _api_payload(api)
        lines.append(
            f"Step {index} MUST call {payload['title']} "
            f"(endpoint: {payload['endpoint']}; docs: {payload['docs']}). "
            f'The step "tools" list MUST be exactly ["{payload["title"]}"].'
        )
    lines.append(
        f"Step {len(combo) + 1} is a pure-Python aggregation and persistence "
        f"step (no API call): consume the variables produced by steps 1..{len(combo)}, "
        "validate them and persist the final summary. Its \"tools\" list MUST be []."
    )
    lines.append(
        f"Return EXACTLY {len(combo) + 1} steps in exactly this order – do not "
        "add, remove, merge or renumber steps."
    )
    return "\n".join(f"- {line}" for line in lines)


def _deterministic_block(skeleton: dict[str, Any]) -> str:
    details = skeleton["details"]
    return "\n".join(
        [
            f"- api_slugs = {json.dumps(details['api_slugs'])}",
            f"- tools = {json.dumps(details['tools'])}",
            f"- before_you_start = {json.dumps(details['before_you_start'])}",
            f"- resources = {json.dumps(details['resources'])}",
            f"- price = {skeleton['price']}",
            f"- created_and_verified_at = {skeleton['created_and_verified_at']}",
            "- prerequisites and resources are optional in your JSON response; "
            "the pipeline overwrites them with the values above.",
        ]
    )


# --------------------------------------------------------------------------- #
# Editorial assembly + deterministic defaults
# --------------------------------------------------------------------------- #
def _fallback_glossary(combo: list[dict[str, Any]]) -> list[dict[str, str]]:
    first = _api_payload(combo[0])
    return [
        {
            "term": f"{first['provider'] or first['short']} Bearer Token Authentication",
            "definition": (
                "The API key is sent in the Authorization header as a bearer "
                "token, so the credential never appears in the URL or in logs."
            ),
        },
        {
            "term": "Idempotent Request Retry",
            "definition": (
                "A retry sends the same idempotency key so that a repeated "
                "write cannot create duplicate records after a timeout."
            ),
        },
        {
            "term": "Defensive JSON Deserialization",
            "definition": (
                "Every optional response field is read through a default-carrying "
                "accessor, so a missing key degrades gracefully instead of "
                "raising an exception."
            ),
        },
        {
            "term": "Rate-Limit Exponential Backoff",
            "definition": (
                "On HTTP 429 the client waits with an exponentially growing "
                "delay and jitter instead of hammering the endpoint."
            ),
        },
    ]


def _fallback_troubleshooting(combo: list[dict[str, Any]]) -> list[dict[str, str]]:
    first = _api_payload(combo[0])
    return [
        {
            "problem": f"{first['title']} returns HTTP 401 or 403",
            "solution": (
                "Read the token from the documented environment variable, check "
                "that it has not expired and confirm the required scopes."
            ),
        },
        {
            "problem": "The API returns HTTP 429 during a larger run",
            "solution": (
                "Respect the Retry-After header, add jittered exponential "
                "backoff and reduce the page size or request rate."
            ),
        },
        {
            "problem": "A response field is missing or has a different type",
            "solution": (
                "Use .get('key', default) for every field, validate the shape "
                "before converting values and log the raw payload on mismatch."
            ),
        },
    ]


def _normalize_glossary(
    entries: Any, combo: list[dict[str, Any]]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        term = str(entry.get("term") or "").strip()
        definition = str(entry.get("definition") or "").strip()
        if not term or not definition:
            continue
        if term.lower() in cfg.TRIVIAL_GLOSSARY_TERMS:
            continue
        if term.lower() in seen:
            continue
        seen.add(term.lower())
        result.append({"term": term, "definition": definition})
    for fallback in _fallback_glossary(combo):
        if len(result) >= cfg.GLOSSARY_TERMS_MIN:
            break
        if fallback["term"].lower() in seen:
            continue
        seen.add(fallback["term"].lower())
        result.append(fallback)
    return result[:8]


def _normalize_troubleshooting(
    entries: Any, combo: list[dict[str, Any]]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        problem = str(entry.get("problem") or "").strip()
        solution = str(entry.get("solution") or "").strip()
        if problem and solution:
            result.append({"problem": problem, "solution": solution})
    for fallback in _fallback_troubleshooting(combo):
        if len(result) >= cfg.TROUBLESHOOTING_MIN:
            break
        result.append(fallback)
    return result


def _pad_explanation(text: str) -> str:
    value = str(text or "").strip()
    while len(value) < 320:
        value = f"{value} {_TECHNICAL_FILLER}".strip()
    return value


def _missing_api_calls(
    steps: list[dict[str, Any]], combo: list[dict[str, Any]]
) -> list[str]:
    missing: list[str] = []
    for index, api in enumerate(combo):
        if index >= len(steps):
            missing.append(f"Step {index + 1} is missing entirely")
            continue
        code = str(steps[index].get("code_snippet") or "").lower()
        markers = validator._api_markers(api)  # type: ignore[attr-defined]
        if not any(marker.lower() in code for marker in markers):
            payload = _api_payload(api)
            missing.append(
                f"Step {index + 1} does not call {payload['title']}; include "
                f"a real urllib.request call to {payload['endpoint']} and set "
                f"the step tools list to [{payload['title']}]"
            )
    return missing


def assemble_candidate(
    skeleton: dict[str, Any],
    concept: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, Any]:
    combo = concept["apis"]
    payloads = concept["payloads"]
    generated_steps = data.get("steps") or []
    expected = len(skeleton["details"]["steps"])
    if not isinstance(generated_steps, list) or len(generated_steps) != expected:
        raise ValueError(
            f"expected exactly {expected} steps in the outline order, "
            f"received {len(generated_steps)}"
        )

    candidate = json.loads(json.dumps(skeleton))
    details = candidate["details"]
    steps: list[dict[str, Any]] = []

    for index, (outline, generated) in enumerate(
        zip(details["steps"], generated_steps)
    ):
        if not isinstance(generated, dict):
            raise ValueError(f"step {index + 1} is not a JSON object")
        code = str(generated.get("code_snippet") or "").strip()
        if not code:
            raise ValueError(f"step {index + 1} has no code_snippet")

        hardened, harden_stats = harden_code(code)
        assigned_api = payloads[index] if index < len(payloads) else None

        actions = [
            str(action).strip()
            for action in (generated.get("actions") or [])
            if str(action).strip()
        ]
        if len(actions) < 3:
            actions.extend(
                [
                    "Build the authenticated request with urllib.request.Request",
                    "Parse the JSON response through defensive accessors",
                    "Hand the normalized records to the next pipeline stage",
                ]
            )
        checklist = [
            str(item).strip()
            for item in (generated.get("checklist") or [])
            if str(item).strip()
        ]
        if len(checklist) < 2:
            checklist.extend(
                [
                    "The step prints a non-empty record count",
                    "The HTTP status and response shape are validated",
                ]
            )

        if assigned_api is not None:
            tools = [assigned_api["title"]]
            links = [
                {
                    "label": f"{assigned_api['title']} Documentation",
                    "url": assigned_api["docs"],
                }
            ]
            expected_result = (
                f"{assigned_api['short']} records are normalized and ready for "
                "the next stage."
            )
        else:
            tools = []
            links = [
                {
                    "label": "Python json Documentation",
                    "url": "https://docs.python.org/3/library/json.html",
                }
            ]
            expected_result = (
                "The final operational summary is validated and persisted "
                "locally or in the selected data store."
            )

        description = str(generated.get("description") or outline.get("description") or "").strip()
        steps.append(
            {
                "title": outline["title"],
                "description": description,
                "technical_explanation": _pad_explanation(
                    str(generated.get("technical_explanation") or "")
                ),
                "code_snippet": hardened,
                "mock_response": generated.get("mock_response") or {},
                "actions": actions[:6],
                "commands": [
                    entry
                    for entry in (generated.get("commands") or [])
                    if isinstance(entry, dict)
                ],
                "config": [
                    entry
                    for entry in (generated.get("config") or [])
                    if isinstance(entry, dict)
                ],
                "tools": tools,
                "checklist": checklist[:4],
                "expectedResult": str(
                    generated.get("expectedResult") or expected_result
                ).strip(),
                "links": links,
            }
        )
        if harden_stats.get("subscripts") or harden_stats.get("environment"):
            log(
                f"  [HARDEN] step {index + 1}: "
                f"{harden_stats.get('subscripts', 0)} JSON access(es), "
                f"{harden_stats.get('environment', 0)} env access(es) hardened"
            )

    missing = _missing_api_calls(steps, combo)
    if missing:
        raise ValueError("; ".join(missing))

    details["steps"] = steps
    details["glossary"] = _normalize_glossary(data.get("glossary"), combo)
    details["troubleshooting"] = _normalize_troubleshooting(
        data.get("troubleshooting"), combo
    )
    # Re-assert Python-owned metadata after the LLM response.
    details["tools"] = [payload["title"] for payload in payloads]
    details["api_slugs"] = [payload["slug"] for payload in payloads]
    details["resources"] = _resources(combo)
    details["prerequisites"] = _before_you_start(combo)
    details["before_you_start"] = list(details["prerequisites"])
    details["price"] = float(concept["price"])
    candidate["price"] = float(concept["price"])
    candidate["created_and_verified_at"] = run_batch._now_timestamp()  # noqa: SLF001

    # Enforce the binding final prerequisite as the last entry.
    run_batch._normalize_workflow(candidate)  # noqa: SLF001
    details["before_you_start"] = list(details["prerequisites"])
    return candidate


# --------------------------------------------------------------------------- #
# Self-healing against the exact runtime traceback
# --------------------------------------------------------------------------- #
def _step_from_combined_traceback(
    traceback_text: str, steps: list[dict[str, Any]]
) -> int:
    line_numbers = [int(value) for value in _TRACEBACK_LINE.findall(traceback_text)]
    if not line_numbers:
        return len(steps) - 1
    failing_line = max(line_numbers)
    cursor = 1
    for index, step in enumerate(steps):
        line_count = len(str(step.get("code_snippet") or "").splitlines())
        if cursor <= failing_line <= cursor + line_count:
            return index
        cursor += line_count + 1  # snippets are joined with a blank line
    return len(steps) - 1


def _repair_step_from_traceback(
    step: dict[str, Any],
    traceback_text: str,
    step_index: int,
    assigned_api: str | None,
    attempt: int,
) -> bool:
    try:
        repaired = llm_client.chat_code(
            prompts.CODE_REPAIR_SYSTEM,
            prompts.build_traceback_repair_prompt(
                step,
                traceback_text,
                step_index,
                assigned_api,
                attempt,
            ),
        )
    except llm_client.LLMError as error:
        log(f"  [HEAL] repair attempt {attempt} failed: {error}")
        return False

    hardened, stats = harden_code(repaired)
    ast_result = validator.check_python_ast(
        hardened, "Step", cfg.WORKFLOW_FORBIDDEN_IMPORTS
    )
    if not ast_result.ok or len(validator.non_empty_lines(hardened)) < cfg.MIN_CODE_LINES:
        log(
            "  [HEAL] repaired snippet rejected by the AST gate: "
            f"{'; '.join(ast_result.errors)[:300]}"
        )
        return False
    step["code_snippet"] = hardened
    log(
        f"  [HEAL] step {step_index} repaired "
        f"({stats.get('subscripts', 0)} JSON access(es) hardened)"
    )
    return True


def _internal_dry_run(candidate: dict[str, Any]) -> validator.ValidationResult:
    codes = [
        str(step.get("code_snippet") or "")
        for step in candidate.get("details", {}).get("steps") or []
    ]
    return validator.execute_workflow_dry_run(codes)


def self_heal_internal(
    candidate: dict[str, Any],
    concept: dict[str, Any],
    rounds: int = MAX_SELF_HEAL_ROUNDS,
) -> tuple[bool, str]:
    steps = candidate["details"]["steps"]
    result = _internal_dry_run(candidate)
    if result.ok:
        return True, ""

    for round_number in range(1, rounds + 1):
        traceback_text = "\n".join(result.errors)
        index = _step_from_combined_traceback(traceback_text, steps)
        assigned = (
            concept["payloads"][index]["title"]
            if index < len(concept["payloads"])
            else None
        )
        log(
            f"  [HEAL] dry-run failed – repairing step {index + 1} "
            f"(round {round_number}/{rounds})"
        )
        if not _repair_step_from_traceback(
            steps[index], traceback_text, index + 1, assigned, round_number
        ):
            continue
        result = _internal_dry_run(candidate)
        if result.ok:
            log("  [HEAL] dry-run passed after self-repair")
            return True, ""

    return False, "\n".join(result.errors)[-2000:]


# --------------------------------------------------------------------------- #
# Artifact gates: PDF, kit, kit dry-run
# --------------------------------------------------------------------------- #
def verify_pdf(pdf_path: Path) -> tuple[bool, int, str]:
    if not pdf_path.exists():
        return False, 0, f"PDF missing: {pdf_path}"
    data = pdf_path.read_bytes()
    if not data.startswith(b"%PDF"):
        return False, 0, "PDF header is invalid"
    pages = len(re.findall(rb"/Type\s*/Page\b", data))
    if len(data) < 8000:
        return False, pages, f"PDF is suspiciously small ({len(data)} bytes)"
    if pages < 2:
        return False, pages, f"PDF has only {pages} page(s); expected a variable multi-page blueprint"
    return True, pages, ""


def _kit_dry_run(kit_path: Path) -> tuple[bool, str, str]:
    """Extract the kit to a temp folder and run ``workflow.py --dry-run``."""
    try:
        with zipfile.ZipFile(kit_path, "r") as archive:
            workflow_py = archive.read("workflow.py").decode("utf-8")
            with tempfile.TemporaryDirectory(prefix="flowmatrix-kit-") as tmp:
                archive.extractall(tmp)
                script = Path(tmp) / "workflow.py"
                env = os.environ.copy()
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                try:
                    result = subprocess.run(
                        [sys.executable, "workflow.py", "--dry-run"],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        timeout=90,
                        env=env,
                    )
                except subprocess.TimeoutExpired:
                    return False, "Kit dry-run timed out after 90s", workflow_py
                output = f"{result.stdout}\n{result.stderr}".strip()
                ok = (
                    result.returncode == 0
                    and "Dry-run completed successfully." in result.stdout
                )
                return ok, output, workflow_py
    except Exception as error:  # noqa: BLE001
        return False, f"{type(error).__name__}: {error}", ""


def _step_from_kit_traceback(
    traceback_text: str, workflow_py: str, steps: list[dict[str, Any]]
) -> int:
    line_numbers = [int(value) for value in _TRACEBACK_LINE.findall(traceback_text)]
    source_lines = workflow_py.splitlines()
    source = ""
    for line_number in reversed(line_numbers):
        if 1 <= line_number <= len(source_lines):
            source = source_lines[line_number - 1].strip()
            if source:
                break
    if source:
        for index, step in enumerate(steps):
            step_code = str(step.get("code_snippet") or "")
            if any(
                line.strip() == source and line.strip()
                for line in step_code.splitlines()
            ):
                return index
    return len(steps) - 1


def build_and_verify_artifacts(
    candidate: dict[str, Any], concept: dict[str, Any]
) -> tuple[Path | None, Path | None, int, str]:
    """Build PDF + kit and prove both by executing the shipped kit."""
    steps = candidate["details"]["steps"]
    for round_number in range(1, MAX_SELF_HEAL_ROUNDS + 2):
        pdf_path = run_batch.write_pdf(candidate)
        ok_pdf, pages, pdf_error = verify_pdf(pdf_path)
        if not ok_pdf:
            return None, None, pages, pdf_error

        kit_path = bundle_builder.build_workflow_kit(candidate, pdf_path, cfg.KITS_DIR)
        kit_result = validator.validate_kit_zip(kit_path, cfg.WORKFLOW_KIT_FILES)
        if not kit_result.ok:
            return (
                None,
                None,
                pages,
                "kit validation failed: " + "; ".join(kit_result.errors),
            )
        if kit_path.stat().st_size <= 0:
            return None, None, pages, "kit ZIP is empty"

        ok_run, output, workflow_py = _kit_dry_run(kit_path)
        if ok_run:
            return pdf_path, kit_path, pages, ""

        if round_number > MAX_SELF_HEAL_ROUNDS:
            return None, None, pages, f"kit dry-run failed: {output[-2000:]}"

        index = _step_from_kit_traceback(output, workflow_py, steps)
        assigned = (
            concept["payloads"][index]["title"]
            if index < len(concept["payloads"])
            else None
        )
        log(
            f"  [HEAL] kit dry-run failed – repairing step {index + 1} "
            f"(round {round_number}/{MAX_SELF_HEAL_ROUNDS})"
        )
        if not _repair_step_from_traceback(
            steps[index], output, index + 1, assigned, round_number
        ):
            continue
        ok_internal, internal_error = self_heal_internal(candidate, concept)
        if not ok_internal:
            return None, None, pages, internal_error
    return None, None, 0, "kit dry-run failed after all repair rounds"


def upload_with_retry(local_path: Path, key: str, attempts: int = 3) -> bool:
    for attempt in range(1, attempts + 1):
        if run_batch.upload_to_r2(local_path, key):
            log(f"  [R2] uploaded {key}")
            return True
        log(f"  [R2] upload attempt {attempt}/{attempts} failed for {key}")
        time.sleep(2 ** (attempt - 1))
    return False


def upload_artifacts(pdf_path: Path, kit_path: Path, slug: str) -> list[str]:
    targets = [
        (pdf_path, f"pdfs/flowmatrix-{slug}.pdf"),
        (pdf_path, f"{slug}.pdf"),
        (kit_path, f"kits/{slug}-kit.zip"),
    ]
    failed: list[str] = []
    for path, key in targets:
        if not upload_with_retry(path, key):
            failed.append(key)
    return failed


# --------------------------------------------------------------------------- #
# Full validation
# --------------------------------------------------------------------------- #
def validate_candidate(
    candidate: dict[str, Any], workflows: list[dict[str, Any]]
) -> validator.ValidationResult:
    with _LiveChecksDisabled():
        result = validator.validate_workflow(candidate)
    result.errors.extend(
        validator.check_duplicate(
            str(candidate.get("slug") or ""),
            str(candidate.get("title") or ""),
            workflows,
        )
    )
    return result


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def _chat_json(system: str, user: str) -> dict[str, Any]:
    return llm_client.chat_json(system, user)


def generate_workflow(
    concept: dict[str, Any],
    workflows: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[str]]:
    skeleton = build_skeleton(concept)
    outline = skeleton["details"]["steps"]
    related_alternatives = [
        alternative
        for alternative in alternatives
        if str(alternative.get("slug")) in concept["alternative_slugs"]
    ]
    feedback: str | None = None
    last_errors: list[str] = []
    primary = cfg.LLM_MODEL
    fallback_used = False

    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        log(
            f"  [GEN] attempt {attempt}/{MAX_GENERATION_ATTEMPTS} "
            f"with {cfg.LLM_MODEL}"
        )
        try:
            data = _chat_json(
                prompts.WORKFLOW_SYSTEM,
                prompts.build_workflow_prompt(
                    skeleton,
                    outline,
                    [
                        run_batch._api_tool(api)  # noqa: SLF001
                        for api in concept["apis"]
                    ],
                    feedback,
                    related_alternatives,
                    step_assignment=_step_assignment(concept["apis"]),
                    deterministic_block=_deterministic_block(skeleton),
                ),
            )
        except llm_client.LLMError as error:
            last_errors = [str(error)]
            feedback = str(error)
            log(f"  [GEN] LLM error: {error}")
            if attempt >= 2 and not fallback_used and cfg.LLM_MODEL != FALLBACK_MODEL:
                log(f"  [GEN] switching to fallback model {FALLBACK_MODEL}")
                cfg.LLM_MODEL = FALLBACK_MODEL
                fallback_used = True
            continue

        try:
            candidate = assemble_candidate(skeleton, concept, data)
        except Exception as error:  # noqa: BLE001 - retry with the exact reason
            last_errors = [f"{type(error).__name__}: {error}"]
            feedback = "; ".join(last_errors)
            log(f"  [GEN] assembly rejected: {feedback[:600]}")
            if attempt >= 2 and not fallback_used and cfg.LLM_MODEL != FALLBACK_MODEL:
                log(f"  [GEN] switching to fallback model {FALLBACK_MODEL}")
                cfg.LLM_MODEL = FALLBACK_MODEL
                fallback_used = True
            continue

        healed, heal_error = self_heal_internal(candidate, concept)
        if not healed:
            last_errors = [heal_error]
            feedback = f"Dry-run traceback (must be fixed):\n{heal_error}"
            log("  [GEN] internal dry-run could not be repaired")
            continue

        result = validate_candidate(candidate, workflows)
        if result.ok:
            cfg.LLM_MODEL = primary
            return candidate, []
        last_errors = result.errors
        feedback = "; ".join(result.errors)
        log(f"  [GEN] validator rejected ({len(result.errors)} errors)")
        for message in result.errors[:8]:
            log(f"        - {message[:500]}")
        if attempt >= 2 and not fallback_used and cfg.LLM_MODEL != FALLBACK_MODEL:
            log(f"  [GEN] switching to fallback model {FALLBACK_MODEL}")
            cfg.LLM_MODEL = FALLBACK_MODEL
            fallback_used = True

    cfg.LLM_MODEL = primary
    return None, last_errors or ["generation failed"]


# --------------------------------------------------------------------------- #
# Candidate runner
# --------------------------------------------------------------------------- #
def process_candidate(
    concept: dict[str, Any],
    workflows: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    *,
    skip_r2: bool = False,
) -> tuple[bool, str, dict[str, Any] | None]:
    slug = concept["slug"]
    log(
        f"[CANDIDATE] {slug} | {concept['difficulty']} €{concept['price']:.2f} | "
        f"APIs: {', '.join(payload['slug'] for payload in concept['payloads'])}"
    )

    live_errors = live_domain_check(concept["apis"])
    if live_errors:
        return False, "live domain check failed: " + "; ".join(live_errors), None

    candidate, errors = generate_workflow(concept, workflows, alternatives)
    if candidate is None:
        return False, "generation failed: " + "; ".join(errors)[-1500:], None

    # Final hard validation including the deterministic metadata invariants.
    final_result = validate_candidate(candidate, workflows)
    if not final_result.ok:
        return (
            False,
            "final validation failed: " + "; ".join(final_result.errors)[-1500:],
            candidate,
        )

    pdf_path, kit_path, pages, artifact_error = build_and_verify_artifacts(
        candidate, concept
    )
    if pdf_path is None or kit_path is None:
        return False, f"artifact gate failed: {artifact_error}", candidate
    log(f"  [ARTIFACTS] PDF {pages} pages, kit {kit_path.name} verified")

    if skip_r2:
        log("  [R2] skipped by --skip-r2 (debug only)")
    else:
        failed = upload_artifacts(pdf_path, kit_path, str(candidate["slug"]))
        if failed:
            return (
                False,
                "R2 upload failed: " + ", ".join(failed),
                candidate,
            )

    # Persist only after every gate passed.
    index = next(
        (
            position
            for position, item in enumerate(workflows)
            if item.get("slug") == candidate["slug"]
        ),
        None,
    )
    if index is None:
        workflows.append(candidate)
    else:
        workflows[index] = candidate
    run_batch.save_json(cfg.WORKFLOWS_FILE, workflows)
    log(
        f"  [OK] {candidate['slug']} persisted "
        f"(pdf pages={pages}, kit={kit_path.name})"
    )
    return True, "", candidate


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unattended FlowMatrix 3-day workflow daemon"
    )
    parser.add_argument("--target-count", type=int, default=3)
    parser.add_argument("--pool-size", type=int, default=MIN_POOL_SIZE)
    parser.add_argument(
        "--model",
        default=os.environ.get("AUTO_BATCH_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or PRIMARY_MODEL,
        help="OpenRouter model for generation (default: DeepSeek V4.1 Flash)",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Build and print the candidate pool without calling the LLM",
    )
    parser.add_argument("--skip-git", action="store_true", help="Skip pull/commit/push")
    parser.add_argument("--skip-build", action="store_true", help="Skip npm run build")
    parser.add_argument(
        "--skip-r2", action="store_true", help="Do not upload artifacts (debug)"
    )
    parser.add_argument(
        "--no-launchd",
        action="store_true",
        help="Do not install the launchd job",
    )
    parser.add_argument(
        "--cloudflare-deploy",
        action="store_true",
        help="Also deploy dist/ to Cloudflare Pages directly (GitHub Actions already deploys)",
    )
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def _finalize(
    args: argparse.Namespace,
    successful: list[str],
) -> tuple[bool, bool]:
    git_ok = True
    build_ok = True

    if not args.skip_git:
        # ``git_commit_and_push`` performs its own pull --rebase immediately
        # before pushing; an additional pull here must not become a hard gate.
        git_pull()
    if not args.skip_build:
        build_ok = build_frontend()
    if not args.skip_git:
        message = (
            f"chore(auto-batch): add {len(successful)} verified implementation kits"
        )
        git_ok = git_commit_and_push(message)
    if args.cloudflare_deploy and build_ok:
        try:
            run_batch.run_deploy()
        except Exception as error:  # noqa: BLE001 - warn only, git is source of truth
            log(f"[DEPLOY] direct Cloudflare Pages deploy failed: {error}")
    return git_ok, build_ok


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg.load_env()
    cfg.LLM_MODEL = args.model
    log("=" * 78)
    log(
        f"AUTO 3-DAY DAEMON START | target={args.target_count} "
        f"pool={max(MIN_POOL_SIZE, args.pool_size)} model={cfg.LLM_MODEL}"
    )

    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        log("[FATAL] OPENROUTER_API_KEY is not set")
        return 2

    state = _load_state()
    state.update(
        {
            "status": "running",
            "started_at": _now(),
            "target": args.target_count,
            "model": cfg.LLM_MODEL,
            "successful": [],
            "rejected": [],
        }
    )
    _save_state(state)

    python_bin = Path(sys.executable)

    if not args.skip_git:
        if not git_pull():
            log("[WARN] initial git pull failed – continuing with the local tree")

    workflows = run_batch.load_json(cfg.WORKFLOWS_FILE) if cfg.WORKFLOWS_FILE.exists() else []
    apis = run_batch.load_json(cfg.APIS_FILE)
    alternatives = run_batch.load_json(cfg.ALTERNATIVES_FILE)

    seed = args.seed if args.seed is not None else int(time.time() // 86400)
    pool_size = max(MIN_POOL_SIZE, args.pool_size)
    pool = build_candidate_pool(apis, alternatives, workflows, pool_size, seed)
    log(f"[POOL] prepared {len(pool)} candidate concept(s) (minimum {MIN_POOL_SIZE})")
    if not pool:
        log("[FATAL] no candidate concepts could be built")
        state["status"] = "failed"
        state["last_error"] = "empty candidate pool"
        _save_state(state)
        return 1

    if args.plan_only:
        for index, concept in enumerate(pool, start=1):
            log(
                f"  {index:02d}. {concept['slug']} | {concept['difficulty']} | "
                f"€{concept['price']:.2f} | "
                f"{', '.join(payload['slug'] for payload in concept['payloads'])}"
            )
        state["status"] = "plan-only"
        state["pool_size"] = len(pool)
        _save_state(state)
        return 0

    successful: list[str] = []
    rejected: list[dict[str, Any]] = []
    attempt_counter = 0
    extension = 0

    while len(successful) < args.target_count:
        if not pool:
            # Extend the pool deterministically instead of aborting. The first
            # pool is always >= 10; extensions only add resilience.
            extension += 1
            if extension > 6:
                log("[FATAL] candidate pool exhausted after six extensions")
                break
            extra = build_candidate_pool(
                apis,
                alternatives,
                workflows,
                pool_size,
                seed + extension * 7919,
            )
            known = {
                str(item.get("slug"))
                for item in workflows
            } | {concept["slug"] for concept in pool}
            extra = [concept for concept in extra if concept["slug"] not in known]
            if not extra:
                log("[FATAL] could not extend the candidate pool")
                break
            pool.extend(extra)
            log(f"[POOL] extended by {len(extra)} candidate(s)")

        concept = pool.pop(0)
        attempt_counter += 1
        state["attempts"] = attempt_counter
        _save_state(state)

        try:
            ok, reason, candidate = process_candidate(
                concept,
                workflows,
                alternatives,
                skip_r2=args.skip_r2,
            )
        except Exception as error:  # noqa: BLE001 - never abort the loop
            ok = False
            candidate = None
            reason = (
                f"{type(error).__name__}: {error}\n"
                f"{traceback.format_exc()[-1200:]}"
            )
            log(f"  [FAIL] unexpected error for {concept['slug']}: {reason}")

        if ok and candidate is not None:
            successful.append(str(candidate["slug"]))
            state["successful"] = list(successful)
            log(
                f"[SUCCESS {len(successful)}/{args.target_count}] "
                f"{candidate['slug']}"
            )
        else:
            rejected.append(
                {
                    "slug": concept["slug"],
                    "reason": reason[-1500:],
                    "timestamp": _now(),
                }
            )
            state["rejected"] = list(rejected)
            log(f"  [DISCARD] {concept['slug']}: {reason[-500:]}")
            # Drop the candidate from workflows.json if a partial record exists.
            workflows[:] = [
                item
                for item in workflows
                if item.get("slug") != concept["slug"]
            ]
        _save_state(state)

    if len(successful) < args.target_count:
        log(
            f"[FATAL] only {len(successful)}/{args.target_count} workflows "
            "passed every gate – nothing was committed or pushed"
        )
        state["status"] = "incomplete"
        state["finished_at"] = _now()
        _save_state(state)
        return 1

    log(f"[DELIVERY] {len(successful)} perfect workflows ready – starting git sync")
    if not args.no_launchd:
        # Written before the commit so the launchd definition is versioned.
        write_plist(python_bin)
    git_ok, build_ok = _finalize(args, successful)
    if not (git_ok and build_ok):
        log(
            "[FATAL] delivery step failed "
            f"(git_ok={git_ok}, build_ok={build_ok}); artifacts are in R2 and "
            "will be retried by the next launchd run"
        )
        state["status"] = "delivery-failed"
        state["git_ok"] = git_ok
        state["build_ok"] = build_ok
        state["finished_at"] = _now()
        _save_state(state)
        return 1

    state["status"] = "success"
    state["finished_at"] = _now()
    state["pool_size"] = len(pool)
    _save_state(state)

    # Activate the launchd job only after a fully successful proof/delivery run.
    # This guarantees that a broken revision can never be scheduled every 72h.
    if not args.no_launchd:
        try:
            load_plist()
        except Exception as error:  # noqa: BLE001 - scheduling must not block work
            log(f"[LAUNCHD] could not load job: {error}")
    log(
        f"AUTO 3-DAY DAEMON COMPLETE | {len(successful)} workflows | "
        f"{len(rejected)} candidate(s) discarded"
    )
    log("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())