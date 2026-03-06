# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Python API-route miner for FastAPI, Flask, and Django."""

from __future__ import annotations

import ast
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specleft.discovery.context import MinerContext
from specleft.discovery.miners.shared.common import (
    elapsed_ms,
    field_text,
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

_SUPPORTED_FRAMEWORKS = frozenset({"fastapi", "flask", "django"})
_FASTAPI_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head"}
)


@dataclass(frozen=True)
class _RouteMatch:
    framework: str
    path: str
    http_method: str | list[str]
    handler_name: str | None = None
    response_model: str | None = None


class PythonRouteMiner:
    """Extract HTTP routes from Python files using framework-specific patterns."""

    miner_id = uuid.UUID("007ab65e-e4e8-4b7e-9c33-163635168071")
    name = "python_api_routes"
    languages = frozenset({SupportedLanguage.PYTHON})

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

        for rel_path in ctx.file_index.files_by_language(SupportedLanguage.PYTHON):
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
                _extract_route_items(
                    root_node=root_node,
                    source_bytes=source_bytes,
                    file_path=rel_path,
                    frameworks=frameworks,
                )
            )

        error_kind: MinerErrorKind | None = None
        error: str | None = None
        if parse_failures:
            error_kind = MinerErrorKind.PARSE_ERROR
            files = ", ".join(path.as_posix() for path in parse_failures)
            error = f"Failed to parse Python route files: {files}"

        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            error=error,
            error_kind=error_kind,
            duration_ms=elapsed_ms(started),
        )


def _enabled_frameworks(ctx: MinerContext) -> tuple[str, ...]:
    detected = ctx.frameworks.get(SupportedLanguage.PYTHON, [])
    enabled: list[str] = []
    for framework in detected:
        if framework in _SUPPORTED_FRAMEWORKS and framework not in enabled:
            enabled.append(framework)
    return tuple(enabled)


def _extract_route_items(
    *,
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
    frameworks: tuple[str, ...],
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []
    framework_set = set(frameworks)

    if {"fastapi", "flask"} & framework_set:
        items.extend(
            _extract_decorated_route_items(
                root_node=root_node,
                source_bytes=source_bytes,
                file_path=file_path,
                frameworks=framework_set,
            )
        )

    if "django" in framework_set:
        items.extend(
            _extract_django_items(source_bytes=source_bytes, file_path=file_path)
        )

    return items


def _extract_decorated_route_items(
    *,
    root_node: Any,
    source_bytes: bytes,
    file_path: Path,
    frameworks: set[str],
) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []

    for node in walk_tree(root_node):
        if node.type != "decorated_definition":
            continue

        definition = node.child_by_field_name("definition")
        if definition is None or definition.type not in {
            "function_definition",
            "async_function_definition",
        }:
            continue

        handler_name = field_text(definition, "name", source_bytes)
        if not handler_name:
            continue

        docstring = _extract_docstring(definition, source_bytes)
        for decorator in _decorator_texts(node, source_bytes):
            route = _parse_decorator_route(decorator, frameworks)
            if route is None:
                continue

            metadata = ApiRouteMeta(
                http_method=route.http_method,
                path=route.path,
                framework=route.framework,
                handler_name=handler_name,
                has_docstring=docstring is not None,
                docstring=docstring,
                response_model=route.response_model,
            )
            method = _display_method(route.http_method)
            items.append(
                DiscoveredItem(
                    kind=ItemKind.API_ROUTE,
                    name=f"{method} {route.path}",
                    file_path=file_path,
                    line_number=line_number(definition),
                    language=SupportedLanguage.PYTHON,
                    raw_text=docstring,
                    metadata=metadata.model_dump(),
                    confidence=0.9,
                )
            )

    return items


def _extract_django_items(
    *, source_bytes: bytes, file_path: Path
) -> list[DiscoveredItem]:
    try:
        source_text = source_bytes.decode("utf-8", errors="ignore")
        module = ast.parse(source_text)
    except SyntaxError:
        return []

    docstrings = _module_function_docstrings(module)
    items: list[DiscoveredItem] = []
    for call in _iter_urlpattern_calls(module):
        route = _parse_django_call(call)
        if route is None:
            continue
        handler_doc = docstrings.get(route.handler_name or "")
        metadata = ApiRouteMeta(
            http_method=route.http_method,
            path=route.path,
            framework=route.framework,
            handler_name=route.handler_name,
            has_docstring=handler_doc is not None,
            docstring=handler_doc,
        )
        items.append(
            DiscoveredItem(
                kind=ItemKind.API_ROUTE,
                name=f"GET {route.path}",
                file_path=file_path,
                line_number=call.lineno,
                language=SupportedLanguage.PYTHON,
                raw_text=handler_doc,
                metadata=metadata.model_dump(),
                confidence=0.9,
            )
        )
    return items


def _module_function_docstrings(module: ast.Module) -> dict[str, str]:
    docstrings: dict[str, str] = {}
    for node in module.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        docstring = ast.get_docstring(node)
        if docstring:
            docstrings[node.name] = docstring
    return docstrings


def _iter_urlpattern_calls(module: ast.Module) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in module.body:
        target_value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "urlpatterns"
            for target in node.targets
        ):
            target_value = node.value
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "urlpatterns"
        ):
            target_value = node.value
        if not isinstance(target_value, ast.List | ast.Tuple):
            continue
        for element in target_value.elts:
            if isinstance(element, ast.Call):
                calls.append(element)
    return calls


