# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""TypeScript/JavaScript API-route miner for Express and Next.js."""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path
from typing import Any

from specleft.discovery.context import MinerContext
from specleft.discovery.miners.shared.common import (
    elapsed_ms,
    line_number,
    node_text,
    walk_tree,
)
from specleft.discovery.models import (
    ApiRouteMeta,
    DiscoveredItem,
    ItemKind,
    MinerErrorKind,
    MinerResult,
    SupportedLanguage,
)

_SUPPORTED_FRAMEWORKS = frozenset({"express", "nextjs"})
_EXPRESS_METHODS = frozenset({"get", "post", "put", "patch", "delete", "use"})
_STRING_NODE_TYPES = frozenset({"string", "template_string"})
_NEXT_ROUTE_FILES = frozenset({"route.ts", "route.js"})
_NEXT_EXPORT_METHODS = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
)
_NEXT_EXPORT_PATTERN = re.compile(
    r"^\s*export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b",
    re.MULTILINE,
)


class TypeScriptRouteMiner:
    """Extract API routes from TS/JS source files."""

    miner_id = uuid.UUID("b06e8c32-c793-41dc-91de-12635d6c4f69")
    name = "typescript_api_routes"
    languages = frozenset({SupportedLanguage.TYPESCRIPT, SupportedLanguage.JAVASCRIPT})

    def mine(self, ctx: MinerContext) -> MinerResult:
        started = time.perf_counter()
        frameworks = _enabled_frameworks(ctx)
        if not frameworks:
            return MinerResult(
                miner_id=self.miner_id,
                miner_name=self.name,
                items=[],
                duration_ms=elapsed_ms(started),
            )

        items: list[DiscoveredItem] = []
        parse_failures: list[Path] = []

        for rel_path in _candidate_files(ctx, frameworks):
            abs_path = ctx.root / rel_path
            parsed = ctx.registry.parse(abs_path)
            if parsed is None:
                parse_failures.append(rel_path)
                continue

            root_node, parsed_language = parsed
            language = _language_for_file(rel_path, parsed_language)

            try:
                source_bytes = abs_path.read_bytes()
            except OSError:
                parse_failures.append(rel_path)
                continue

            if "express" in frameworks:
                items.extend(
                    _extract_express_items(
                        root_node=root_node,
                        source_bytes=source_bytes,
                        file_path=rel_path,
                        language=language,
                    )
                )

            if "nextjs" in frameworks and _is_next_route_file(rel_path):
                items.extend(
                    _extract_nextjs_items(
                        source_bytes=source_bytes,
                        file_path=rel_path,
                        language=language,
                    )
                )

        error_kind: MinerErrorKind | None = None
        error: str | None = None
        if parse_failures:
            error_kind = MinerErrorKind.PARSE_ERROR
            files = ", ".join(path.as_posix() for path in parse_failures)
            error = f"Failed to parse TypeScript/JavaScript route files: {files}"

        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            error=error,
            error_kind=error_kind,
            duration_ms=elapsed_ms(started),
        )


def _enabled_frameworks(ctx: MinerContext) -> tuple[str, ...]:
    detected: list[str] = []
    for language in (SupportedLanguage.TYPESCRIPT, SupportedLanguage.JAVASCRIPT):
        for framework in ctx.frameworks.get(language, []):
            if framework not in _SUPPORTED_FRAMEWORKS or framework in detected:
                continue
            detected.append(framework)
    return tuple(detected)


def _candidate_files(ctx: MinerContext, frameworks: tuple[str, ...]) -> list[Path]:
    candidates: set[Path] = set()
    if "express" in frameworks:
        for language in (SupportedLanguage.TYPESCRIPT, SupportedLanguage.JAVASCRIPT):
            candidates.update(ctx.file_index.files_by_language(language))
    if "nextjs" in frameworks:
        for candidate in ctx.file_index.files_matching("route.ts", "route.js"):
            if _is_next_route_file(candidate):
                candidates.add(candidate)
    return sorted(candidates, key=lambda value: value.as_posix())


def _language_for_file(
    file_path: Path,
    fallback: SupportedLanguage,
) -> SupportedLanguage:
    suffix = file_path.suffix.lower()
    if suffix in {".ts", ".tsx"}:
        return SupportedLanguage.TYPESCRIPT
    if suffix in {".js", ".jsx", ".mjs"}:
        return SupportedLanguage.JAVASCRIPT
    return fallback


