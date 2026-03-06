# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""TypeScript/JavaScript test-function miner."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from specleft.discovery.context import MinerContext
from specleft.discovery.miners.shared.common import elapsed_ms, line_number, node_text
from specleft.discovery.models import (
    DiscoveredItem,
    ItemKind,
    MinerErrorKind,
    MinerResult,
    SupportedLanguage,
    TestFunctionMeta,
)

_TEST_PATTERNS = (
    "*.test.ts",
    "*.spec.ts",
    "*.test.js",
    "*.spec.js",
    "*.test.tsx",
    "*.spec.tsx",
)
_TEST_CALL_NAMES = frozenset({"it", "test"})
_CALLBACK_NODE_TYPES = frozenset(
    {
        "arrow_function",
        "function",
        "function_expression",
    }
)
_STRING_NODE_TYPES = frozenset({"string", "template_string"})
_KNOWN_FRAMEWORKS = frozenset({"jest", "vitest"})


class TypeScriptTestMiner:
    """Extract Jest/Vitest test calls from TypeScript/JavaScript test files."""

    miner_id = uuid.UUID("aa5151b6-3805-419c-a726-a56755300dda")
    name = "typescript_test_functions"
    languages = frozenset({SupportedLanguage.TYPESCRIPT, SupportedLanguage.JAVASCRIPT})

    def mine(self, ctx: MinerContext) -> MinerResult:
        started = time.perf_counter()
        items: list[DiscoveredItem] = []
        parse_failures: list[Path] = []

        for rel_path in ctx.file_index.files_matching(*_TEST_PATTERNS):
            abs_path = ctx.root / rel_path
            parsed = ctx.registry.parse(abs_path)
            if parsed is None:
                parse_failures.append(rel_path)
                continue

            root_node, language = parsed
            if language not in self.languages:
                continue

            try:
                source_bytes = abs_path.read_bytes()
            except OSError:
                parse_failures.append(rel_path)
                continue

            framework = _primary_framework(ctx, language)
            items.extend(
                _extract_test_items(
                    root_node=root_node,
                    source_bytes=source_bytes,
                    file_path=rel_path,
                    language=language,
                    framework=framework,
                )
            )

        error_kind: MinerErrorKind | None = None
        error: str | None = None
        if parse_failures:
            error_kind = MinerErrorKind.PARSE_ERROR
            files = ", ".join(path.as_posix() for path in parse_failures)
            error = f"Failed to parse TypeScript/JavaScript test files: {files}"

        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            error=error,
            error_kind=error_kind,
            duration_ms=elapsed_ms(started),
        )


def _primary_framework(ctx: MinerContext, language: SupportedLanguage) -> str:
    frameworks = ctx.frameworks.get(language, [])

    if not frameworks and language is SupportedLanguage.JAVASCRIPT:
        frameworks = ctx.frameworks.get(SupportedLanguage.TYPESCRIPT, [])
    if not frameworks and language is SupportedLanguage.TYPESCRIPT:
        frameworks = ctx.frameworks.get(SupportedLanguage.JAVASCRIPT, [])

    return frameworks[0] if frameworks else "unknown"


def _extract_test_items(
    *,
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
    language: SupportedLanguage,
    framework: str,
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []

    def walk(node: Any, describe_stack: list[str]) -> None:
        describe_payload = _describe_payload(node, source_bytes)
        if describe_payload is not None:
            describe_name, callback = describe_payload
            if callback is not None:
                next_stack = describe_stack
                if describe_name:
                    next_stack = [*describe_stack, describe_name]
                walk(callback, next_stack)
            return

        call_payload = _test_call_payload(node, source_bytes)
        if call_payload is not None:
            test_name, call_style, has_todo = call_payload
            metadata = TestFunctionMeta(
                framework=framework,
                class_name=describe_stack[-1] if describe_stack else None,
                has_docstring=False,
                docstring=None,
                is_parametrized=False,
                call_style=call_style,
                has_todo=has_todo,
            )
            items.append(
                DiscoveredItem(
                    kind=ItemKind.TEST_FUNCTION,
                    name=test_name,
                    file_path=file_path,
                    line_number=line_number(node),
                    language=language,
                    raw_text=None,
                    metadata=metadata.model_dump(),
                    confidence=_confidence_for(file_path, framework),
                )
            )

        for child in getattr(node, "named_children", ()):  # pragma: no branch
            walk(child, describe_stack)

    walk(root_node, [])
    return items


def _describe_payload(node: Any, source_bytes: bytes) -> tuple[str | None, Any] | None:
    if getattr(node, "type", "") != "call_expression":
        return None

    function_node = node.child_by_field_name("function")
    if function_node is None:
        return None

    call_target, _ = _call_target(function_node, source_bytes)
    if call_target != "describe":
        return None

    args = _call_arguments(node)
    describe_name = _first_string_arg(args, source_bytes)
    callback = _callback_arg(args)
    return describe_name, callback


def _test_call_payload(
    node: Any,
    source_bytes: bytes,
) -> tuple[str, str, bool] | None:
    if getattr(node, "type", "") != "call_expression":
        return None

    function_node = node.child_by_field_name("function")
    if function_node is None:
        return None

    call_target, has_todo = _call_target(function_node, source_bytes)
    if call_target not in _TEST_CALL_NAMES:
        return None

    name = _first_string_arg(_call_arguments(node), source_bytes)
    if name is None:
        return None

    return name, call_target, has_todo


def _call_target(function_node: Any, source_bytes: bytes) -> tuple[str | None, bool]:
    text = node_text(function_node, source_bytes).strip()

    if text in _TEST_CALL_NAMES or text == "describe":
        return text, False

    if text in {"it.todo", "test.todo"}:
        return text.split(".", maxsplit=1)[0], True

    if getattr(function_node, "type", "") != "member_expression":
        return None, False

    object_name = _strip_quotes(_field_value(function_node, "object", source_bytes))
    property_name = _strip_quotes(_field_value(function_node, "property", source_bytes))

    if object_name in _TEST_CALL_NAMES and property_name == "todo":
        return object_name, True
    if object_name == "describe":
        return object_name, False

    return None, False


def _call_arguments(node: Any) -> list[Any]:
    arguments_node = node.child_by_field_name("arguments")
    if arguments_node is None:
        return []
    return list(getattr(arguments_node, "named_children", ()))


def _first_string_arg(args: list[Any], source_bytes: bytes) -> str | None:
    for arg in args:
        if getattr(arg, "type", "") not in _STRING_NODE_TYPES:
            continue
        value = _clean_string(node_text(arg, source_bytes))
        if value:
            return value
    return None


def _callback_arg(args: list[Any]) -> Any | None:
    for arg in args:
        if getattr(arg, "type", "") in _CALLBACK_NODE_TYPES:
            return arg
    return None


def _field_value(node: Any, field: str, source_bytes: bytes) -> str:
    field_node = node.child_by_field_name(field)
    if field_node is None:
        return ""
    return node_text(field_node, source_bytes).strip()


def _clean_string(raw: str) -> str:
    stripped = raw.strip()
    return _strip_quotes(stripped)


def _strip_quotes(value: str) -> str:
    for quote in ('"', "'", "`"):
        if value.startswith(quote) and value.endswith(quote) and len(value) >= 2:
            return value[1:-1].strip()
    return value.strip()


def _confidence_for(file_path: Path, framework: str) -> float:
    if framework in _KNOWN_FRAMEWORKS and ".spec." in file_path.name:
        return 0.9
    return 0.7
