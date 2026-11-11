"""Regenerate legacy workflow code snippets that contain placeholders or are too short.

Only affected steps are rewritten. Every candidate is validated mechanically
(AST + stdlib imports + placeholder scan + minimum line count) before it is
written back to ``src/data/workflows.json``.

Usage:
    .venv/bin/python -m pipeline.repair_snippets --dry-run
    .venv/bin/python -m pipeline.repair_snippets --limit=2
    .venv/bin/python -m pipeline.repair_snippets --concurrency=3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Load the local .env before importing config (config reads env at import time).
def _load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env()
os.environ.setdefault("OPENROUTER_MODEL", "deepseek/deepseek-v4.1-flash-1017")

from . import config  # noqa: E402
from .llm_client import LLMError, chat_json  # noqa: E402
from .validator import check_python_ast, non_empty_lines  # noqa: E402

WORKFLOWS_FILE = config.ROOT / "src" / "data" / "workflows.json"
PLACEHOLDER_RE = re.compile(
    r"YOUR_[A-Z0-9_]+|<YOUR|your-[a-z]|example\.com|lorem ipsum|"
    r"\bdummy\b|\bplaceholder\b|TODO|FIXME|realistic fallback",
    re.IGNORECASE,
)
MIN_LINES = max(config.MIN_CODE_LINES, 10)
FALLBACK_MODEL = os.environ.get("OPENROUTER_FALLBACK_MODEL", "openai/gpt-4o")
MODEL_LOCK = threading.Lock()

SYSTEM_PROMPT = (
    "You are a senior Python engineer. You rewrite workflow snippets so they "
    "are runnable, defensive and free of placeholders. Return only valid JSON."
)


def _needs_repair(code: str) -> str | None:
    if not code:
        return None
    if PLACEHOLDER_RE.search(code):
        return "placeholder"
    if len(non_empty_lines(code)) < MIN_LINES:
        return "short"
    return None


def find_targets(workflows: list[dict], slug: str | None = None) -> list[dict]:
    targets: list[dict] = []
    for wf_index, workflow in enumerate(workflows):
        if slug and workflow.get("slug") != slug:
            continue
        for step_index, step in enumerate(workflow.get("details", {}).get("steps", [])):
            if not isinstance(step, dict):
                continue
            reason = _needs_repair(str(step.get("code_snippet") or ""))
            if reason:
                targets.append(
                    {
                        "workflow_index": wf_index,
                        "step_index": step_index,
                        "slug": workflow.get("slug"),
                        "step_number": step_index + 1,
                        "reason": reason,
                    }
                )
    return targets


def build_user_prompt(
    workflow: dict, step: dict, step_number: int, feedback: list[str] | None
) -> str:
    details = workflow.get("details", {})
    feedback_text = ""
    if feedback:
        feedback_text = (
            "\nThe previous attempt failed validation. Fix ALL of these issues:\n"
            + "\n".join(f"- {item}" for item in feedback)
        )

    return f"""Rewrite the Python `code_snippet` for this FlowMatrix workflow step.

WORKFLOW: {workflow.get("title")} ({workflow.get("slug")})
TOOLS: {", ".join(details.get("tools", []))}
STEP {step_number}: {step.get("title")}
DESCRIPTION: {step.get("description")}
TECHNICAL EXPLANATION: {step.get("technical_explanation")}
EXPECTED RESULT: {step.get("expectedResult")}

CURRENT SNIPPET (must be replaced):
```python
{step.get("code_snippet", "")}
```

HARD REQUIREMENTS:
- Python 3.10+, standard library only (no requests/openai/supabase/httpx/etc.).
- At least 12 non-empty lines of real logic.
- NO placeholders: do not use YOUR_API_KEY, <YOUR_...>, example.com, "dummy",
  "placeholder", random values or fake fallback data.
- Read secrets via os.environ.get("KEY", "") and import every module at the top.
- Keep the step's intent and a real data flow; end with a top-level call.
- English comments only. Syntactically valid Python (balanced quotes/brackets).
{feedback_text}

