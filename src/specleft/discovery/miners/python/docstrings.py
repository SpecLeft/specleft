# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Python docstring extraction for discovery miners."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specleft.discovery.miners.shared.common import (
    field_text,
    line_number,
    make_docstring_item,
    node_text,
    walk_tree,
)
from specleft.discovery.models import DiscoveredItem, SupportedLanguage

_MEANINGFUL_INIT_DOCSTRING_LEN = 10


@dataclass(frozen=True)
class _DocstringMatch:
    text: str
    line_number: int


def extract_python_items(
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
) -> list[DiscoveredItem]:
    """Extract module/class/function docstrings from a Python source tree."""
    items: list[DiscoveredItem] = []
    module_doc = _extract_python_leading_docstring(root_node, source_bytes)
    if module_doc is not None:
        items.append(
            make_docstring_item(
                file_path=file_path,
                line_number=module_doc.line_number,
                language=SupportedLanguage.PYTHON,
                target_kind="module",
                target_name=file_path.stem,
                text=module_doc.text,
            )
        )

    for node in walk_tree(root_node):
        if node.type == "class_definition":
            name = field_text(node, "name", source_bytes)
            class_doc = _extract_python_body_docstring(node, source_bytes)
            if class_doc is None or not name:
                continue
            items.append(
                make_docstring_item(
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

        name = field_text(node, "name", source_bytes)
        function_doc = _extract_python_body_docstring(node, source_bytes)
        if function_doc is None or not name:
            continue
        if (
            name == "__init__"
            and len(function_doc.text.strip()) <= _MEANINGFUL_INIT_DOCSTRING_LEN
        ):
            continue

        items.append(
            make_docstring_item(
                file_path=file_path,
                line_number=function_doc.line_number,
                language=SupportedLanguage.PYTHON,
                target_kind="function",
                target_name=name,
                text=function_doc.text,
            )
        )

    return items


def _extract_python_leading_docstring(
    container_node: Any,
    source_bytes: bytes,
) -> _DocstringMatch | None:
    expression = _first_expression_string(container_node)
    if expression is None:
        return None
    text = _clean_python_string(node_text(expression, source_bytes))
    if not text:
        return None
    return _DocstringMatch(text=text, line_number=line_number(expression))


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