def _parse_django_call(call: ast.Call) -> _RouteMatch | None:
    func_name = _name_from_expr(call.func)
    if func_name not in {"path", "re_path"}:
        return None
    path = _first_string_arg(call)
    if not path:
        return None
    handler: str | None = None
    if len(call.args) >= 2:
        handler = _name_from_expr(call.args[1])
    return _RouteMatch(
        framework="django",
        path=path,
        http_method="GET",
        handler_name=handler,
    )


def _parse_decorator_route(
    decorator_text: str,
    frameworks: set[str],
) -> _RouteMatch | None:
    call = _parse_decorator_call(decorator_text)
    if call is None:
        return None

    if "fastapi" in frameworks:
        fastapi = _parse_fastapi_call(call)
        if fastapi is not None:
            return fastapi

    if "flask" in frameworks:
        flask = _parse_flask_call(call)
        if flask is not None:
            return flask

    return None


def _parse_fastapi_call(call: ast.Call) -> _RouteMatch | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    owner = _name_from_expr(call.func.value)
    method = call.func.attr.lower()
    if owner not in {"app", "router"} or method not in _FASTAPI_METHODS:
        return None
    path = _first_string_arg(call)
    if not path:
        return None
    return _RouteMatch(
        framework="fastapi",
        path=path,
        http_method=method.upper(),
        response_model=_keyword_as_source(call, "response_model"),
    )


def _parse_flask_call(call: ast.Call) -> _RouteMatch | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    if call.func.attr != "route":
        return None
    path = _first_string_arg(call)
    if not path:
        return None
    return _RouteMatch(
        framework="flask",
        path=path,
        http_method=_parse_flask_methods(call),
    )


def _parse_flask_methods(call: ast.Call) -> list[str]:
    raw_value = _keyword_value(call, "methods")
    if raw_value is None:
        return ["GET"]

    elements: list[str] = []
    if isinstance(raw_value, ast.Constant) and isinstance(raw_value.value, str):
        elements = [raw_value.value]
    elif isinstance(raw_value, ast.List | ast.Tuple | ast.Set):
        for element in raw_value.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                elements.append(element.value)

    methods: list[str] = []
    for method in elements:
        normalized = method.strip().upper()
        if normalized and normalized not in methods:
            methods.append(normalized)
    return methods or ["GET"]


def _parse_decorator_call(decorator_text: str) -> ast.Call | None:
    expression = decorator_text.strip()
    if expression.startswith("@"):
        expression = expression[1:]

    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None

    if not isinstance(parsed, ast.Expression) or not isinstance(parsed.body, ast.Call):
        return None
    return parsed.body


def _first_string_arg(call: ast.Call) -> str | None:
    if not call.args:
        return None
    first = call.args[0]
    if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
        return None
    value = first.value.strip()
    return value or None


def _keyword_value(call: ast.Call, keyword: str) -> ast.expr | None:
    for item in call.keywords:
        if item.arg == keyword:
            return item.value
    return None


def _keyword_as_source(call: ast.Call, keyword: str) -> str | None:
    value = _keyword_value(call, keyword)
    if value is None:
        return None
    try:
        rendered = ast.unparse(value).strip()
    except Exception:
        return None
    return rendered or None


def _name_from_expr(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _decorator_texts(node: Any, source_bytes: bytes) -> list[str]:
    decorators: list[str] = []
    for child in getattr(node, "named_children", ()):
        if child.type != "decorator":
            continue
        text = node_text(child, source_bytes).strip()
        if text:
            decorators.append(text)
    return decorators


def _extract_docstring(function_node: Any, source_bytes: bytes) -> str | None:
    body = function_node.child_by_field_name("body")
    if body is None:
        return None
    children = list(getattr(body, "named_children", ()))
    if not children or children[0].type != "expression_statement":
        return None
    for child in getattr(children[0], "named_children", ()):
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


def _display_method(http_method: str | list[str]) -> str:
    if isinstance(http_method, str):
        return http_method
    if not http_method:
        return "GET"
    return http_method[0]
