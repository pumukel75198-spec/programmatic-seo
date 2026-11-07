"""Deterministic hardening of generated Python snippets.

The LLM keeps writing ``payload["key"]`` even when it was told to use
``payload.get("key", default)``. A single missing key then aborts the whole
dry-run with ``KeyError``. This module rewrites *all* subscript reads on
JSON-derived containers into defensive ``.get(key, default)`` calls, while
keeping the original source (and therefore every human-readable comment).

Two passes are applied:

1. **AST pass** – tracks the names that come from ``json.loads``, ``json.load``,
   ``response.json()`` and common JSON containers, then rewrites every string
   subscript read on those names. The default value is inferred from the
   surrounding expression (iteration -> list, arithmetic -> 0, string method ->
   ""), so hardening cannot silently turn a float into ``None``.
2. **Regex pass** – rewrites ``os.environ["NAME"]`` and ``os.getenv("NAME")``
   to their default-carrying variants.

The module never raises on invalid input: if the snippet cannot be parsed or
the rewritten snippet no longer parses, the original code is returned.
"""

from __future__ import annotations

import ast
import re
from typing import Any

# --------------------------------------------------------------------------- #
# Heuristics
# --------------------------------------------------------------------------- #
# Response keys that most APIs return as a list.
_LIST_KEYS: frozenset[str] = frozenset(
    {
        "assets",
        "choices",
        "cohorts",
        "data",
        "drafts",
        "edges",
        "entries",
        "events",
        "files",
        "items",
        "keywords",
        "messages",
        "mentions",
        "nodes",
        "orders",
        "products",
        "projects",
        "records",
        "results",
        "rows",
        "slots",
        "tags",
        "tasks",
        "topics",
        "users",
    }
)

# Response keys that most APIs return as a nested object.
_DICT_KEYS: frozenset[str] = frozenset(
    {
        "account",
        "auth",
        "body",
        "details",
        "error",
        "headers",
        "lead",
        "message",
        "meta",
        "metadata",
        "payload",
        "profile",
        "rate_limit",
        "summary",
        "usage",
    }
)

# Response keys that are consumed numerically.
_NUMERIC_KEYS: frozenset[str] = frozenset(
    {
        "amount",
        "count",
        "duration",
        "latency",
        "price",
        "quantity",
        "rate",
        "score",
        "sentiment",
        "total",
        "value",
        "z_score",
    }
)

# Response keys that are consumed as strings.
_STRING_KEYS: frozenset[str] = frozenset(
    {
        "code",
        "content",
        "created_at",
        "currency",
        "description",
        "email",
        "id",
        "key",
        "keyword",
        "model",
        "name",
        "object",
        "query",
        "role",
        "secret",
        "status",
        "text",
        "title",
        "token",
        "type",
        "updated_at",
        "url",
    }
)

# Variable names that almost always hold parsed JSON.
_JSON_NAME_EXACT: frozenset[str] = frozenset(
    {
        "body",
        "content",
        "data",
        "details",
        "entry",
        "event",
        "item",
        "lead",
        "message",
        "meta",
        "order",
        "payload",
        "profile",
        "record",
        "report",
        "response",
        "result",
        "row",
        "stats",
        "summary",
    }
)
_JSON_NAME_SUFFIXES: tuple[str, ...] = (
    "_body",
    "_data",
    "_entry",
    "_item",
    "_json",
    "_payload",
    "_record",
    "_response",
    "_result",
    "_row",
)

_STRING_METHODS: frozenset[str] = frozenset(
    {
        "encode",
        "endswith",
        "format",
        "index",
        "lower",
        "replace",
        "rstrip",
        "split",
        "startswith",
        "strip",
        "upper",
    }
)
_NUMERIC_CALLS: frozenset[str] = frozenset({"float", "int", "round", "sum"})
_ITERABLE_CALLS: frozenset[str] = frozenset(
    {"all", "any", "len", "list", "max", "min", "set", "sorted", "tuple"}
)


