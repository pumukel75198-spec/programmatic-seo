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

from . import config as cfg
from . import bundle_builder, llm_client, pdf_renderer, prompts, validator


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


def _tool_map(partner: dict[str, Any], names: list[str]) -> list[dict[str, Any]]:
    return [{"name": name, **partner.get(name, {})} for name in names]


TOOL_FALLBACKS: dict[str, dict[str, str]] = {
    "x api": {
        "provider": "X",
        "endpoint": "https://api.x.com/2/tweets/search/recent",
        "url": "https://developer.x.com/en/docs/twitter-api/tweets/search/introduction",
        "authentication": "Bearer token",
    },
    "twitter api": {
        "provider": "X",
        "endpoint": "https://api.x.com/2/tweets/search/recent",
        "url": "https://developer.x.com/en/docs/twitter-api/tweets/search/introduction",
        "authentication": "Bearer token",
    },
    "openai api": {
        "provider": "OpenAI",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "url": "https://platform.openai.com/docs/api-reference/chat/create",
        "authentication": "Bearer API key",
    },
    "slack": {
        "provider": "Slack",
        "endpoint": "https://hooks.slack.com/services/<workspace>/<channel>/<token>",
        "url": "https://api.slack.com/messaging/webhooks",
        "authentication": "Incoming webhook URL",
    },
    "n8n": {
        "provider": "n8n",
        "endpoint": "https://<your-n8n-instance>/webhook/<name>",
        "url": "https://docs.n8n.io/",
        "authentication": "Webhook URL",
    },
}


def _api_script_endpoint(api: dict[str, Any]) -> str:
    """Return a concrete URL that the validated API script actually uses."""
    slug = str(api.get("slug") or "")
    path = cfg.API_SCRIPTS_DIR / slug / f"{slug}.py"
    if not path.exists():
        return ""
    code = path.read_text(encoding="utf-8")
    urls = [
        url
        for url in validator.extract_urls(code)
        if not any(marker in url for marker in ("<", ">", "{", "}"))
    ]
    for url in urls:
        parsed = urllib.parse.urlparse(url)
        if parsed.path not in ("", "/"):
            return url
    return urls[0] if urls else ""


def _api_tokens(api: dict[str, Any]) -> set[str]:
    details = api.get("details") or {}
    text = " ".join(
        [
            str(api.get("title") or ""),
            str(details.get("provider") or ""),
            str(details.get("useCase") or ""),
            " ".join(str(tag) for tag in api.get("tags") or []),
        ]
    ).lower()
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if len(token) >= 3
        and token not in {"api", "the", "and", "for", "with"}
    }


def _tool_aliases(name: str) -> set[str]:
    lowered = name.lower()
    aliases = {
        token for token in re.findall(r"[a-z0-9]+", lowered) if len(token) >= 3
    }
    if "x api" in lowered or "twitter" in lowered:
        aliases |= {"twitter", "tweets"}
    if "openai" in lowered:
        aliases |= {"openai", "gpt"}
    if "supabase" in lowered:
        aliases |= {"supabase"}
    if "slack" in lowered:
        aliases |= {"slack"}
    if "resend" in lowered:
        aliases |= {"resend"}
    if "crm" in lowered or "hubspot" in lowered:
        aliases |= {"hubspot", "crm"}
    return aliases


def _grounded_tools(
    workflow: dict[str, Any],
    apis: list[dict[str, Any]],
    partner: dict[str, Any],
) -> list[dict[str, Any]]:
    """Map workflow tool names to real API records (endpoint + docs URL)."""
    details = workflow.get("details") or {}
    names = [str(t).strip() for t in (details.get("tools") or []) if str(t).strip()]
    workflow_category = str(workflow.get("category") or "").lower()
    workflow_tags = {str(tag).lower() for tag in workflow.get("tags") or []}
    grounded: list[dict[str, Any]] = []
    used: set[str] = set()
    for name in names:
        fallback = TOOL_FALLBACKS.get(name.lower())
        if fallback:
            grounded.append({"name": name, **fallback})
            continue
        aliases = _tool_aliases(name)
        best = None
        best_score = 0
        for api in apis:
            if api.get("slug") in used:
                continue
            score = len(aliases & _api_tokens(api))
            if score == 0:
                continue
            if (
                workflow_category
                and str(api.get("category") or "").lower() == workflow_category
            ):
                score += 2
            if workflow_tags & {
                str(tag).lower() for tag in api.get("tags") or []
            }:
                score += 1
            if score > best_score:
                best_score = score
                best = api
        if best is None:
            entry = partner.get(name) or {}
            entry_url = entry.get("affiliateUrl") or entry.get("url") or ""
            entry_endpoint = entry.get("endpoint") or ""
            if not entry_url and not entry_endpoint:
                # Ungrounded tool: exclude it so the LLM cannot invent an API.
                continue
            grounded.append(
                {
                    "name": name,
                    "provider": entry.get("provider") or "",
                    "url": entry_url,
                    "endpoint": entry_endpoint,
                    "authentication": entry.get("authentication") or "",
                }
            )
            continue
        used.add(best["slug"])
        data = best.get("details") or {}
        grounded.append(
            {
                "name": name,
                "provider": data.get("provider") or "",
                "url": data.get("docsUrl") or data.get("website") or "",
                "endpoint": (
                    _api_script_endpoint(best)
                    or data.get("endpoint")
                    or ""
                ),
                "authentication": data.get("authentication") or "",
            }
        )
    return grounded