Return exactly this JSON shape:
{{"code_snippet": "..."}}"""


def validate_snippet(code: str, context: str) -> list[str]:
    errors: list[str] = []
    if not code.strip():
        return ["code is empty"]
    if PLACEHOLDER_RE.search(code):
        errors.append("contains a placeholder/dummy value")
    line_count = len(non_empty_lines(code))
    if line_count < MIN_LINES:
        errors.append(f"has only {line_count} non-empty lines (minimum {MIN_LINES})")
    result = check_python_ast(code, context, config.WORKFLOW_FORBIDDEN_IMPORTS)
    errors.extend(result.errors)
    if "random." in code or "import random" in code:
        errors.append("randomness is forbidden")
    if "# Dummy" in code or "Dummy" in code:
        errors.append("dummy data is forbidden")
    return errors


def _strip_fences(text: str) -> str:
    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines.pop()
        cleaned = "\n".join(lines)
    return cleaned


def _chat_with_fallback(system: str, user: str) -> dict:
    try:
        return chat_json(system, user)
    except LLMError as error:
        message = str(error).lower()
        if ("model" in message or "endpoint" in message) and config.LLM_MODEL != FALLBACK_MODEL:
            with MODEL_LOCK:
                config.LLM_MODEL = FALLBACK_MODEL
            return chat_json(system, user)
        raise


def repair_one(workflow: dict, target: dict) -> dict:
    step = workflow["details"]["steps"][target["step_index"]]
    context = f"{target['slug']} step {target['step_number']}"
    feedback: list[str] | None = None

    for attempt in range(1, 4):
        payload = _chat_with_fallback(
            SYSTEM_PROMPT,
            build_user_prompt(workflow, step, target["step_number"], feedback),
        )
        code = _strip_fences(str(payload.get("code_snippet") or ""))
        errors = validate_snippet(code, context)
        if not errors:
            return {"ok": True, "code": code, "attempts": attempt, "target": target}
        feedback = errors
        print(f"  ↻ {context}: Versuch {attempt} ungültig: {'; '.join(errors)}")

    return {"ok": False, "errors": feedback, "target": target}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="0 = alle")
    parser.add_argument("--slug", help="Nur diesen Workflow bearbeiten")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--model", help="OpenRouter-Modell überschreiben")
    args = parser.parse_args()

    if args.model:
        config.LLM_MODEL = args.model
        os.environ["OPENROUTER_MODEL"] = args.model

    if not config.get_api_key():
        print("✖ OPENROUTER_API_KEY fehlt (.env oder Umgebung).")
        return 1

    workflows = json.loads(WORKFLOWS_FILE.read_text(encoding="utf-8"))
    targets = find_targets(workflows, args.slug)
    if args.limit > 0:
        targets = targets[: args.limit]

    print(
        f"▶ Snippet-Reparatur · Modell: {config.LLM_MODEL} · "
        f"Ziele: {len(targets)} · Concurrency: {args.concurrency}"
    )
    for target in targets:
        print(
            f"  - {target['slug']} step {target['step_number']} "
            f"({target['reason']})"
        )

    if args.dry_run or not targets:
        return 0

    results: dict[tuple[int, int], str] = {}
    failures: list[dict] = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = {
            pool.submit(repair_one, workflows[target["workflow_index"]], target): target
            for target in targets
        }
        for future in as_completed(futures):
            target = futures[future]
            completed += 1
            try:
                result = future.result()
            except Exception as error:  # noqa: BLE001 - report and continue
                failures.append({"target": target, "error": str(error)})
                print(f"  ✖ {target['slug']} step {target['step_number']}: {error}")
                continue
            if result["ok"]:
                results[(target["workflow_index"], target["step_index"])] = result["code"]
                print(
                    f"  ✓ [{completed}/{len(targets)}] {target['slug']} "
                    f"step {target['step_number']} ({len(non_empty_lines(result['code']))} Zeilen)"
                )
            else:
                failures.append(
                    {"target": target, "errors": result.get("errors", [])}
                )
                print(
                    f"  ✖ {target['slug']} step {target['step_number']}: "
                    f"{result.get('errors')}"
                )

    for (workflow_index, step_index), code in results.items():
        workflows[workflow_index]["details"]["steps"][step_index][
            "code_snippet"
        ] = code

    WORKFLOWS_FILE.write_text(
        json.dumps(workflows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"\n✔ {len(results)} Snippet(s) repariert, "
        f"{len(failures)} fehlgeschlagen."
    )
    if failures:
        report = Path("/tmp/repair-snippets-failures.json")
        report.write_text(
            json.dumps(failures, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  Fehlerbericht: {report}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