def _call_name(node: ast.AST | None) -> str:
    """Return a dotted callable name for ``Name`` / ``Attribute`` chains."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _root_name(node: ast.AST | None) -> str | None:
    """Return the variable a subscript/call chain is rooted in."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, (ast.Subscript, ast.Attribute)):
        return _root_name(node.value)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "get":
            return _root_name(func.value)
        return _root_name(func)
    return None


def _is_json_producer(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call):
        return False
    name = _call_name(node.func)
    if name in {"json.loads", "json.load"}:
        return True
    if name.endswith(".json"):
        return True
    # ``json.loads(response.read().decode(...))`` is covered above.
    return False


def _collect_json_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if value is None:
                continue
            if _is_json_producer(value):
                for target in targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif (
                isinstance(value, ast.Subscript)
                and _root_name(value) in names
                and isinstance(value.ctx, ast.Load)
            ):
                for target in targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(value, ast.Dict):
                # Dict literals are already safe; only dict comprehensions that
                # wrap API data are relevant and those root in a JSON name.
                continue
        elif isinstance(node, ast.For):
            if _root_name(node.iter) in names:
                target = node.target
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, ast.Tuple):
                    for element in target.elts:
                        if isinstance(element, ast.Name):
                            names.add(element.id)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id in _JSON_NAME_EXACT or node.id.endswith(
                _JSON_NAME_SUFFIXES
            ):
                names.add(node.id)

    return names


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    mapping: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            mapping[child] = parent
    return mapping


class _DefensiveSubscript(ast.NodeTransformer):
    """Rewrite string subscript reads on JSON containers into ``.get()``."""

    def __init__(
        self, json_names: set[str], parents: dict[ast.AST, ast.AST]
    ) -> None:
        self.json_names = json_names
        self.parents = parents
        self.replacements: list[tuple[ast.Subscript, ast.AST]] = []

    # -- helpers --------------------------------------------------------- #
    def _is_container(self, node: ast.AST) -> bool:
        root = _root_name(node)
        return bool(root and root in self.json_names)

    def _default_for(self, node: ast.Subscript, key: str) -> ast.AST:
        parent = self.parents.get(node)

        # ``data["choices"][0]`` – the key must yield an indexable list.
        if (
            isinstance(parent, ast.Subscript)
            and isinstance(parent.slice, ast.Constant)
            and isinstance(parent.slice.value, int)
        ):
            if key in _LIST_KEYS or key in _DICT_KEYS:
                return ast.List(elts=[ast.Dict(keys=[], values=[])], ctx=ast.Load())
            return ast.Constant(value="")

        # Iteration, len() and friends need an iterable default.
        if isinstance(parent, (ast.For, ast.comprehension)):
            return ast.List(elts=[], ctx=ast.Load())
        if isinstance(parent, ast.Call):
            call_name = _call_name(parent.func)
            if call_name in _ITERABLE_CALLS:
                if call_name in {"max", "min", "sum"} and key in _NUMERIC_KEYS:
                    return ast.Constant(value=0)
                return ast.List(elts=[], ctx=ast.Load())
            if call_name in _NUMERIC_CALLS:
                return ast.Constant(value=0)
            if isinstance(parent.func, ast.Attribute) and parent.func.attr in _STRING_METHODS:
                return ast.Constant(value="")

        if isinstance(parent, ast.JoinedStr):
            return ast.Constant(value="")

        if isinstance(parent, ast.BinOp):
            other = parent.right if parent.left is node else parent.left
            if isinstance(other, ast.Constant) and isinstance(other.value, str):
                return ast.Constant(value="")
            return ast.Constant(value=0)

        if isinstance(parent, ast.Compare):
            comparators = list(parent.comparators)
            if any(
                isinstance(item, ast.Constant) and isinstance(item.value, str)
                for item in comparators
            ):
                return ast.Constant(value="")
            return ast.Constant(value=0)

        if key in _NUMERIC_KEYS:
            return ast.Constant(value=0)
        if key in _DICT_KEYS:
            return ast.Dict(keys=[], values=[])
        if key in _STRING_KEYS:
            return ast.Constant(value="")
        if key in _LIST_KEYS:
            return ast.List(elts=[], ctx=ast.Load())
        return ast.Constant(value="")

    # -- visitor --------------------------------------------------------- #
    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        self.generic_visit(node)
        if not isinstance(node.ctx, ast.Load):
            return node
        if not self._is_container(node.value):
            return node
        key = node.slice
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            return node

        get_call = ast.Call(
            func=ast.Attribute(
                value=node.value, attr="get", ctx=ast.Load()
            ),
            args=[key, self._default_for(node, key.value)],
            keywords=[],
        )
        ast.copy_location(get_call, node)
        ast.fix_missing_locations(get_call)
        self.replacements.append((node, get_call))
        return get_call


