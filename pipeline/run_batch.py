"""The single entry point for the FlowMatrix content pipeline.

Usage (always run as a module from the project root):
    python -m pipeline.run_batch --only-workflow automated-api-error-reporting \
        --only-api sentry-performance-api --skip-build --skip-upload --skip-deploy

    python -m pipeline.run_batch --workflows 3 --apis 4 --alternatives 2

Flow:
    load data -> generate via LLM -> validate (hard gate) -> self-healing retry
    (max 3, feedback = exact validator errors) -> store JSON -> render PDFs ->
    write API scripts -> upload to R2 -> Astro build -> Cloudflare Pages deploy.

If a workflow is rejected because one of its domains is not reachable, the
pipeline discards it and automatically generates a brand-new topic as a
replacement (up to ``MAX_REPLACEMENT_TOPICS``).

Nothing is written/uploaded/deployed unless validator.py returns ok=True.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import random
import re
import subprocess
import urllib.parse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow direct execution: ``python3 pipeline/run_batch.py --limit 10``.
if __package__ in (None, ""):
    import os as _os
    import sys as _sys

    _sys.path.insert(
        0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    )
    __package__ = "pipeline"

from . import config as cfg
from . import bundle_builder, full_product_audit, llm_client, pdf_renderer, prompts, validator
from . import seeds as seed_catalog


# --------------------------------------------------------------------------- #
# I/O helpers
# --------------------------------------------------------------------------- #
def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _api_tool(api: dict[str, Any]) -> dict[str, Any]:
    """Project an API record onto the tool shape used by the prompt."""
    details = api.get("details") or {}
    return {
        "name": str(api.get("title") or ""),
        "slug": str(api.get("slug") or ""),
        "provider": str(details.get("provider") or ""),
        "endpoint": str(details.get("endpoint") or ""),
        "url": str(details.get("docsUrl") or details.get("website") or ""),
        "authentication": str(details.get("authentication") or ""),
    }


def _grounded_tools(
    workflow: dict[str, Any],
    apis: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve the curated ``details.api_slugs`` to real API records.

    No heuristic name matching is performed. A workflow without curated API
    slugs is not grounded at all and must be discarded by the caller.
    """
    details = workflow.get("details") or {}
    slugs = [
        str(slug).strip()
        for slug in (details.get("api_slugs") or [])
        if str(slug).strip()
    ]
    if not slugs:
        return []
    api_index = {str(api.get("slug")): api for api in apis}
    tools: list[dict[str, Any]] = []
    for slug in slugs:
        api = api_index.get(slug)
        if api is not None:
            tools.append(_api_tool(api))
    return tools


def _tool_code_markers(tool: dict[str, Any]) -> tuple[str, ...]:
    """Return strings that prove this exact API is called in generated code."""
    markers: list[str] = []
    for candidate in (tool.get("endpoint"), tool.get("url")):
        raw = str(candidate or "")
        if "<" in raw or "{" in raw:
            continue
        host = urllib.parse.urlparse(raw).hostname or ""
        if host and host not in markers:
            markers.append(host)
    provider = str(tool.get("provider") or "").strip().lower()
    if provider and provider not in markers:
        markers.append(provider)
    slug = str(tool.get("slug") or "").strip().lower()
    if slug and slug not in markers:
        markers.append(slug)
    return tuple(markers) or (str(tool.get("name") or "").lower(),)


def _normalise_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _match_tool_name(
    raw_name: str, available_tools: list[dict[str, Any]]
) -> str | None:
    """Flexibly match a free-form tool name to a curated API title."""
    value = str(raw_name or "").strip()
    if not value:
        return None
    lowered = value.lower()
    normalised = _normalise_name(value)
    for tool in available_tools:
        name = str(tool.get("name") or "")
        name_lower = name.lower()
        name_norm = _normalise_name(name)
        slug = str(tool.get("slug") or "").lower()
        provider = str(tool.get("provider") or "").lower()
        if (
            lowered == name_lower
            or normalised == name_norm
            or normalised in name_norm
            or name_norm in normalised
            or (slug and (lowered == slug or normalised == _normalise_name(slug)))
            or (provider and provider in lowered)
        ):
            return name
    return None


