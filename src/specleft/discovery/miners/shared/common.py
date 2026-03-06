# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared helpers for discovery miners."""

from __future__ import annotations

import fnmatch
import time
from pathlib import Path
from typing import Any

from specleft.discovery.context import MinerContext
from specleft.discovery.models import (
    DiscoveredItem,
    DocstringMeta,
    ItemKind,
    SupportedLanguage,
)

CONFIDENCE = 0.8
TEST_FILE_PATTERNS = (
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


def candidate_source_files(ctx: MinerContext) -> list[Path]:
    """Return configured source files in deterministic order."""
    source_dirs = ctx.config.source_dirs
    if not source_dirs:
        return []

    return sorted(
        ctx.file_index.files_under(*source_dirs),
        key=lambda value: value.as_posix(),
    )


def is_test_file(path: Path) -> bool:
    """Return whether a path should be excluded as a test file."""
    file_name = path.name
    if any(part in {"tests", "__tests__"} for part in path.parts):
        return True
    return any(fnmatch.fnmatch(file_name, pattern) for pattern in TEST_FILE_PATTERNS)


def make_docstring_item(
    *,
    file_path: Path,
    line_number: int,
    language: SupportedLanguage,
    target_kind: str,
    target_name: str | None,
    text: str,
) -> DiscoveredItem:
    """Build a typed discovery item for docstring/JSDoc output."""
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
        confidence=CONFIDENCE,
    )


def elapsed_ms(started: float) -> int:
    """Return elapsed milliseconds from a `time.perf_counter()` start."""
    return max(0, int((time.perf_counter() - started) * 1000))


def walk_tree(node: Any) -> list[Any]:
    """Return all descendant nodes in depth-first order."""
    nodes: list[Any] = []
    for child in getattr(node, "children", ()):
        nodes.append(child)
        nodes.extend(walk_tree(child))
    return nodes


def line_number(node: Any) -> int:
    """Return 1-based line number for a tree-sitter node."""
    return int(node.start_point[0]) + 1


def field_text(node: Any, field: str, source_bytes: bytes) -> str | None:
    """Return source text for a named field on a node."""
    field_node = node.child_by_field_name(field)
    if field_node is None:
        return None
    text = node_text(field_node, source_bytes).strip()
    return text or None


def node_text(node: Any, source_bytes: bytes) -> str:
    """Return best-effort source text for a tree-sitter node."""
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