def _offset(source: str, line: int, column: int) -> int | None:
    lines = source.splitlines(keepends=True)
    if line < 1 or line > len(lines):
        return None
    return sum(len(item) for item in lines[: line - 1]) + column


def _splice_replacements(
    source: str,
    replacements: list[tuple[ast.Subscript, ast.AST]],
    parents: dict[ast.AST, ast.AST],
) -> str:
    """Splice only the outermost rewritten expression into the source.

    Nested rewrites are already contained in the unparsed outermost
    expression, so applying them separately would corrupt the offsets.
    """
    replacement_nodes = {node for node, _ in replacements}
    outermost: list[tuple[ast.Subscript, ast.AST]] = []
    for node, new_node in replacements:
        ancestor = parents.get(node)
        nested = False
        while ancestor is not None:
            if ancestor in replacement_nodes:
                nested = True
                break
            ancestor = parents.get(ancestor)
        if not nested:
            outermost.append((node, new_node))

    edits: list[tuple[int, int, str]] = []
    for node, new_node in outermost:
        start = _offset(source, node.lineno, node.col_offset)
        end = _offset(source, node.end_lineno or node.lineno, node.end_col_offset or 0)
        if start is None or end is None or end <= start:
            continue
        edits.append((start, end, ast.unparse(new_node)))

    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


_IMPORTABLE_MODULES: tuple[str, ...] = (
    "argparse",
    "base64",
    "collections",
    "contextlib",
    "dataclasses",
    "datetime",
    "difflib",
    "email.utils",
    "functools",
    "hashlib",
    "hmac",
    "http.client",
    "itertools",
    "json",
    "logging",
    "math",
    "os",
    "re",
    "socket",
    "ssl",
    "statistics",
    "sys",
    "time",
    "typing",
    "unittest",
    "urllib.error",
    "urllib.parse",
    "urllib.request",
    "uuid",
)