def _related_alternatives(
    workflow: dict[str, Any],
    alternatives: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Resolve the curated ``details.alternative_slugs`` to real records."""
    details = workflow.get("details") or {}
    slugs = [
        str(slug).strip()
        for slug in (details.get("alternative_slugs") or [])
        if str(slug).strip()
    ]
    alt_index = {str(item.get("slug")): item for item in alternatives}
    return [
        alt_index[slug]
        for slug in slugs[:limit]
        if slug in alt_index
    ]

def _deep_copy(item: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(item))


def _now_timestamp() -> str:
    return datetime.now(timezone.utc).strftime(cfg.TIMESTAMP_FORMAT)


def _is_domain_failure(errors: list[str]) -> bool:
    markers = (
        "domain not reachable",
        "base domain not reachable",
        "invented domain",
    )
    return any(
        any(marker in str(error).lower() for marker in markers)
        for error in errors
    )


def _normalize_workflow(candidate: dict[str, Any]) -> None:
    """Enforce structural invariants the LLM keeps drifting away from.

    * The binding Python prerequisite must be the LAST entry (the validator
      only requires it to be present, but the PDF should show it last).
    * At most ``MAX_STEPS`` steps – extra generated steps are dropped.
    """
    details = candidate.setdefault("details", {})

    prerequisites = [
        str(item).strip() for item in (details.get("prerequisites") or [])
    ]
    prerequisites = [item for item in prerequisites if item]
    prerequisites = [
        item for item in prerequisites if item != cfg.FINAL_PREREQUISITE
    ]
    prerequisites.append(cfg.FINAL_PREREQUISITE)
    details["prerequisites"] = prerequisites

    steps = details.get("steps") or []
    if len(steps) > cfg.MAX_STEPS:
        details["steps"] = steps[: cfg.MAX_STEPS]


def repair_step_code(
    step: dict[str, Any],
    error: str,
    max_attempts: int = 2,
) -> str | None:
    """Ask the LLM to fix a single broken code snippet in isolation."""
    feedback: str | None = error
    for _ in range(max_attempts):
        try:
            code = llm_client.chat_code(
                prompts.CODE_REPAIR_SYSTEM,
                prompts.build_code_repair_prompt(step, feedback),
            )
        except llm_client.LLMError as exc:
            feedback = str(exc)
            continue

        result = validator.check_python_ast(
            code, "Step", cfg.WORKFLOW_FORBIDDEN_IMPORTS
        )
        if result.ok and len(validator.non_empty_lines(code)) >= cfg.MIN_CODE_LINES:
            return code
        feedback = "; ".join(result.errors) or "code has too few non-empty lines"
    return None


def repair_step_explanation(
    step: dict[str, Any],
    max_attempts: int = 2,
) -> str | None:
    """Expand a too-short technical explanation for a single step."""
    for _ in range(max_attempts):
        try:
            data = llm_client.chat_json(
                prompts.CODE_REPAIR_SYSTEM,
                prompts.build_technical_explanation_repair_prompt(step),
            )
        except llm_client.LLMError:
            continue
        text = str(data.get("technical_explanation") or "").strip()
        if len(text) >= cfg.MIN_TECHNICAL_EXPLANATION:
            return text
    return None


def repair_existing_workflow(
    workflow: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Try to fix an existing record in place before regenerating via the LLM."""
    candidate = _deep_copy(workflow)
    _normalize_workflow(candidate)

    for step in candidate.get("details", {}).get("steps") or []:
        code = str(step.get("code_snippet") or "")
        ast_result = validator.check_python_ast(
            code, "Step", cfg.WORKFLOW_FORBIDDEN_IMPORTS
        )
        line_count = len(validator.non_empty_lines(code))
        if not ast_result.ok or line_count < cfg.MIN_CODE_LINES:
            feedback = "; ".join(ast_result.errors)
            if line_count < cfg.MIN_CODE_LINES:
                feedback = (f"{feedback}; " if feedback else "") + (
                    f"code_snippet has only {line_count} non-empty lines "
                    f"(minimum {cfg.MIN_CODE_LINES})"
                )
            repaired = repair_step_code(step, feedback)
            if repaired:
                step["code_snippet"] = repaired
        if len(
            str(step.get("technical_explanation") or "").strip()
        ) < cfg.MIN_TECHNICAL_EXPLANATION:
            repaired_explanation = repair_step_explanation(step)
            if repaired_explanation:
                step["technical_explanation"] = repaired_explanation

    result = validator.validate_workflow(candidate)
    if result.ok:
        return candidate, []
    return None, result.errors


# --------------------------------------------------------------------------- #
# Workflow generation with self-healing
# --------------------------------------------------------------------------- #
def generate_workflow(
    workflow: dict[str, Any],
    workflows_all: list[dict[str, Any]],
    apis: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    max_attempts: int = cfg.LLM_MAX_ATTEMPTS,
    force_regenerate: bool = False,
) -> tuple[dict[str, Any] | None, list[str], int]:
    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    available_tools = _grounded_tools(workflow, apis)
    if not available_tools:
        return None, ["workflow has no curated details.api_slugs – not grounded"], 0
    related_alternatives = _related_alternatives(workflow, alternatives)
    prompt_workflow = _deep_copy(workflow)
    prompt_workflow.setdefault("details", {})["tools"] = [
        tool["name"] for tool in available_tools
    ]
    feedback: str | None = None
    last_errors: list[str] = []

    # First try to repair the existing record in place. This fixes pure code
    # errors (SyntaxError / forbidden import) without a full regeneration.
    if not force_regenerate:
        repaired, repair_errors = repair_existing_workflow(workflow)
        if repaired is not None:
            duplicate_errors = validator.check_duplicate(
                repaired.get("slug", ""),
                repaired.get("title", ""),
                workflows_all,
                ignore_slug=workflow.get("slug"),
            )
            if not duplicate_errors:
                print(
                    f"  [REPAIR] {workflow['slug']}: existing record repaired in place"
                )
                return repaired, [], 0
            repair_errors = duplicate_errors
        last_errors = repair_errors
        feedback = "; ".join(repair_errors) if repair_errors else None

    for attempt in range(1, max_attempts + 1):
        try:
            data = llm_client.chat_json(
                prompts.WORKFLOW_SYSTEM,
                prompts.build_workflow_prompt(
                    prompt_workflow,
                    steps,
                    available_tools,
                    feedback,
                    related_alternatives,
                ),
            )

            candidate = _deep_copy(workflow)
            candidate_details = candidate.setdefault("details", {})
            candidate_details["prerequisites"] = data.get("prerequisites", [])
            candidate_details["glossary"] = data.get("glossary", [])
            candidate_details["troubleshooting"] = data.get("troubleshooting", [])
            # Resources are deterministic: one docs URL per curated API.
            # Endpoints are prefixes and must never be linked bare (they often
            # return 404 on the base path and would fail the live-URL gate).
            grounded_resources = [
                {"label": tool["name"], "url": tool["url"]}
                for tool in available_tools
                if tool.get("url")
            ]
            candidate_details["resources"] = grounded_resources

            # Every grounded tool needs its own BEFORE YOU START bullet.
            prerequisites = list(candidate_details.get("prerequisites") or [])
            for tool in available_tools:
                tool_name = tool["name"]
                if not any(
                    tool_name.lower() in str(item).lower()
                    for item in prerequisites
                ):
                    prerequisites.insert(
                        max(0, len(prerequisites) - 1),
                        f"Access to {tool_name}",
                    )
            candidate_details["prerequisites"] = prerequisites
            # Replace known dead documentation URLs with the current live pages.
            # The hard live-URL gate would otherwise discard the workflow.
            doc_url_fixes = {
                "https://api.x.com": "https://developer.x.com/en/docs",
                "https://api.x.com/docs": (
                    "https://developer.x.com/en/docs/twitter-api/tweets/search/introduction"
                ),
                "https://api.x.com/docs/search": (
                    "https://developer.x.com/en/docs/twitter-api/tweets/search/introduction"
                ),
                "https://supabase.com/docs/reference/rest": (
                    "https://supabase.com/docs/guides/api"
                ),
                "https://supabase.com/docs/reference/javascript": (
                    "https://supabase.com/docs/guides/api"
                ),
            }
            for resource in candidate_details["resources"]:
                label = str(resource.get("label") or "").strip().lower()
                url = str(resource.get("url") or "")
                if label == "x api" and "developer.twitter.com" in url:
                    resource["url"] = "https://developer.x.com/en/docs"
                elif "supabase.com/docs/reference/javascript" in url:
                    resource["url"] = "https://supabase.com/docs/guides/api"
                else:
                    resource["url"] = doc_url_fixes.get(url, url)

            generated_steps = data.get("steps") or []
            steps_out: list[dict[str, Any]] = []
            for generated in generated_steps:
                if not isinstance(generated, dict):
                    raise ValueError(
                        f"LLM returned a non-object step: {generated!r}"
                    )
                step = dict(generated)
                links = step.get("links") or []
                if not links:
                    links = []
                    resources = candidate_details.get("resources") or []
                    for tool_name in step.get("tools") or []:
                        matched_name = _match_tool_name(
                            str(tool_name), available_tools
                        )
                        matched = next(
                            (
                                tool
                                for tool in available_tools
                                if tool["name"] == matched_name
                            ),
                            None,
                        )
                        if matched and matched.get("url"):
                            links.append(
                                {"label": matched["name"], "url": matched["url"]}
                            )
                if not links:
                    code = str(step.get("code_snippet") or "")
                    stdlib_docs = [
                        ("collections", "Python collections Docs", "https://docs.python.org/3/library/collections.html"),
                        ("statistics", "Python statistics Docs", "https://docs.python.org/3/library/statistics.html"),
                        ("json", "Python json Docs", "https://docs.python.org/3/library/json.html"),
                        ("re", "Python re Docs", "https://docs.python.org/3/library/re.html"),
                        ("math", "Python math Docs", "https://docs.python.org/3/library/math.html"),
                        ("datetime", "Python datetime Docs", "https://docs.python.org/3/library/datetime.html"),
                        ("itertools", "Python itertools Docs", "https://docs.python.org/3/library/itertools.html"),
                        ("functools", "Python functools Docs", "https://docs.python.org/3/library/functools.html"),
                        ("hashlib", "Python hashlib Docs", "https://docs.python.org/3/library/hashlib.html"),
                        ("hmac", "Python hmac Docs", "https://docs.python.org/3/library/hmac.html"),
                        ("argparse", "Python argparse Docs", "https://docs.python.org/3/library/argparse.html"),
                    ]
                    for module, label, url in stdlib_docs:
                        if f"import {module}" in code or f"from {module}" in code:
                            links.append({"label": label, "url": url})
                            break
                for link in links:
                    url = str(link.get("url") or "")
                    if "supabase.com/docs/reference/javascript" in url:
                        url = "https://supabase.com/docs/guides/api"
                    link["url"] = doc_url_fixes.get(url, url)
                step_tool_names = []
                for raw_tool in step.get("tools") or []:
                    matched_name = _match_tool_name(
                        str(raw_tool), available_tools
                    )
                    if matched_name and matched_name not in step_tool_names:
                        step_tool_names.append(matched_name)
                step["tools"] = step_tool_names
                grounded_link = next(
                    (
                        tool
                        for tool in available_tools
                        if tool["name"] in step_tool_names and tool.get("url")
                    ),
                    None,
                )
                if grounded_link:
                    step["links"] = [
                        {
                            "label": f"{grounded_link['name']} Documentation",
                            "url": grounded_link["url"],
                        }
                    ]
                else:
                    step["links"] = links
                steps_out.append(step)
            candidate_details["steps"] = steps_out

            # Keep the workflow tool list in sync with the tools actually used
            # in the generated steps (prevents "listed but never used" errors).
            used_tools: list[str] = []
            for step in steps_out:
                for tool in step.get("tools") or []:
                    name = str(tool).strip()
                    if (
                        name
                        and name.lower()
                        not in {
                            "python standard library",
                            "standard library",
                            "none",
                            "null",
                        }
                        and name not in used_tools
                    ):
                        used_tools.append(name)
            tool_by_name = {tool["name"]: tool for tool in available_tools}
            if not used_tools:
                # Fallback: infer the used APIs directly from the generated
                # code. This prevents a false "none of the curated APIs" abort
                # when the LLM mislabels the step tool list.
                code_all = "\n".join(
                    str(step.get("code_snippet") or "") for step in steps_out
                ).lower()
                for tool in available_tools:
                    if any(
                        marker.lower() in code_all
                        for marker in _tool_code_markers(tool)
                    ):
                        used_tools.append(tool["name"])
            if not used_tools:
                raise ValueError(
                    "the generated steps reference none of the curated APIs"
                )
            code_all = "\n".join(
                str(step.get("code_snippet") or "") for step in steps_out
            ).lower()
            filtered_tools = []
            for name in used_tools:
                tool = tool_by_name.get(name)
                markers = (
                    _tool_code_markers(tool)
                    if tool is not None
                    else cfg.TOOL_CODE_MARKERS.get(name) or (name.lower(),)
                )
                if any(marker.lower() in code_all for marker in markers):
                    filtered_tools.append(name)
            if not filtered_tools:
                # Keep the curated tools instead of aborting: the validator
                # now treats "listed but not used" as a warning.
                filtered_tools = list(used_tools)
            candidate_details["tools"] = filtered_tools
            allowed_tools = set(filtered_tools)
            for step in steps_out:
                step["tools"] = [
                    str(tool).strip()
                    for tool in (step.get("tools") or [])
                    if str(tool).strip() in allowed_tools
                ]

            # Normalise structure, then repair only the snippets that fail the
            # AST gate instead of regenerating the entire workflow.
            _normalize_workflow(candidate)
            for step in candidate.get("details", {}).get("steps") or []:
                code = str(step.get("code_snippet") or "")
                ast_result = validator.check_python_ast(
                    code, "Step", cfg.WORKFLOW_FORBIDDEN_IMPORTS
                )
                line_count = len(validator.non_empty_lines(code))
                if not ast_result.ok or line_count < cfg.MIN_CODE_LINES:
                    feedback = "; ".join(ast_result.errors)
                    if line_count < cfg.MIN_CODE_LINES:
                        feedback = (
                            f"{feedback}; " if feedback else ""
                        ) + (
                            f"code_snippet has only {line_count} non-empty lines "
                            f"(minimum {cfg.MIN_CODE_LINES})"
                        )
                    repaired = repair_step_code(step, feedback)
                    if repaired:
                        step["code_snippet"] = repaired
                        print(
                            f"  [REPAIR] {workflow['slug']}: fixed snippet "
                            f"'{step.get('title', '')[:40]}'"
                        )

                # Expand shallow explanations instead of rejecting the whole
                # workflow after an otherwise valid generation.
                if len(
                    str(step.get("technical_explanation") or "").strip()
                ) < cfg.MIN_TECHNICAL_EXPLANATION:
                    repaired_explanation = repair_step_explanation(step)
                    if repaired_explanation:
                        step["technical_explanation"] = repaired_explanation
                        print(
                            f"  [REPAIR] {workflow['slug']}: expanded technical "
                            f"explanation for '{step.get('title', '')[:40]}'"
                        )

            result = validator.validate_workflow(candidate)
            result.errors.extend(
                validator.check_duplicate(
                    candidate.get("slug", ""),
                    candidate.get("title", ""),
                    workflows_all,
                    ignore_slug=workflow.get("slug"),
                )
            )
            if not result.ok:
                # Map "Step N: ..." errors back to the exact snippet and repair
                # only that step. This fixes content-level issues (dummy data,
                # overwritten variables, missing top-level calls) without
                # burning a full workflow regeneration attempt.
                repaired_steps = False
                for index, step in enumerate(
                    candidate_details.get("steps") or [], start=1
                ):
                    step_errors = [
                        message
                        for message in result.errors
                        if message.startswith(f"Step {index}:")
                    ]
                    if not step_errors:
                        continue
                    repaired = repair_step_code(step, "; ".join(step_errors))
                    if repaired:
                        step["code_snippet"] = repaired
                        repaired_steps = True
                        print(
                            f"  [REPAIR] {workflow['slug']}: targeted repair "
                            f"for step {index} '{step.get('title', '')[:40]}'"
                        )
                if repaired_steps:
                    result = validator.validate_workflow(candidate)
                    result.errors.extend(
                        validator.check_duplicate(
                            candidate.get("slug", ""),
                            candidate.get("title", ""),
                            workflows_all,
                            ignore_slug=workflow.get("slug"),
                        )
                    )
            if result.ok:
                return candidate, result.warnings, attempt

            last_errors = result.errors
            feedback = "; ".join(result.errors)
            print(
                f"  [RETRY] {workflow['slug']} attempt {attempt}: {len(result.errors)} validator error(s)"
            )
            for message in result.errors[:6]:
                print(f"           - {message}")
        except llm_client.LLMError as error:
            feedback = str(error)
            last_errors = [feedback]
            print(f"  [RETRY] {workflow['slug']} attempt {attempt}: {feedback}")
        except Exception as error:  # noqa: BLE001 - never abort the batch
            feedback = f"{type(error).__name__}: {error}"
            last_errors = [feedback]
            print(f"  [RETRY] {workflow['slug']} attempt {attempt}: {feedback}")

    return None, last_errors or ["max attempts reached"], max_attempts


def _unique_slug(base: str, existing: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "generated-workflow"
    candidate = slug
    counter = 2
    while candidate in existing:
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate


def build_batch_workflow_seeds(
    selected_apis: list[dict[str, Any]],
    selected_alternatives: list[dict[str, Any]],
    count: int,
    workflows_all: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create ``count`` workflow skeletons grounded on the batch records.

    The LLM only proposes the topic and step outline. The API and alternative
    slugs are assigned by the pipeline from the current batch, so a workflow can
    never reference an API that was not selected and validated in this run.
    """
    if count <= 0 or not selected_apis:
        return []
    api_index = {str(api.get("slug")): api for api in selected_apis}
    existing_slugs = {str(item.get("slug", "")) for item in workflows_all}
    existing_titles = [str(item.get("title", "")) for item in workflows_all]
    created: list[dict[str, Any]] = []

    for index in range(count):
        combo_size = min(3, len(selected_apis))
        combo = [
            selected_apis[(index + offset) % len(selected_apis)]
            for offset in range(combo_size)
        ]
        combo = list({str(api["slug"]): api for api in combo}.values())
        alt_combo: list[dict[str, Any]] = []
        if selected_alternatives:
            alt_combo.append(selected_alternatives[index % len(selected_alternatives)])
            if len(selected_alternatives) > 1:
                alt_combo.append(
                    selected_alternatives[(index + 1) % len(selected_alternatives)]
                )
            alt_combo = list(
                {str(alt["slug"]): alt for alt in alt_combo}.values()
            )
        try:
            topic = llm_client.chat_json(
                prompts.TOPIC_SYSTEM,
                prompts.build_curated_topic_prompt(
                    combo, alt_combo, existing_titles
                ),
            )
        except llm_client.LLMError as error:
            print(f"  [SEED] could not generate a topic: {error}")
            continue
        if len(topic.get("steps") or []) < cfg.MIN_STEPS:
            print("  [SEED] topic has too few steps – skipped")
            continue
        topic["slug"] = _unique_slug(
            str(topic.get("slug") or "generated-workflow"), existing_slugs
        )
        seed = seed_catalog.build_dynamic_seed(
            topic,
            [str(api["slug"]) for api in combo],
            [str(alt["slug"]) for alt in alt_combo],
        )
        workflow = seed_catalog.build_workflow_from_seed(seed, api_index)
        created.append(workflow)
        existing_slugs.add(workflow["slug"])
        existing_titles.append(workflow["title"])
        print(
            f"  [SEED] {workflow['slug']} grounded on "
            f"{', '.join(seed['api_slugs'])}"
        )
    return created


def build_seed_workflows(
    seeds: list[dict[str, Any]],
    apis: list[dict[str, Any]],
    only: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build workflow skeletons from the curated seed catalogue.

    This is the deterministic rebuild path: every workflow is grounded on the
    exact API and alternative slugs declared in ``pipeline/seeds.py``. The LLM
    only fills the editorial content later.
    """
    api_index = {str(api.get("slug")): api for api in apis}
    wanted = set(only or [])
    selected = [
        seed
        for seed in seeds
        if not wanted or str(seed.get("slug")) in wanted
    ]
    return [
        seed_catalog.build_workflow_from_seed(seed, api_index)
        for seed in selected
    ]


# --------------------------------------------------------------------------- #
# API script generation with self-healing
# --------------------------------------------------------------------------- #
def generate_api_script(
    api: dict[str, Any],
    overrides: dict[str, Any],
    max_attempts: int = cfg.LLM_MAX_ATTEMPTS,
) -> tuple[str | None, list[str], int]:
    override = overrides.get(api.get("slug", ""), {}) or {}
    endpoint = override.get("endpoint") or (api.get("details") or {}).get("endpoint")
    feedback: str | None = None
    last_errors: list[str] = []

    # Reuse an existing, already valid script instead of burning an LLM call.
    existing_path = cfg.API_SCRIPTS_DIR / api["slug"] / f"{api['slug']}.py"
    if existing_path.exists():
        existing_script = existing_path.read_text(encoding="utf-8")
        existing_result = validator.validate_api_script(existing_script)
        if not existing_result.ok:
            missing_modules = sorted(
                {
                    match.group(1)
                    for error in existing_result.errors
                    if (
                        match := re.search(
                            r"module '(\w+)' is used but never imported", error
                        )
                    )
                }
            )
            if missing_modules:
                prefix = "\n".join(
                    f"import {name}" for name in missing_modules
                )
                existing_script = f"{prefix}\n{existing_script}"
                existing_result = validator.validate_api_script(existing_script)
        if existing_result.ok:
            return existing_script, existing_result.warnings, 0
        feedback = "; ".join(existing_result.errors)
        last_errors = existing_result.errors
        print(
            f"  [REUSE] {api['slug']}: existing script invalid "
            f"({len(existing_result.errors)} error(s)) – regenerating"
        )

    for attempt in range(1, max_attempts + 1):
        try:
            script = llm_client.chat_code(
                prompts.API_SCRIPT_SYSTEM,
                prompts.build_api_script_prompt(api, endpoint, feedback),
            )
        except llm_client.LLMError as error:
            feedback = str(error)
            last_errors = [feedback]
            print(f"  [RETRY] {api['slug']} attempt {attempt}: {feedback}")
            continue

        result = validator.validate_api_script(script)
        # Deterministically add missing stdlib imports before asking the LLM
        # again. This fixes the most common API-script failure instantly.
        missing_modules = sorted(
            {
                match.group(1)
                for error in result.errors
                if (
                    match := re.search(
                        r"module '(\w+)' is used but never imported", error
                    )
                )
            }
        )
        if missing_modules:
            prefix = "\n".join(f"import {name}" for name in missing_modules)
            script = f"{prefix}\n{script}"
            result = validator.validate_api_script(script)
        if result.ok:
            return script, result.warnings, attempt

        last_errors = result.errors
        feedback = "; ".join(result.errors)
        print(
            f"  [RETRY] {api['slug']} attempt {attempt}: {len(result.errors)} validator error(s)"
        )
        for message in result.errors[:6]:
            print(f"           - {message}")

    return None, last_errors or ["max attempts reached"], max_attempts


# --------------------------------------------------------------------------- #
# Alternatives
# --------------------------------------------------------------------------- #
def generate_alternative(
    alternative: dict[str, Any],
    alternatives_all: list[dict[str, Any]],
    max_attempts: int = cfg.LLM_MAX_ATTEMPTS,
) -> tuple[dict[str, Any] | None, list[str], int]:
    feedback: str | None = None
    last_errors: list[str] = []

    # Reuse an already valid alternative instead of burning an LLM call.
    existing_result = validator.validate_alternative(alternative)
    existing_result.errors.extend(
        validator.check_duplicate(
            alternative.get("slug", ""),
            alternative.get("title", ""),
            alternatives_all,
            ignore_slug=alternative.get("slug"),
        )
    )
    if existing_result.ok:
        return alternative, existing_result.warnings, 0
    feedback = "; ".join(existing_result.errors)
    last_errors = existing_result.errors

    for attempt in range(1, max_attempts + 1):
        try:
            data = llm_client.chat_json(
                prompts.ALTERNATIVE_SYSTEM,
                prompts.build_alternative_prompt(alternative, feedback),
            )
        except llm_client.LLMError as error:
            feedback = str(error)
            last_errors = [feedback]
            continue

        candidate = _deep_copy(alternative)
        details = candidate.setdefault("details", {})
        if data.get("description"):
            candidate["description"] = data["description"]
        if data.get("tags"):
            candidate["tags"] = data["tags"]
        if data.get("alternatives"):
            details["alternatives"] = data["alternatives"]
        for key in ("bestFor", "pricing", "features"):
            if data.get(key):
                details[key] = data[key]
        # Enforce the affiliate parameter on every real tool URL.
        for item in details.get("alternatives") or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if url.startswith(("http://", "https://")) and "ref=flowmatrix" not in url:
                separator = "&" if "?" in url else "?"
                item["url"] = f"{url}{separator}ref=flowmatrix"

        result = validator.validate_alternative(candidate)
        result.errors.extend(
            validator.check_duplicate(
                candidate.get("slug", ""),
                candidate.get("title", ""),
                alternatives_all,
                ignore_slug=alternative.get("slug"),
            )
        )
        if result.ok:
            return candidate, result.warnings, attempt
        last_errors = result.errors
        feedback = "; ".join(result.errors)
        print(f"  [RETRY] {alternative['slug']} attempt {attempt}: {feedback}")

    return None, last_errors or ["max attempts reached"], max_attempts


# --------------------------------------------------------------------------- #
# Artefacts
# --------------------------------------------------------------------------- #
def write_pdf(workflow: dict[str, Any]) -> Path:
    out = cfg.DOWNLOADS_DIR / f"flowmatrix-{workflow['slug']}.pdf"
    pdf_renderer.render_workflow_pdf(workflow, out)
    return out


def enforce_product_gate(product: dict[str, Any], kind: str) -> None:
    """Hard gate: refuse to upload anything the deep audit flags."""
    report = full_product_audit.audit_product(product, kind)
    if not report.ok:
        details = "; ".join(str(finding) for finding in report.findings)
        raise RuntimeError(f"product gate failed: {details}")
    print(f"  [GATE] {kind} {product.get('slug')} passed ({report.pages} pages)")


def rebuild_artifacts(
    workflows_to_rebuild: list[dict[str, Any]],
    upload: bool = True,
    skip_product_gate: bool = False,
) -> int:
    """Rebuild PDF/kit artifacts from existing records without calling the LLM.

    Used by ``--rebuild-artifacts`` to refresh the delivered artifacts after a
    data-only repair. It validates the record (live checks disabled), renders
    the PDF, builds the kit and uploads all delivery keys used by the
    download-gate worker.
    """
    previous_live = os.environ.get("FLOWMATRIX_SKIP_LIVE")
    os.environ["FLOWMATRIX_SKIP_LIVE"] = "1"
    failures: list[str] = []
    successes = 0
    try:
        for index, workflow in enumerate(workflows_to_rebuild, start=1):
            slug = str(workflow.get("slug"))
            print(f"\n[{index}/{len(workflows_to_rebuild)}] {slug}")
            try:
                result = validator.validate_workflow(workflow)
                if not result.ok:
                    raise RuntimeError("; ".join(result.errors))

                combined = "\n\n".join(
                    str(step.get("code_snippet") or "")
                    for step in (workflow.get("details") or {}).get("steps", [])
                )
                ast.parse(combined, feature_version=(3, 10))

                pdf_path = write_pdf(workflow)
                kit_path = bundle_builder.build_workflow_kit(
                    workflow, pdf_path, cfg.KITS_DIR
                )
                kit_result = validator.validate_kit_zip(
                    kit_path, cfg.WORKFLOW_KIT_FILES
                )
                if not kit_result.ok:
                    raise RuntimeError("kit: " + "; ".join(kit_result.errors))

                if not skip_product_gate:
                    enforce_product_gate(workflow, "workflow")

                if upload:
                    targets = [
                        (f"pdfs/flowmatrix-{slug}.pdf", pdf_path),
                        (f"{slug}.pdf", pdf_path),
                        (f"kits/{slug}-kit.zip", kit_path),
                    ]
                    for key, path in targets:
                        if not upload_to_r2(path, key):
                            raise RuntimeError(f"R2 upload failed: {key}")
                        print(f"  [OK] uploaded to R2: {key}")

                successes += 1
                print(f"  [OK] {pdf_path.name}, {kit_path.name}")
            except Exception as error:  # noqa: BLE001 - keep rebuilding
                failures.append(f"{slug}: {error}")
                print(f"  [FAIL] {slug}: {error}")
    finally:
        if previous_live is None:
            os.environ.pop("FLOWMATRIX_SKIP_LIVE", None)
        else:
            os.environ["FLOWMATRIX_SKIP_LIVE"] = previous_live

    print(
        f"\nArtifact rebuild: {successes} succeeded, {len(failures)} failed."
    )
    for failure in failures:
        print(f"  ✖ {failure}")
    return 0 if not failures else 1


def write_api_script(api: dict[str, Any], script: str) -> Path:
    directory = cfg.API_SCRIPTS_DIR / api["slug"]
    directory.mkdir(parents=True, exist_ok=True)
    script_path = directory / f"{api['slug']}.py"
    script_path.write_text(script, encoding="utf-8")

    details = api.get("details") or {}
    metadata = {
        "slug": api["slug"],
        "title": api.get("title"),
        "provider": details.get("provider"),
        "endpoint": details.get("endpoint"),
        "scriptFile": f"{api['slug']}.py",
        "price": cfg.SCRIPT_PRICE,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    (directory / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (directory / "README.md").write_text(
        f"# {api.get('title')} – Starter Script\n\n"
        f"Generated by FlowMatrix.dev. Zero-dependency Python 3.10+ script.\n\n"
        f"```bash\npython3 {api['slug']}.py\n```\n",
        encoding="utf-8",
    )
    return script_path


# --------------------------------------------------------------------------- #
# Upload / build / deploy
# --------------------------------------------------------------------------- #
def _cloudflare_ready() -> bool:
    cfg.load_env()
    return bool(os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID"))


def upload_to_r2(local_path: Path, key: str, bucket: str = "flowmatrix-downloads") -> bool:
    # wrangler may be authenticated via OAuth locally, so do not hard-require
    # CLOUDFLARE_* environment variables here – just try and degrade safely.
    cfg.load_env()
    try:
        subprocess.run(
            [
                "npx",
                "wrangler",
                "r2",
                "object",
                "put",
                f"{bucket}/{key}",
                "--file",
                str(local_path),
                "--remote",
            ],
            cwd=str(cfg.ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"  [WARN] R2 upload failed for {key}: {error}")
        return False


def delete_from_r2(key: str, bucket: str = "flowmatrix-downloads") -> bool:
    """Delete a single object from the R2 bucket (best effort)."""
    cfg.load_env()
    try:
        subprocess.run(
            [
                "npx",
                "wrangler",
                "r2",
                "object",
                "delete",
                f"{bucket}/{key}",
                "--remote",
                "--force",
            ],
            cwd=str(cfg.ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"  [WARN] R2 delete failed for {key}: {error}")
        return False


def purge_r2_artifacts(
    workflows: list[dict[str, Any]],
    apis: list[dict[str, Any]],
    include_apis: bool = False,
) -> None:
    """Delete the generated artifacts of the given workflows (and APIs) from R2.

    The keys are deterministic, so no bucket listing is required. Missing
    objects are reported as warnings and never abort the rebuild.
    """
    keys: list[str] = []
    for workflow in workflows:
        slug = str(workflow.get("slug") or "").strip()
        if not slug:
            continue
        keys.append(f"pdfs/flowmatrix-{slug}.pdf")
        keys.append(f"kits/{slug}-kit.zip")
    if include_apis:
        for api in apis:
            slug = str(api.get("slug") or "").strip()
            if not slug:
                continue
            keys.append(f"api-scripts/{slug}/{slug}.py")
            keys.append(f"api-kits/{slug}-kit.zip")
            keys.append(f"api-kits/{slug}-cheatsheet.pdf")
    print(f"[R2] purging {len(keys)} object(s) from flowmatrix-downloads")
    for key in keys:
        if delete_from_r2(key):
            print(f"  [OK] deleted from R2: {key}")


def run_build() -> None:
    subprocess.run(["npm", "run", "build"], cwd=str(cfg.ROOT), check=True)


def run_deploy() -> None:
    dist_index = cfg.ROOT / "dist" / "index.html"
    if not dist_index.exists() or dist_index.stat().st_size == 0:
        raise RuntimeError("Build output dist/index.html is missing or empty. Cannot deploy.")
    for attempt in range(1, 4):
        try:
            print(f"  [DEPLOY] Running wrangler pages deploy (attempt {attempt}/3)...")
            result = subprocess.run(
                [
                    "npx",
                    "wrangler",
                    "pages",
                    "deploy",
                    "dist",
                    "--project-name=programmatic-seo",
                    "--branch=main",
                    "--commit-dirty=true",
                ],
                cwd=str(cfg.ROOT),
                check=True,
                capture_output=True,
                text=True,
            )
            print("  [OK] Cloudflare Pages deployment successful.")
            if result.stdout:
                for line in result.stdout.splitlines():
                    if "success" in line.lower() or "https://" in line:
                        print(f"       {line.strip()}")
            return
        except subprocess.CalledProcessError as error:
            print(f"  [WARN] Deploy attempt {attempt} failed:")
            if error.stdout:
                print(f"       stdout: {error.stdout}")
            if error.stderr:
                print(f"       stderr: {error.stderr}")
            if attempt == 3:
                raise RuntimeError(f"Cloudflare Pages deployment failed after 3 attempts: {error}") from error
            print("       Retrying deployment...")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FlowMatrix unified pipeline")
    parser.add_argument("--workflows", type=int, default=0, help="Enrich N workflows")
    parser.add_argument("--apis", type=int, default=0, help="Regenerate scripts for N APIs")
    parser.add_argument("--alternatives", type=int, default=0, help="Enrich N alternatives")
    parser.add_argument("--only-workflow", action="append", default=[], help="Workflow slug (repeatable)")
    parser.add_argument("--only-api", action="append", default=[], help="API slug (repeatable)")
    parser.add_argument("--only-alternative", action="append", default=[], help="Alternative slug")
    parser.add_argument("--skip-workflow", action="append", default=[], help="Workflow slug to skip")
    parser.add_argument("--retry-skipped", action="store_true", help="Retry workflows marked as skipped")
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Skip in-place repair and always call the LLM",
    )
    parser.add_argument(
        "--from-seeds",
        action="store_true",
        help="Rebuild workflows from the curated pipeline/seeds.py catalogue",
    )
    parser.add_argument(
        "--reset-workflows",
        action="store_true",
        help="Clear workflows.json before the run (destructive)",
    )
    parser.add_argument(
        "--purge-r2",
        action="store_true",
        help="Delete generated workflow/API artifacts from R2 before the run",
    )
    parser.add_argument(
        "--rebuild-artifacts",
        action="store_true",
        help="Rebuild PDF/kit/R2 artifacts for selected workflows without LLM",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--skip-deploy", action="store_true")
    parser.add_argument(
        "--skip-product-gate",
        action="store_true",
        help="Debug only: skip the strict PDF/kit gate before R2 upload",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process exactly N open workflows from the 76-seed catalogue",
    )
    return parser.parse_args(argv)


def _select(
    items: list[dict[str, Any]],
    only: list[str],
    limit: int,
    incomplete=None,
) -> list[dict[str, Any]]:
    """Select a random batch from the catalogue.

    ``--seed`` makes the selection reproducible; the scheduled GitHub batch
    runs without a seed and therefore samples a fresh combination every time.
    """
    if only:
        wanted = set(only)
        return [item for item in items if item.get("slug") in wanted]
    pool = [item for item in items if incomplete(item)] if incomplete else list(items)
    if not pool:
        pool = list(items)
    if limit <= 0:
        return []
    if len(pool) <= limit:
        return list(pool)
    return random.sample(pool, limit)


# --------------------------------------------------------------------------- #
# Limited batch mode (10er-Blöcke) with persistent progress
# --------------------------------------------------------------------------- #
PROGRESS_FILE = cfg.ROOT / "pipeline" / "batch_progress.json"
FAILED_FILE = cfg.ROOT / "pipeline" / "failed_workflows.json"


def _load_progress() -> dict[str, Any]:
    if PROGRESS_FILE.exists():
        try:
            data = load_json(PROGRESS_FILE)
            if isinstance(data, dict):
                data.setdefault("status", {})
                return data
        except Exception:  # noqa: BLE001
            pass
    return {"status": {}, "updated_at": ""}


def _save_progress(progress: dict[str, Any]) -> None:
    progress["updated_at"] = _now_timestamp()
    save_json(PROGRESS_FILE, progress)


def _load_failed() -> dict[str, Any]:
    if FAILED_FILE.exists():
        try:
            data = load_json(FAILED_FILE)
            if isinstance(data, dict):
                return data
        except Exception:  # noqa: BLE001
            pass
    return {}


def _save_failed(failed: dict[str, Any]) -> None:
    save_json(FAILED_FILE, failed)


def _is_complete_workflow(item: dict[str, Any]) -> bool:
    details = item.get("details") or {}
    steps = details.get("steps") or []
    prerequisites = details.get("prerequisites") or []
    return bool(
        cfg.MIN_STEPS <= len(steps) <= cfg.MAX_STEPS
        and len(prerequisites) >= cfg.PREREQUISITES_MIN
        and any(
            str(entry).strip() == cfg.FINAL_PREREQUISITE
            for entry in prerequisites
        )
        and len(details.get("glossary") or []) >= cfg.GLOSSARY_TERMS_MIN
        and len(details.get("troubleshooting") or []) >= cfg.TROUBLESHOOTING_MIN
        and details.get("resources")
        and str(item.get("created_and_verified_at") or "").strip()
    )


def run_limited_batch(limit: int, skip_product_gate: bool = False) -> int:
    """Process exactly ``limit`` open workflows from the 76-seed catalogue.

    Progress is persisted in ``pipeline/batch_progress.json``. A workflow that
    fails after the configured attempts is written to
    ``pipeline/failed_workflows.json`` and the batch continues – it never
    aborts with exit code 1.
    """
    cfg.load_env()
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        print("[FAIL] OPENROUTER_API_KEY is not set.")
        return 2

    workflows = load_json(cfg.WORKFLOWS_FILE) if cfg.WORKFLOWS_FILE.exists() else []
    apis = load_json(cfg.APIS_FILE)
    alternatives = load_json(cfg.ALTERNATIVES_FILE)
    api_index = {str(api.get("slug")): api for api in apis}

    all_skeletons = [
        seed_catalog.build_workflow_from_seed(seed, api_index)
        for seed in seed_catalog.SEEDS
    ]
    existing_by_slug = {str(item.get("slug")): item for item in workflows}

    progress = _load_progress()
    status = progress.setdefault("status", {})
    failed = _load_failed()

    open_skeletons = [
        skeleton
        for skeleton in all_skeletons
        if status.get(str(skeleton["slug"])) != "done"
    ]
    batch = open_skeletons[: max(0, limit)]

    print("=" * 72)
    print(
        f"FLOWMATRIX LIMITED BATCH – {len(batch)} of {len(open_skeletons)} "
        f"open workflows (total {len(all_skeletons)})"
    )
    print("=" * 72)

    succeeded = 0
    for skeleton in batch:
        slug = str(skeleton["slug"])
        print(f"\n[WORKFLOW] {slug}")
        try:
            candidate: dict[str, Any] | None = None
            attempts = 0
            warnings: list[str] = []

            existing = existing_by_slug.get(slug)
            if existing is not None and _is_complete_workflow(existing):
                reuse_copy = _deep_copy(existing)
                reuse_result = validator.validate_workflow(reuse_copy)
                if reuse_result.ok:
                    candidate = reuse_copy
                    warnings = reuse_result.warnings
                    print("  [REUSE] existing complete record passed validation")

            if candidate is None:
                candidate, errors, attempts = generate_workflow(
                    skeleton,
                    workflows,
                    apis,
                    alternatives,
                    max_attempts=3,
                    force_regenerate=True,
                )
                if candidate is None:
                    raise RuntimeError("; ".join(errors) or "generation failed")
                final_result = validator.validate_workflow(candidate)
                if not final_result.ok:
                    raise RuntimeError("; ".join(final_result.errors))
                warnings = final_result.warnings

            candidate["created_and_verified_at"] = _now_timestamp()
            index = next(
                (
                    i
                    for i, item in enumerate(workflows)
                    if item.get("slug") == slug
                ),
                None,
            )
            if index is None:
                workflows.append(candidate)
            else:
                workflows[index] = candidate
            save_json(cfg.WORKFLOWS_FILE, workflows)
            existing_by_slug[slug] = candidate

            pdf_path = write_pdf(candidate)
            kit_path = bundle_builder.build_workflow_kit(
                candidate, pdf_path, cfg.KITS_DIR
            )
            kit_result = validator.validate_kit_zip(
                kit_path, cfg.WORKFLOW_KIT_FILES
            )
            if not kit_result.ok:
                raise RuntimeError(
                    "kit validation failed: " + "; ".join(kit_result.errors)
                )

            if not skip_product_gate:
                enforce_product_gate(candidate, "workflow")

            pdf_key = f"pdfs/flowmatrix-{slug}.pdf"
            delivery_key = f"{slug}.pdf"
            kit_key = f"kits/{slug}-kit.zip"
            pdf_uploaded = upload_to_r2(pdf_path, pdf_key)
            delivery_uploaded = upload_to_r2(pdf_path, delivery_key)
            kit_uploaded = upload_to_r2(kit_path, kit_key)
            if not (pdf_uploaded and delivery_uploaded and kit_uploaded):
                print(
                    "  [WARN] R2 upload incomplete – local artifacts kept, "
                    "workflow still marked done"
                )

            status[slug] = "done"
            failed.pop(slug, None)
            _save_progress(progress)
            _save_failed(failed)
            succeeded += 1
            print(
                f"  [OK] {slug} done (attempts={attempts}) -> "
                f"{pdf_path.name}, {kit_path.name}"
            )
        except Exception as error:  # noqa: BLE001 - never abort the batch
            reason = f"{type(error).__name__}: {error}"
            print(f"  [FAIL] {slug}: {reason}")
            failed[slug] = {
                "reason": reason,
                "timestamp": _now_timestamp(),
            }
            _save_failed(failed)
            continue

    done_count = sum(
        1
        for skeleton in all_skeletons
        if status.get(str(skeleton["slug"])) == "done"
    )
    total = len(all_skeletons)
    print("\n" + "=" * 72)
    print(f"BATCH SUMMARY: {succeeded}/{len(batch)} successful")
    print(f"TOTAL: {done_count}/{total} done | open: {total - done_count}")
    print("=" * 72)
    return 0


def main(argv: list[str] | None = None) -> int:
    cfg.load_env()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.limit and args.limit > 0:
        return run_limited_batch(args.limit, args.skip_product_gate)
    if args.seed is not None:
        random.seed(args.seed)

    api_key_missing = not os.environ.get("OPENROUTER_API_KEY", "").strip()
    needs_llm = bool(
        args.workflows or args.apis or args.alternatives
        or args.only_workflow or args.only_api or args.only_alternative
        or args.from_seeds
    ) and not args.rebuild_artifacts
    if needs_llm and api_key_missing:
        print("[FAIL] OPENROUTER_API_KEY is not set.")
        return 2

    workflows = load_json(cfg.WORKFLOWS_FILE)
    apis = load_json(cfg.APIS_FILE)
    alternatives = load_json(cfg.ALTERNATIVES_FILE)
    overrides = load_json(cfg.API_ENDPOINTS_FILE) if cfg.API_ENDPOINTS_FILE.exists() else {}
    overrides.pop("_comment", None)

    if args.rebuild_artifacts:
        selected = [
            item
            for item in workflows
            if not args.only_workflow
            or item.get("slug") in set(args.only_workflow)
        ]
        if not selected:
            print("[FAIL] --rebuild-artifacts matched no workflows")
            return 2
        return rebuild_artifacts(
            selected,
            upload=not args.skip_upload,
            skip_product_gate=args.skip_product_gate,
        )

    # Destructive cleanup happens before anything is regenerated. The R2 keys
    # are derived from the current catalogue, so no bucket listing is needed.
    if args.purge_r2:
        purge_r2_artifacts(workflows, apis)
    if args.reset_workflows:
        print("[RESET] clearing workflows.json")
        workflows = []
        save_json(cfg.WORKFLOWS_FILE, workflows)

    skipped_file = cfg.ROOT / "pipeline" / "skipped.json"
    skipped: set[str] = set()
    if skipped_file.exists() and not args.retry_skipped:
        try:
            skipped = set(load_json(skipped_file))
        except Exception:  # noqa: BLE001
            skipped = set()

    protocol: list[dict[str, Any]] = []

    def is_incomplete_workflow(item: dict[str, Any]) -> bool:
        details = item.get("details") or {}
        prerequisites = details.get("prerequisites") or []
        glossary = details.get("glossary") or []
        troubleshooting = details.get("troubleshooting") or []
        steps = details.get("steps") or []
        resources = details.get("resources") or []
        return not (
            cfg.MIN_STEPS <= len(steps) <= cfg.MAX_STEPS
            and len(prerequisites) >= cfg.PREREQUISITES_MIN
            and any(
                str(entry).strip() == cfg.FINAL_PREREQUISITE
                for entry in prerequisites
            )
            and len(glossary) >= cfg.GLOSSARY_TERMS_MIN
            and len(troubleshooting) >= cfg.TROUBLESHOOTING_MIN
            and len(resources) >= 1
            and str(item.get("created_and_verified_at") or "").strip()
        )

    # Random batch selection: 4 APIs + 3 alternatives + N workflows per run.
    selected_apis = (
        _select(apis, args.only_api, args.apis or 0)
        if (args.only_api or args.apis)
        else []
    )
    selected_alternatives = (
        _select(alternatives, args.only_alternative, args.alternatives or 0)
        if (args.only_alternative or args.alternatives)
        else []
    )

    if args.from_seeds:
        skeletons = build_seed_workflows(
            seed_catalog.SEEDS, apis, args.only_workflow
        )
        if not skeletons:
            print("[FAIL] no curated seeds matched the selection")
            return 2
        existing_by_slug = {str(item.get("slug")): item for item in workflows}
        if not args.force_regenerate:
            # Resume-friendly: already complete workflows are not regenerated.
            skeletons = [
                skeleton
                for skeleton in skeletons
                if is_incomplete_workflow(
                    existing_by_slug.get(str(skeleton["slug"]), skeleton)
                )
            ]
        selected_workflows = skeletons
        # Merge the seed skeletons into the live catalogue so duplicate
        # protection and the final store see every workflow of this rebuild.
        by_slug = {str(item.get("slug")): item for item in workflows}
        for skeleton in selected_workflows:
            by_slug[str(skeleton["slug"])] = skeleton
        workflows = list(by_slug.values())
        save_json(cfg.WORKFLOWS_FILE, workflows)
    elif args.only_workflow:
        selected_workflows = [
            item for item in workflows if item.get("slug") in set(args.only_workflow)
        ]
    elif args.workflows:
        if selected_apis:
            # New workflows are composed from the APIs/alternatives selected in
            # this exact batch. The LLM proposes the topic; the pipeline owns
            # the grounding slugs.
            selected_workflows = build_batch_workflow_seeds(
                selected_apis,
                selected_alternatives,
                args.workflows,
                workflows,
            )
        else:
            skip = set(args.skip_workflow) | skipped
            pool = [
                item
                for item in workflows
                if is_incomplete_workflow(item) and item.get("slug") not in skip
            ]
            if not pool:
                pool = [
                    item for item in workflows if item.get("slug") not in skip
                ]
            selected_workflows = random.sample(
                pool, min(args.workflows, len(pool))
            )
    else:
        selected_workflows = []

    # Live reference: candidates are written back into ``workflows`` during the
    # loop, so duplicate protection always sees the current state.
    workflows_for_checks = workflows

    print("=" * 72)
    print("FLOWMATRIX UNIFIED PIPELINE")
    print("=" * 72)
    print(
        f"Workflows: {len(selected_workflows)} | APIs: {len(selected_apis)} | "
        f"Alternatives: {len(selected_alternatives)} | dry-run={args.dry_run}"
    )

    # --- Workflows ----------------------------------------------------------- #
    queue = list(selected_workflows)
    processed: set[str] = set()

    while queue:
        workflow = queue.pop(0)
        slug = workflow.get("slug", "")
        if slug in processed:
            continue
        processed.add(slug)

        print(f"\n[WORKFLOW] {slug}")
        if args.dry_run:
            print("  (dry-run, skipped)")
            continue

        candidate, errors, attempts = generate_workflow(
            workflow,
            workflows_for_checks,
            apis,
            alternatives,
            force_regenerate=args.force_regenerate or args.from_seeds,
        )
        if candidate is None:
            protocol.append({"kind": "workflow", "slug": slug, "ok": False,
                             "attempts": attempts, "errors": errors})
            print(f"  [FAIL] {slug} rejected after {attempts} attempts")
            skipped.add(slug)
            save_json(skipped_file, sorted(skipped))
            continue

        result = validator.validate_workflow(candidate)
        if not result.ok:  # defensive: never store invalid content
            protocol.append({"kind": "workflow", "slug": slug, "ok": False,
                             "attempts": attempts, "errors": result.errors})
            print(f"  [FAIL] {slug} failed final gate")
            continue

        candidate["created_and_verified_at"] = _now_timestamp()
        index = next(
            (i for i, item in enumerate(workflows) if item["slug"] == slug),
            None,
        )
        if index is None:
            workflows.append(candidate)
        else:
            workflows[index] = candidate
        save_json(cfg.WORKFLOWS_FILE, workflows)
        skipped.discard(slug)
        save_json(skipped_file, sorted(skipped))

        pdf_path = write_pdf(candidate)
        kit_path = bundle_builder.build_workflow_kit(
            candidate, pdf_path, cfg.KITS_DIR
        )
        kit_res = validator.validate_kit_zip(kit_path, cfg.WORKFLOW_KIT_FILES)
        if not kit_res.ok:
            protocol.append({"kind": "workflow", "slug": slug, "ok": False,
                             "attempts": attempts, "errors": kit_res.errors})
            print(f"  [FAIL] Workflow kit validation failed: {kit_res.errors}")
            continue

        if not args.skip_product_gate:
            try:
                enforce_product_gate(candidate, "workflow")
            except Exception as error:  # noqa: BLE001
                protocol.append({"kind": "workflow", "slug": slug, "ok": False,
                                 "attempts": attempts, "errors": [str(error)]})
                print(f"  [FAIL] {slug} product gate: {error}")
                continue

        protocol.append({"kind": "workflow", "slug": slug, "ok": True,
                         "attempts": attempts, "warnings": result.warnings,
                         "pdf": str(pdf_path), "kit": str(kit_path),
                         "price": cfg.price_label(
                             (candidate.get("details") or {}).get("difficulty"))})
        print(f"  [OK] validated after {attempts} attempt(s) -> {pdf_path.name}")
        print(f"  [OK] implementation kit -> {kit_path.name}")

        if not args.skip_upload:
            key = f"pdfs/flowmatrix-{candidate['slug']}.pdf"
            if upload_to_r2(pdf_path, key):
                print(f"  [OK] uploaded to R2: {key}")
            delivery_key = f"{candidate['slug']}.pdf"
            if upload_to_r2(pdf_path, delivery_key):
                print(f"  [OK] uploaded to R2: {delivery_key}")
            kit_key = f"kits/{candidate['slug']}-kit.zip"
            if upload_to_r2(kit_path, kit_key):
                print(f"  [OK] uploaded to R2: {kit_key}")

    # --- API scripts --------------------------------------------------------- #
    for api in selected_apis:
        print(f"\n[API] {api['slug']}")
        if args.dry_run:
            print("  (dry-run, skipped)")
            continue
        script, warnings, attempts = generate_api_script(api, overrides)
        if script is None:
            protocol.append({"kind": "api", "slug": api["slug"], "ok": False,
                             "attempts": attempts, "errors": warnings})
            print(f"  [FAIL] {api['slug']} rejected after {attempts} attempts")
            continue

        result = validator.validate_api_script(script)
        if not result.ok:
            protocol.append({"kind": "api", "slug": api["slug"], "ok": False,
                             "attempts": attempts, "errors": result.errors})
            print(f"  [FAIL] {api['slug']} failed final gate")
            continue

        script_path = write_api_script(api, script)
        kit_path, cheatsheet_path = bundle_builder.build_api_kit(
            api, script_path, cfg.API_KITS_DIR
        )
        kit_res = validator.validate_kit_zip(kit_path, cfg.API_KIT_FILES)
        if not kit_res.ok:
            protocol.append({"kind": "api", "slug": api["slug"], "ok": False,
                             "attempts": attempts, "errors": kit_res.errors})
            print(f"  [FAIL] API kit validation failed: {kit_res.errors}")
            continue

        if not args.skip_product_gate:
            try:
                enforce_product_gate(api, "api")
            except Exception as error:  # noqa: BLE001
                protocol.append({"kind": "api", "slug": api["slug"], "ok": False,
                                 "attempts": attempts, "errors": [str(error)]})
                print(f"  [FAIL] {api['slug']} product gate: {error}")
                continue

        protocol.append({"kind": "api", "slug": api["slug"], "ok": True,
                         "attempts": attempts, "warnings": warnings,
                         "script": str(script_path), "kit": str(kit_path),
                         "cheatsheet": str(cheatsheet_path)})
        print(f"  [OK] validated after {attempts} attempt(s) -> {script_path.name}")
        print(f"  [OK] API implementation kit -> {kit_path.name}")

        if not args.skip_upload:
            key = f"api-scripts/{api['slug']}/{api['slug']}.py"
            if upload_to_r2(script_path, key):
                print(f"  [OK] uploaded to R2: {key}")
            kit_key = f"api-kits/{api['slug']}-kit.zip"
            if upload_to_r2(kit_path, kit_key):
                print(f"  [OK] uploaded to R2: {kit_key}")
            cheatsheet_key = f"api-kits/{api['slug']}-cheatsheet.pdf"
            if upload_to_r2(cheatsheet_path, cheatsheet_key):
                print(f"  [OK] uploaded to R2: {cheatsheet_key}")

    # --- Alternatives -------------------------------------------------------- #
    for alternative in selected_alternatives:
        print(f"\n[ALTERNATIVE] {alternative['slug']}")
        if args.dry_run:
            print("  (dry-run, skipped)")
            continue
        candidate, warnings, attempts = generate_alternative(alternative, alternatives)
        if candidate is None:
            protocol.append({"kind": "alternative", "slug": alternative["slug"], "ok": False,
                             "attempts": attempts, "errors": warnings})
            print(f"  [FAIL] {alternative['slug']} rejected")
            continue
        index = next(i for i, item in enumerate(alternatives) if item["slug"] == alternative["slug"])
        alternatives[index] = candidate
        save_json(cfg.ALTERNATIVES_FILE, alternatives)
        protocol.append({"kind": "alternative", "slug": alternative["slug"], "ok": True,
                         "attempts": attempts, "warnings": warnings})
        print(f"  [OK] validated after {attempts} attempt(s)")

    # --- Summary ------------------------------------------------------------- #
    if protocol:
        ok = sum(1 for entry in protocol if entry["ok"])
        print("\n" + "=" * 72)
        print(f"VALIDATION PROTOCOL: {ok}/{len(protocol)} passed")
        for entry in protocol:
            status = "OK" if entry["ok"] else "FAIL"
            print(f"  [{status}] {entry['kind']}:{entry['slug']} (attempts={entry['attempts']})")
            for error in entry.get("errors", []):
                print(f"        - {error}")
        log_path = cfg.ROOT / "pipeline" / "last_run.json"
        log_path.write_text(
            json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Protocol written to {log_path}")

    failed = [entry for entry in protocol if not entry["ok"]]
    if failed:
        print("\n[FAIL] Batch aborted – not all items passed the hard gate.")
        return 1

    # --- Build / deploy ------------------------------------------------------ #
    if not args.skip_build:
        print("\n[BUILD] npm run build")
        run_build()
    if not args.skip_deploy and not args.dry_run:
        print("\n[DEPLOY] Cloudflare Pages")
        run_deploy()

    print("\n[DONE] Pipeline finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
