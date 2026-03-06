# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Python test-function miner."""

from __future__ import annotations

import ast
import time
import uuid
from pathlib import Path
from typing import Any

from specleft.discovery.context import MinerContext
from specleft.discovery.miners.shared.common import line_number, node_text
from specleft.discovery.models import (
    DiscoveredItem,
    ItemKind,
    MinerErrorKind,
    MinerResult,
    SupportedLanguage,
    TestFunctionMeta,
)

_TEST_PATTERNS = ("test_*.py", "*_test.py")
_KNOWN_FRAMEWORKS = {"pytest", "unittest"}


class PythonTestMiner:
    """Extract Python test functions from indexed test files."""

    miner_id = uuid.UUID("a7b21db5-0d22-41be-9902-7c725e63892e")
    name = "python_test_functions"
    languages = frozenset({SupportedLanguage.PYTHON})

    def mine(self, ctx: MinerContext) -> MinerResult:
        started = time.perf_counter()
        framework = _primary_framework(ctx)
        items: list[DiscoveredItem] = []
        parse_failures: list[Path] = []

        for rel_path in ctx.file_index.files_matching(*_TEST_PATTERNS):
            abs_path = ctx.root / rel_path
            parsed = ctx.registry.parse(abs_path)
            if parsed is None:
                parse_failures.append(rel_path)
                continue

            root_node, language = parsed
            if language is not SupportedLanguage.PYTHON:
                continue

            try:
                source_bytes = abs_path.read_bytes()
            except OSError:
                parse_failures.append(rel_path)
                continue

            items.extend(
                _extract_test_items(
                    root_node=root_node,
                    source_bytes=source_bytes,
                    file_path=rel_path,
                    framework=framework,
                )
            )

        error_kind: MinerErrorKind | None = None
        error: str | None = None
        if parse_failures:
            error_kind = MinerErrorKind.PARSE_ERROR
            files = ", ".join(path.as_posix() for path in parse_failures)
            error = f"Failed to parse Python test files: {files}"

        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            error=error,
            error_kind=error_kind,
            duration_ms=max(0, int((time.perf_counter() - started) * 1000)),
        )


def _primary_framework(ctx: MinerContext) -> str:
    frameworks = ctx.frameworks.get(SupportedLanguage.PYTHON, [])
    return frameworks[0] if frameworks else "unknown"


def _extract_test_items(
    *,
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
    framework: str,
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []
    for node in getattr(root_node, "named_children", ()):
        test_function = _extract_function(node, source_bytes)
        if test_function is not None:
            function_node, decorators = test_function
            item = _to_discovered_item(
                function_node=function_node,
                decorators=decorators,
                source_bytes=source_bytes,
                file_path=file_path,
                framework=framework,
                class_name=None,
            )
            if item is not None:
                items.append(item)
            continue

        if node.type != "class_definition":
            continue

        class_name = _field_text(node, "name", source_bytes)
        if not class_name or not class_name.startswith("Test"):
            continue

        body = node.child_by_field_name("body")
        if body is None:
            continue

        for member in getattr(body, "named_children", ()):
            method = _extract_function(member, source_bytes)
            if method is None:
                continue
            function_node, decorators = method
            item = _to_discovered_item(
                function_node=function_node,
                decorators=decorators,
                source_bytes=source_bytes,
                file_path=file_path,
                framework=framework,
                class_name=class_name,
            )
            if item is not None:
                items.append(item)

    return items


def _extract_function(node: Any, source_bytes: bytes) -> tuple[Any, list[str]] | None:
    if node.type in {"function_definition", "async_function_definition"}:
        return node, []

    if node.type != "decorated_definition":
        return None

    definition = node.child_by_field_name("definition")
    if definition is None or definition.type not in {
        "function_definition",
        "async_function_definition",
    }:
        return None

    decorators = [
        _normalize_decorator(node_text(child, source_bytes))
        for child in getattr(node, "named_children", ())
        if child.type == "decorator"
    ]
    return definition, [value for value in decorators if value]


def _to_discovered_item(
    *,
    function_node: Any,
    decorators: list[str],
    source_bytes: bytes,
    file_path: Path,
    framework: str,
    class_name: str | None,
) -> DiscoveredItem | None:
    name = _field_text(function_node, "name", source_bytes)
    if not name or not name.startswith("test_"):
        return None

    docstring = _extract_docstring(function_node, source_bytes)
    is_parametrized = any(decorator.endswith("parametrize") for decorator in decorators)
    confidence = 0.9 if framework in _KNOWN_FRAMEWORKS else 0.7

    metadata = TestFunctionMeta(
        framework=framework,
        class_name=class_name,
        decorators=decorators,
        has_docstring=docstring is not None,
        docstring=docstring,
        is_parametrized=is_parametrized,
    )

    return DiscoveredItem(
        kind=ItemKind.TEST_FUNCTION,
        name=name,
        file_path=file_path,
        line_number=line_number(function_node),
        language=SupportedLanguage.PYTHON,
        raw_text=docstring,
        metadata=metadata.model_dump(),
        confidence=confidence,
    )


def _normalize_decorator(raw: str) -> str:
    normalized = raw.strip()
    if normalized.startswith("@"):
        normalized = normalized[1:]
    return normalized.split("(", 1)[0].strip()


def _extract_docstring(function_node: Any, source_bytes: bytes) -> str | None:
    body = function_node.child_by_field_name("body")
    if body is None:
        return None

    named_children = list(getattr(body, "named_children", ()))
    if not named_children:
        return None

    first = named_children[0]
    if first.type != "expression_statement":
        return None

    for child in getattr(first, "named_children", ()):
        if child.type in {"string", "concatenated_string"}:
            return _clean_python_string(node_text(child, source_bytes))
    return None


def _clean_python_string(value: str) -> str | None:
    stripped = value.strip()
    if not stripped:
        return None

    try:
        parsed = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        parsed = _strip_wrapping_quotes(stripped)
    if not isinstance(parsed, str):
        return None

    cleaned = parsed.strip()
    return cleaned or None


def _strip_wrapping_quotes(value: str) -> str:
    for quote in ('"""', "'''", '"', "'"):
        if value.startswith(quote) and value.endswith(quote) and len(value) >= 2:
            return value[len(quote) : len(value) - len(quote)].strip()
    return value


def _field_text(node: Any, field: str, source_bytes: bytes) -> str | None:
    field_node = node.child_by_field_name(field)
    if field_node is None:
        return None
    text = node_text(field_node, source_bytes).strip()
    return text or None