def _imported_modules(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.add(node.module.split(".")[0])
    return imported


def ensure_imports(source: str) -> tuple[str, int]:
    """Prepend imports for standard-library modules that are used but missing.

    The validator rejects a snippet that uses ``os.environ`` without
    ``import os`` – a very common LLM slip. Adding the import deterministically
    is safer than spending another LLM round.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, 0

    imported = _imported_modules(tree)
    needed: list[str] = []
    for module in _IMPORTABLE_MODULES:
        if module in imported:
            continue
        if f"{module}." not in source:
            continue
        # ``import urllib.request`` does not expose ``urllib.parse``; checking
        # the exact dotted module name is intentional.
        needed.append(module)
    if not needed:
        return source, 0

    deduped: list[str] = []
    for module in needed:
        if module not in deduped:
            deduped.append(module)

    header = "\n".join(f"import {module}" for module in deduped) + "\n"
    lines = source.splitlines(keepends=True)
    insert_at = 0
    for index, node in enumerate(tree.body):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and index == 0
        ):
            insert_at = max(insert_at, node.end_lineno or 0)
        elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_at = max(insert_at, node.end_lineno or 0)

    if insert_at:
        lines.insert(insert_at, header)
    else:
        lines.insert(0, header)
    candidate = "".join(lines)
    try:
        ast.parse(candidate)
    except SyntaxError:
        return source, 0
    return candidate, len(deduped)


_ENV_SUBSCRIPT = re.compile(
    r"""os\.environ\[\s*(?P<quote>['"])(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)\s*\]"""
)
_GETENV_NO_DEFAULT = re.compile(
    r"""os\.getenv\(\s*(?P<quote>['"])(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)\s*\)"""
)


def _hardening_regex(source: str) -> tuple[str, int]:
    count = 0

    def _env_sub(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return (
            f"os.environ.get({match.group('quote')}{match.group('name')}"
            f"{match.group('quote')}, \"\")"
        )

    def _getenv(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return (
            f"os.getenv({match.group('quote')}{match.group('name')}"
            f"{match.group('quote')}, \"\")"
        )

    source = _ENV_SUBSCRIPT.sub(_env_sub, source)
    source = _GETENV_NO_DEFAULT.sub(_getenv, source)
    return source, count


def harden_code(source: str) -> tuple[str, dict[str, Any]]:
    """Return ``(hardened_source, stats)``.

    ``stats`` always contains ``subscripts`` (AST rewrites) and
    ``environment`` (regex rewrites). On any parse failure the original source
    is returned and ``stats["error"]`` explains why.
    """
    stats: dict[str, Any] = {"subscripts": 0, "environment": 0, "imports": 0}
    if not isinstance(source, str) or not source.strip():
        return source, stats

    hardened = source
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        stats["error"] = f"SyntaxError: {error.msg}"
        tree = None

    if tree is not None:
        try:
            json_names = _collect_json_names(tree)
            parents = _parents(tree)
            transformer = _DefensiveSubscript(json_names, parents)
            new_tree = transformer.visit(tree)
            ast.fix_missing_locations(new_tree)
            if transformer.replacements:
                candidate = _splice_replacements(
                    source, transformer.replacements, parents
                )
                try:
                    ast.parse(candidate)
                except SyntaxError:
                    # Splicing failed – fall back to the AST-unparsed version
                    # (comments are lost, but the code stays correct).
                    candidate = ast.unparse(new_tree)
                hardened = candidate
                stats["subscripts"] = len(transformer.replacements)
        except Exception as error:  # noqa: BLE001 - hardening must never break
            stats["error"] = f"{type(error).__name__}: {error}"

    hardened, env_count = _hardening_regex(hardened)
    stats["environment"] = env_count
    hardened, import_count = ensure_imports(hardened)
    stats["imports"] = import_count
    try:
        ast.parse(hardened)
    except SyntaxError as error:
        stats["error"] = f"post-parse SyntaxError: {error.msg}"
        return source, stats
    return hardened, stats


def harden_workflow(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Harden every ``code_snippet`` of a workflow in place.

    Returns one stats entry per step so the daemon can log exactly how many
    unsafe accesses were removed.
    """
    details = workflow.get("details") or {}
    report: list[dict[str, Any]] = []
    for index, step in enumerate(details.get("steps") or [], start=1):
        if not isinstance(step, dict):
            continue
        code = str(step.get("code_snippet") or "")
        hardened, stats = harden_code(code)
        if hardened != code:
            step["code_snippet"] = hardened
        stats["step"] = index
        stats["title"] = str(step.get("title") or "")
        report.append(stats)
    return report


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    samples = [
        """import json, urllib.request
response = urllib.request.urlopen("https://api.example.com/v1/items")
payload = json.loads(response.read().decode("utf-8"))
records = payload["data"]
for record in payload["data"]:
    print(record["text"])
count = payload["count"] + 1
name = payload["profile"]["name"]
token = os.environ["API_TOKEN"]
""",
        """import json
data = json.loads('{"choices": [{"message": {"content": "0.8"}}]}')
content = data["choices"][0]["message"]["content"]
sentiment = float(data["choices"][0]["message"]["content"])
""",
    ]
    for sample in samples:
        result, information = harden_code(sample)
        print("-" * 70)
        print(result)
        print(information)