def _extract_express_items(
    *,
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
    language: SupportedLanguage,
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []

    for node in walk_tree(root_node):
        if getattr(node, "type", "") != "call_expression":
            continue
        function_node = node.child_by_field_name("function")
        if (
            function_node is None
            or getattr(function_node, "type", "") != "member_expression"
        ):
            continue

        target = _member_call_target(function_node, source_bytes)
        if target is None:
            continue
        receiver, method = target
        if receiver not in {"app", "router"} or method not in _EXPRESS_METHODS:
            continue

        args = _call_arguments(node)
        path = _first_string_arg(args, source_bytes)
        if path is None:
            continue

        http_method = method.upper()
        metadata = ApiRouteMeta(
            http_method=http_method,
            path=path,
            framework="express",
            handler_name=_handler_name(args, source_bytes),
        )
        items.append(
            DiscoveredItem(
                kind=ItemKind.API_ROUTE,
                name=f"{http_method} {path}",
                file_path=file_path,
                line_number=line_number(node),
                language=language,
                raw_text=None,
                metadata=metadata.model_dump(),
                confidence=0.9,
            )
        )

    return items


def _member_call_target(
    function_node: Any, source_bytes: bytes
) -> tuple[str, str] | None:
    object_name = _clean_identifier(_field_value(function_node, "object", source_bytes))
    property_name = _clean_identifier(
        _field_value(function_node, "property", source_bytes)
    )
    if object_name and property_name:
        return object_name, property_name.lower()

    text = node_text(function_node, source_bytes).strip()
    if "." not in text:
        return None
    object_part, property_part = text.rsplit(".", maxsplit=1)
    object_name = _clean_identifier(object_part)
    property_name = _clean_identifier(property_part)
    if not object_name or not property_name:
        return None
    return object_name, property_name.lower()


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


def _handler_name(args: list[Any], source_bytes: bytes) -> str | None:
    for arg in args[1:]:
        arg_type = getattr(arg, "type", "")
        if arg_type in {"identifier", "property_identifier"}:
            value = _clean_identifier(node_text(arg, source_bytes))
            if value:
                return value
    return None


def _extract_nextjs_items(
    *,
    source_bytes: bytes,
    file_path: Path,
    language: SupportedLanguage,
) -> list[DiscoveredItem]:
    route_path = _next_route_path(file_path)
    if route_path is None:
        return []

    source_text = source_bytes.decode("utf-8", errors="ignore")
    items: list[DiscoveredItem] = []
    for match in _NEXT_EXPORT_PATTERN.finditer(source_text):
        method = match.group(1).upper()
        if method not in _NEXT_EXPORT_METHODS:
            continue
        metadata = ApiRouteMeta(
            http_method=method,
            path=route_path,
            framework="nextjs",
            handler_name=method,
            is_file_based_route=True,
        )
        items.append(
            DiscoveredItem(
                kind=ItemKind.API_ROUTE,
                name=f"{method} {route_path}",
                file_path=file_path,
                line_number=_line_from_offset(source_text, match.start()),
                language=language,
                raw_text=None,
                metadata=metadata.model_dump(),
                confidence=0.9,
            )
        )

    return items


def _line_from_offset(source_text: str, offset: int) -> int:
    return source_text.count("\n", 0, offset) + 1


def _is_next_route_file(file_path: Path) -> bool:
    return file_path.name in _NEXT_ROUTE_FILES and "app" in file_path.parts[:-1]


def _next_route_path(file_path: Path) -> str | None:
    if not _is_next_route_file(file_path):
        return None

    parts = list(file_path.parts)
    app_index = parts.index("app")
    route_parts = parts[app_index + 1 : -1]
    if not route_parts:
        return "/"

    normalized = [_normalize_next_segment(segment) for segment in route_parts]
    return "/" + "/".join(normalized)


def _normalize_next_segment(segment: str) -> str:
    if segment.startswith("[") and segment.endswith("]") and len(segment) > 2:
        inner = segment[1:-1]
        if inner.startswith("..."):
            inner = inner[3:]
        if inner:
            return f"{{{inner}}}"
    return segment


def _field_value(node: Any, field: str, source_bytes: bytes) -> str:
    field_node = node.child_by_field_name(field)
    if field_node is None:
        return ""
    return node_text(field_node, source_bytes).strip()


def _clean_string(raw: str) -> str:
    value = raw.strip()
    for quote in ('"', "'", "`"):
        if value.startswith(quote) and value.endswith(quote) and len(value) >= 2:
            return value[1:-1].strip()
    return value


def _clean_identifier(raw: str) -> str:
    value = raw.strip()
    if value.startswith("this."):
        value = value.split(".", maxsplit=1)[1]
    return value.strip(" ?")
