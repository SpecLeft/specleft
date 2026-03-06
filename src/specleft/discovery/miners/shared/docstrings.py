# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Docstring/JSDoc miner for discovery pipeline."""

from __future__ import annotations

import ast
import fnmatch
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specleft.discovery.context import MinerContext
from specleft.discovery.models import (
    DiscoveredItem,
    DocstringMeta,
    ItemKind,
    MinerResult,
    SupportedLanguage,
)

_CONFIDENCE = 0.8
_MEANINGFUL_INIT_DOCSTRING_LEN = 10
_JSDOC_TARGET_TYPES = frozenset(
    {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "export_statement",
    }
)
_TEST_FILE_PATTERNS = (
    "test_*.py",
    "*_test.py",
    "*_tests.py",
    "test_*.ts",
    "*.test.ts",
    "*.spec.ts",
    "test_*.tsx",
    "*.test.tsx",
    "*.spec.tsx",
    "test_*.js",
    "*.test.js",
    "*.spec.js",
    "test_*.jsx",
    "*.test.jsx",
    "*.spec.jsx",
    "test_*.mjs",
    "*.test.mjs",
    "*.spec.mjs",
)


@dataclass(frozen=True)
class _DocstringMatch:
    text: str
    line_number: int


class DocstringMiner:
    """Extract Python docstrings and TypeScript/JavaScript JSDoc comments."""

    miner_id = uuid.UUID("dcc2e631-67e7-4af7-b8ba-ca3397ccae0b")
    name = "docstrings"
    languages = frozenset(
        {
            SupportedLanguage.PYTHON,
            SupportedLanguage.TYPESCRIPT,
            SupportedLanguage.JAVASCRIPT,
        }
    )

    def mine(self, ctx: MinerContext) -> MinerResult:
        started = time.perf_counter()
        items: list[DiscoveredItem] = []

        for rel_path in _candidate_source_files(ctx):
            if _is_test_file(rel_path):
                continue

            abs_path = ctx.root / rel_path
            parsed = ctx.registry.parse(abs_path)
            if parsed is None:
                continue

            try:
                source_bytes = abs_path.read_bytes()
            except OSError:
                continue

            root_node, language = parsed
            if language == SupportedLanguage.PYTHON:
                items.extend(_extract_python_items(root_node, source_bytes, rel_path))
            elif language in (
                SupportedLanguage.TYPESCRIPT,
                SupportedLanguage.JAVASCRIPT,
            ):
                items.extend(
                    _extract_jsdoc_items(root_node, source_bytes, rel_path, language)
                )

        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            duration_ms=_elapsed_ms(started),
        )


def _candidate_source_files(ctx: MinerContext) -> list[Path]:
    source_dirs = ctx.config.source_dirs
    if not source_dirs:
        return []

    return sorted(
        ctx.file_index.files_under(*source_dirs),
        key=lambda value: value.as_posix(),
    )


