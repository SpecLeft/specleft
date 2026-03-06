# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""TypeScript/JavaScript JSDoc extraction for discovery miners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specleft.discovery.miners.shared.common import (
    field_text,
    line_number,
    make_docstring_item,
    node_text,
)
from specleft.discovery.models import DiscoveredItem, SupportedLanguage

_JSDOC_TARGET_TYPES = frozenset(
    {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "export_statement",
    }
)


def extract_jsdoc_items(
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
    language: SupportedLanguage,
) -> list[DiscoveredItem]:
    """Extract attached JSDoc comments for TS/JS declarations."""
    items: list[DiscoveredItem] = []

    def walk(parent: Any) -> None:
        children = list(getattr(parent, "children", ()))
        for index, child in enumerate(children):
            if child.type == "comment":
                jsdoc_text = _normalise_jsdoc(node_text(child, source_bytes))
                if jsdoc_text:
                    target = _resolve_jsdoc_target(children, index, source_bytes)
                    if target is not None:
                        kind, name = _target_kind_and_name(
                            target, source_bytes, file_path
                        )
                        items.append(
                            make_docstring_item(
                                file_path=file_path,
                                line_number=line_number(child),
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
        return "class", field_text(node, "name", source_bytes)
    if node.type == "method_definition":
        return "method", field_text(node, "name", source_bytes)
    if node.type == "function_declaration":
        return "function", field_text(node, "name", source_bytes)
    if node.type == "export_statement":
        return "module", file_path.stem
    return "module", file_path.stem


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