def _related_alternatives(
    workflow: dict[str, Any],
    alternatives: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    tags = {str(tag).lower() for tag in workflow.get("tags") or []}
    category = str(workflow.get("category") or "").lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for alternative in alternatives:
        alt_tags = {str(tag).lower() for tag in alternative.get("tags") or []}
        score = len(tags & alt_tags)
        if category and str(alternative.get("category") or "").lower() == category:
            score += 1
        if score:
            scored.append((score, alternative))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [alternative for _, alternative in scored[:limit]]


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
    partner: dict[str, Any],
    apis: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    max_attempts: int = cfg.LLM_MAX_ATTEMPTS,
    force_regenerate: bool = False,
) -> tuple[dict[str, Any] | None, list[str], int]:
    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    available_tools = _grounded_tools(workflow, apis, partner)
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
            grounded_resources = []
            for tool in available_tools:
                if tool.get("url"):
                    grounded_resources.append(
                        {"label": tool["name"], "url": tool["url"]}
                    )
                endpoint = str(tool.get("endpoint") or "")
                if (
                    endpoint.startswith("http")
                    and "<" not in endpoint
                    and "{" not in endpoint
                ):
                    endpoint_host = endpoint.split("//", 1)[-1].split("/", 1)[0]
                    docs_host = (
                        str(tool.get("url") or "")
                        .split("//", 1)[-1]
                        .split("/", 1)[0]
                    )
                    if endpoint_host and endpoint_host != docs_host:
                        grounded_resources.append(
                            {
                                "label": f"{tool['name']} Endpoint",
                                "url": endpoint,
                            }
                        )
            candidate_details["resources"] = (
                grounded_resources or data.get("resources", [])
            )

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
                    tool_docs = {
                        "X API": (
                            "X API Search Docs",
                            "https://developer.x.com/en/docs/twitter-api/tweets/search/introduction",
                        ),
                        "OpenAI API": (
                            "OpenAI Chat Completions Docs",
                            "https://platform.openai.com/docs/api-reference/chat/create",
                        ),
                        "Supabase": (
                            "Supabase REST Docs",
                            "https://supabase.com/docs/guides/api",
                        ),
                        "Slack": (
                            "Slack Incoming Webhooks",
                            "https://api.slack.com/messaging/webhooks",
                        ),
                    }
                    for tool_name in step.get("tools") or []:
                        tool = partner.get(tool_name) or {}
                        url = tool.get("affiliateUrl") or tool.get("url") or ""
                        label = tool_name
                        if not url and tool_name in tool_docs:
                            label, url = tool_docs[tool_name]
                        if not url:
                            for resource in resources:
                                resource_label = str(
                                    resource.get("label") or ""
                                ).strip().lower()
                                if resource_label == str(tool_name).strip().lower():
                                    url = str(resource.get("url") or "")
                                    label = str(resource.get("label") or tool_name)
                                    break
                        if url:
                            links.append({"label": label, "url": url})
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
                    raw_name = str(raw_tool).strip()
                    if not raw_name:
                        continue
                    matched_name = next(
                        (
                            tool["name"]
                            for tool in available_tools
                            if tool["name"].lower() == raw_name.lower()
                            or raw_name.lower() in tool["name"].lower()
                            or tool["name"].lower() in raw_name.lower()
                        ),
                        None,
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
            if used_tools:
                code_all = "\n".join(
                    str(step.get("code_snippet") or "") for step in steps_out
                ).lower()
                filtered_tools = []
                for name in used_tools:
                    markers = cfg.TOOL_CODE_MARKERS.get(name) or (name.lower(),)
                    if any(marker.lower() in code_all for marker in markers):
                        filtered_tools.append(name)
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


def generate_replacement_topic(
    workflows_all: list[dict[str, Any]],
    partner: dict[str, Any],
) -> dict[str, Any] | None:
    """Ask the LLM for a brand-new workflow topic after a domain failure."""
    existing_titles = [str(item.get("title", "")) for item in workflows_all]
    available_tools = list(partner.keys())
    try:
        data = llm_client.chat_json(
            prompts.TOPIC_SYSTEM,
            prompts.build_new_topic_prompt(existing_titles, available_tools),
        )
    except llm_client.LLMError as error:
        print(f"  [REPLACE] could not generate a new topic: {error}")
        return None

    slug = str(data.get("slug") or "").strip()
    title = str(data.get("title") or "").strip()
    if not slug or not title:
        print("  [REPLACE] new topic is missing slug/title")
        return None

    existing_slugs = {str(item.get("slug", "")) for item in workflows_all}
    base_slug = slug
    counter = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    return {
        "slug": slug,
        "title": title,
        "description": str(data.get("description") or "").strip(),
        "category": str(data.get("category") or "Data & Automation").strip(),
        "tags": data.get("tags") or [],
        "details": {
            "difficulty": str(data.get("difficulty") or "Intermediate").strip(),
            "duration": str(data.get("duration") or "30–45 minutes").strip(),
            "tools": data.get("tools") or [],
            "steps": data.get("steps") or [],
            "useCase": str(data.get("useCase") or "").strip(),
        },
    }


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
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--skip-deploy", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args(argv)


def _select(items: list[dict[str, Any]], only: list[str], limit: int, incomplete=None) -> list[dict[str, Any]]:
    if only:
        wanted = set(only)
        return [item for item in items if item.get("slug") in wanted]
    pool = [item for item in items if incomplete(item)] if incomplete else list(items)
    if not pool:
        pool = list(items)
    if limit <= 0:
        return []
    return pool[:limit]


def main(argv: list[str] | None = None) -> int:
    cfg.load_env()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.seed is not None:
        random.seed(args.seed)

    api_key_missing = not os.environ.get("OPENROUTER_API_KEY", "").strip()
    needs_llm = bool(
        args.workflows or args.apis or args.alternatives
        or args.only_workflow or args.only_api or args.only_alternative
    )
    if needs_llm and api_key_missing:
        print("[FAIL] OPENROUTER_API_KEY is not set.")
        return 2

    workflows = load_json(cfg.WORKFLOWS_FILE)
    apis = load_json(cfg.APIS_FILE)
    alternatives = load_json(cfg.ALTERNATIVES_FILE)
    overrides = load_json(cfg.API_ENDPOINTS_FILE) if cfg.API_ENDPOINTS_FILE.exists() else {}
    overrides.pop("_comment", None)
    partner = load_json(cfg.PARTNER_FILE) if cfg.PARTNER_FILE.exists() else {}

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

    if args.only_workflow or args.workflows:
        selected_workflows = _select(
            workflows, args.only_workflow, 100000, is_incomplete_workflow
        )
        if args.only_workflow:
            selected_workflows = [
                item for item in workflows if item.get("slug") in set(args.only_workflow)
            ]
        skip = set(args.skip_workflow) | skipped
        if skip:
            selected_workflows = [w for w in selected_workflows if w.get("slug") not in skip]
        selected_workflows = selected_workflows[: args.workflows or len(selected_workflows)]
    else:
        selected_workflows = []
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
    replacements = 0

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
            workflows,
            partner,
            apis,
            alternatives,
            force_regenerate=args.force_regenerate,
        )
        if candidate is None:
            # Domain failure -> discard and generate a brand-new topic.
            if _is_domain_failure(errors) and replacements < cfg.MAX_REPLACEMENT_TOPICS:
                replacements += 1
                print(
                    f"  [REPLACE] {slug}: unreachable domain -> generating a new topic "
                    f"({replacements}/{cfg.MAX_REPLACEMENT_TOPICS})"
                )
                new_topic = generate_replacement_topic(workflows, partner)
                if new_topic is not None:
                    workflows.append(new_topic)
                    save_json(cfg.WORKFLOWS_FILE, workflows)
                    queue.append(new_topic)
                    continue

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
        index = next(i for i, item in enumerate(workflows) if item["slug"] == slug)
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