def _extract_python_items(
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []
    module_doc = _extract_python_leading_docstring(root_node, source_bytes)
    if module_doc is not None:
        items.append(
            _make_item(
                file_path=file_path,
                line_number=module_doc.line_number,
                language=SupportedLanguage.PYTHON,
                target_kind="module",
                target_name=file_path.stem,
                text=module_doc.text,
            )
        )

    for node in _walk_tree(root_node):
        if node.type == "class_definition":
            name = _field_text(node, "name", source_bytes)
            class_doc = _extract_python_body_docstring(node, source_bytes)
            if class_doc is None or not name:
                continue
            items.append(
                _make_item(
                    file_path=file_path,
                    line_number=class_doc.line_number,
                    language=SupportedLanguage.PYTHON,
                    target_kind="class",
                    target_name=name,
                    text=class_doc.text,
                )
            )
            continue

        if node.type not in {"function_definition", "async_function_definition"}:
            continue

        name = _field_text(node, "name", source_bytes)
        function_doc = _extract_python_body_docstring(node, source_bytes)
        if function_doc is None or not name:
            continue
        if (
            name == "__init__"
            and len(function_doc.text.strip()) <= _MEANINGFUL_INIT_DOCSTRING_LEN
        ):
            continue

        items.append(
            _make_item(
                file_path=file_path,
                line_number=function_doc.line_number,
                language=SupportedLanguage.PYTHON,
                target_kind="function",
                target_name=name,
                text=function_doc.text,
            )
        )

    return items


def _extract_jsdoc_items(
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
    language: SupportedLanguage,
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []

    def walk(parent: Any) -> None:
        children = list(getattr(parent, "children", ()))
        for index, child in enumerate(children):
            if child.type == "comment":
                jsdoc_text = _normalise_jsdoc(_node_text(child, source_bytes))
                if jsdoc_text:
                    target = _resolve_jsdoc_target(children, index, source_bytes)
                    if target is not None:
                        kind, name = _target_kind_and_name(
                            target, source_bytes, file_path
                        )
                        items.append(
                            _make_item(
                                file_path=file_path,
                                line_number=_line_number(child),
                                language=language,
                                target_kind=kind,
                                target_name=name,
                                text=jsdoc_text,
                            )
                        )

            walk(child)

    walk(root_node)
    return items


def _resolve_jsdoc_target(
    siblings: list[Any],
    comment_index: int,
    source_bytes: bytes,
) -> Any | None:
    comment_node = siblings[comment_index]
    for candidate in siblings[comment_index + 1 :]:
        if candidate.type == "comment":
            continue

        target = _unwrap_export_target(candidate)
        if target is None:
            break

        if not _is_immediately_before(comment_node, target, source_bytes):
            break
        return target
    return None


def _unwrap_export_target(node: Any) -> Any | None:
    if node.type in _JSDOC_TARGET_TYPES and node.type != "export_statement":
        return node
    if node.type != "export_statement":
        return None

    for child in getattr(node, "named_children", ()):
        if child.type in _JSDOC_TARGET_TYPES and child.type != "export_statement":
            return child
    return node


def _is_immediately_before(
    comment_node: Any, target_node: Any, source_bytes: bytes
) -> bool:
    source_text = source_bytes.decode("utf-8", errors="ignore")
    lines = source_text.splitlines()
    comment_line = int(comment_node.end_point[0])
    target_line = int(target_node.start_point[0])
    if target_line < comment_line:
        return False
    if target_line == comment_line:
        return True
    for index in range(comment_line + 1, target_line):
        if index >= len(lines):
            break
        if lines[index].strip():
            return False
    return True


def _target_kind_and_name(
    node: Any,
    source_bytes: bytes,
    file_path: Path,
) -> tuple[str, str | None]:
    if node.type == "class_declaration":
        return "class", _field_text(node, "name", source_bytes)
    if node.type == "method_definition":
        return "method", _field_text(node, "name", source_bytes)
    if node.type == "function_declaration":
        return "function", _field_text(node, "name", source_bytes)
    if node.type == "export_statement":
        return "module", file_path.stem
    return "module", file_path.stem


def _extract_python_leading_docstring(
    container_node: Any,
    source_bytes: bytes,
) -> _DocstringMatch | None:
    expression = _first_expression_string(container_node)
    if expression is None:
        return None
    text = _clean_python_string(_node_text(expression, source_bytes))
    if not text:
        return None
    return _DocstringMatch(text=text, line_number=_line_number(expression))


def _extract_python_body_docstring(
    definition_node: Any,
    source_bytes: bytes,
) -> _DocstringMatch | None:
    body = definition_node.child_by_field_name("body")
    if body is None:
        return None
    return _extract_python_leading_docstring(body, source_bytes)


def _first_expression_string(container_node: Any) -> Any | None:
    named_children = list(getattr(container_node, "named_children", ()))
    if not named_children:
        return None
    first = named_children[0]
    if first.type != "expression_statement":
        return None

    for child in getattr(first, "named_children", ()):
        if child.type in {"string", "concatenated_string"}:
            return child
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


def _normalise_jsdoc(raw_comment: str) -> str | None:
    stripped = raw_comment.strip()
    if not stripped.startswith("/**"):
        return None

    content = stripped
    if content.startswith("/**"):
        content = content[3:]
    if content.endswith("*/"):
        content = content[:-2]

    lines = []
    for line in content.splitlines():
        cleaned = line.lstrip()
        if cleaned.startswith("*"):
            cleaned = cleaned[1:]
            if cleaned.startswith(" "):
                cleaned = cleaned[1:]
        lines.append(cleaned.rstrip())

    text = "\n".join(lines).strip()
    return text or None


def _make_item(
    *,
    file_path: Path,
    line_number: int,
    language: SupportedLanguage,
    target_kind: str,
    target_name: str | None,
    text: str,
) -> DiscoveredItem:
    item_name = (
        f"{target_kind}:{target_name}" if target_name else f"module:{file_path.stem}"
    )
    metadata = DocstringMeta(
        target_kind=target_kind,
        target_name=target_name,
        text=text,
    )
    return DiscoveredItem(
        kind=ItemKind.DOCSTRING,
        name=item_name,
        file_path=file_path,
        line_number=line_number,
        language=language,
        raw_text=text,
        metadata=metadata.model_dump(),
        confidence=_CONFIDENCE,
    )


def _walk_tree(node: Any) -> list[Any]:
    nodes: list[Any] = []
    for child in getattr(node, "children", ()):
        nodes.append(child)
        nodes.extend(_walk_tree(child))
    return nodes


def _line_number(node: Any) -> int:
    return int(node.start_point[0]) + 1


def _field_text(node: Any, field: str, source_bytes: bytes) -> str | None:
    field_node = node.child_by_field_name(field)
    if field_node is None:
        return None
    text = _node_text(field_node, source_bytes).strip()
    return text or None


def _node_text(node: Any, source_bytes: bytes) -> str:
    raw = getattr(node, "text", None)
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        return raw

    start_byte = getattr(node, "start_byte", None)
    end_byte = getattr(node, "end_byte", None)
    if isinstance(start_byte, int) and isinstance(end_byte, int):
        return source_bytes[start_byte:end_byte].decode("utf-8", errors="ignore")
    return ""


def _is_test_file(path: Path) -> bool:
    file_name = path.name
    if any(part in {"tests", "__tests__"} for part in path.parts):
        return True
    return any(fnmatch.fnmatch(file_name, pattern) for pattern in _TEST_FILE_PATTERNS)


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
