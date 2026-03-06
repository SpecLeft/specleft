# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for TypeScript/JavaScript API-route discovery miner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import FileIndex
from specleft.discovery.miners.typescript.routes import TypeScriptRouteMiner
from specleft.discovery.models import (
    ApiRouteMeta as _ApiRouteMeta,
    MinerErrorKind,
    SupportedLanguage,
)


@dataclass
class _FakeNode:
    type: str
    text_value: str = ""
    children: list[_FakeNode] = field(default_factory=list)
    named_children: list[_FakeNode] = field(default_factory=list)
    fields: dict[str, _FakeNode] = field(default_factory=dict)
    start_point: tuple[int, int] = (0, 0)
    end_point: tuple[int, int] = (0, 0)

    @property
    def text(self) -> bytes:
        return self.text_value.encode("utf-8")

    def child_by_field_name(self, name: str) -> _FakeNode | None:
        return self.fields.get(name)


class _RegistryStub:
    def __init__(
        self, mapping: dict[Path, tuple[Any, SupportedLanguage] | None]
    ) -> None:
        self._mapping = mapping
        self.calls: list[Path] = []

    def parse(self, file_path: Path) -> tuple[Any, SupportedLanguage] | None:
        self.calls.append(file_path)
        return self._mapping.get(file_path)


def _context(
    root: Path,
    registry: _RegistryStub,
    *,
    frameworks: dict[SupportedLanguage, list[str]] | None = None,
) -> MinerContext:
    return MinerContext(
        root=root,
        registry=registry,  # type: ignore[arg-type]
        file_index=FileIndex(root),
        frameworks=frameworks or {},
        config=DiscoveryConfig.default(),
    )


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "discovery"


def _identifier(value: str, row: int) -> _FakeNode:
    return _FakeNode(
        type="identifier",
        text_value=value,
        start_point=(row, 0),
        end_point=(row, len(value)),
    )


def _property_identifier(value: str, row: int) -> _FakeNode:
    return _FakeNode(
        type="property_identifier",
        text_value=value,
        start_point=(row, 0),
        end_point=(row, len(value)),
    )


def _string(value: str, row: int) -> _FakeNode:
    return _FakeNode(
        type="string",
        text_value=value,
        start_point=(row, 0),
        end_point=(row, len(value)),
    )


def _member_expression(object_name: str, property_name: str, row: int) -> _FakeNode:
    object_node = _identifier(object_name, row)
    property_node = _property_identifier(property_name, row)
    return _FakeNode(
        type="member_expression",
        children=[object_node, property_node],
        named_children=[object_node, property_node],
        fields={"object": object_node, "property": property_node},
        start_point=(row, 0),
        end_point=(row, len(object_name) + len(property_name) + 1),
    )


def _call_expression(callee: _FakeNode, args: list[_FakeNode], row: int) -> _FakeNode:
    arguments_node = _FakeNode(
        type="arguments",
        children=list(args),
        named_children=list(args),
        start_point=(row, 0),
        end_point=(row, 0),
    )
    return _FakeNode(
        type="call_expression",
        children=[callee, arguments_node],
        named_children=[callee, arguments_node],
        fields={"function": callee, "arguments": arguments_node},
        start_point=(row, 0),
        end_point=(row + 1, 0),
    )


def _expression_statement(expression: _FakeNode, row: int) -> _FakeNode:
    return _FakeNode(
        type="expression_statement",
        children=[expression],
        named_children=[expression],
        start_point=(row, 0),
        end_point=(row + 1, 0),
    )


def _route_call(
    *,
    target: str,
    method: str,
    path: str,
    handler: str,
    row: int,
) -> _FakeNode:
    return _call_expression(
        _member_expression(target, method, row),
        [_string(f"'{path}'", row), _identifier(handler, row)],
        row,
    )


def _module(statements: list[_FakeNode]) -> _FakeNode:
    return _FakeNode(
        type="program",
        children=list(statements),
        named_children=list(statements),
        start_point=(0, 0),
        end_point=(max((child.end_point[0] for child in statements), default=0) + 1, 0),
    )


def _express_tree(route_calls: list[_FakeNode]) -> _FakeNode:
    statements = [
        _expression_statement(call, row=index + 1)
        for index, call in enumerate(route_calls)
    ]
    return _module(statements)


def test_typescript_route_miner_extracts_express_routes_and_languages(
    tmp_path: Path,
) -> None:
    fixture = _fixture_dir() / "sample_api.ts"
    ts_file = tmp_path / "src" / "routes.ts"
    js_file = tmp_path / "src" / "routes.js"
    ts_file.parent.mkdir(parents=True)

    ts_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    js_file.write_text("app.delete('/users/{id}', deleteUser)\n", encoding="utf-8")

    registry = _RegistryStub(
        {
            ts_file: (
                _express_tree(
                    [
                        _route_call(
                            target="router",
                            method="get",
                            path="/health",
                            handler="healthHandler",
                            row=1,
                        )
                    ]
                ),
                SupportedLanguage.TYPESCRIPT,
            ),
            js_file: (
                _express_tree(
                    [
                        _route_call(
                            target="app",
                            method="delete",
                            path="/users/{id}",
                            handler="deleteUser",
                            row=1,
                        )
                    ]
                ),
                SupportedLanguage.JAVASCRIPT,
            ),
        }
    )

    result = TypeScriptRouteMiner().mine(
        _context(
            tmp_path,
            registry,
            frameworks={SupportedLanguage.TYPESCRIPT: ["express"]},
        )
    )

    assert result.error is None
    assert result.error_kind is None
    assert len(result.items) == 2
    assert all(isinstance(item.typed_meta(), _ApiRouteMeta) for item in result.items)

    by_name = {item.name: item for item in result.items}
    assert set(by_name) == {"GET /health", "DELETE /users/{id}"}
    assert by_name["GET /health"].metadata["framework"] == "express"
    assert by_name["GET /health"].metadata["handler_name"] == "healthHandler"
    assert by_name["GET /health"].language == SupportedLanguage.TYPESCRIPT
    assert by_name["DELETE /users/{id}"].language == SupportedLanguage.JAVASCRIPT


def test_typescript_route_miner_extracts_nextjs_app_router_exports(
    tmp_path: Path,
) -> None:
    fixture = _fixture_dir() / "app" / "api" / "users" / "[id]" / "route.ts"
    route_file = tmp_path / "app" / "api" / "users" / "[id]" / "route.ts"
    route_file.parent.mkdir(parents=True)
    route_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    registry = _RegistryStub(
        {
            route_file: (_module([]), SupportedLanguage.TYPESCRIPT),
        }
    )

    result = TypeScriptRouteMiner().mine(
        _context(
            tmp_path,
            registry,
            frameworks={SupportedLanguage.TYPESCRIPT: ["nextjs"]},
        )
    )

    assert result.error is None
    assert result.error_kind is None
    assert registry.calls == [route_file]
    assert len(result.items) == 2
    assert all(item.metadata["framework"] == "nextjs" for item in result.items)
    assert all(item.metadata["is_file_based_route"] is True for item in result.items)
    assert {item.name for item in result.items} == {
        "DELETE /api/users/{id}",
        "POST /api/users/{id}",
    }
    assert all(item.metadata["path"] == "/api/users/{id}" for item in result.items)


def test_typescript_route_miner_reports_parse_failures_and_keeps_valid_items(
    tmp_path: Path,
) -> None:
    good_file = tmp_path / "src" / "routes.ts"
    bad_file = tmp_path / "src" / "broken.js"
    good_file.parent.mkdir(parents=True)

    good_file.write_text("app.get('/ok', okHandler)\n", encoding="utf-8")
    bad_file.write_text("app.get('/broken'\n", encoding="utf-8")

    registry = _RegistryStub(
        {
            good_file: (
                _express_tree(
                    [
                        _route_call(
                            target="app",
                            method="get",
                            path="/ok",
                            handler="okHandler",
                            row=1,
                        )
                    ]
                ),
                SupportedLanguage.TYPESCRIPT,
            ),
            bad_file: None,
        }
    )

    result = TypeScriptRouteMiner().mine(
        _context(
            tmp_path,
            registry,
            frameworks={SupportedLanguage.TYPESCRIPT: ["express"]},
        )
    )

    assert result.error_kind == MinerErrorKind.PARSE_ERROR
    assert result.error is not None
    assert "src/broken.js" in result.error
    assert len(result.items) == 1
    assert result.items[0].name == "GET /ok"


def test_typescript_route_miner_skips_when_framework_is_not_supported(
    tmp_path: Path,
) -> None:
    ts_file = tmp_path / "src" / "routes.ts"
    ts_file.parent.mkdir(parents=True)
    ts_file.write_text("router.get('/health', healthHandler)\n", encoding="utf-8")

    registry = _RegistryStub(
        {
            ts_file: (_module([]), SupportedLanguage.TYPESCRIPT),
        }
    )
    result = TypeScriptRouteMiner().mine(
        _context(
            tmp_path,
            registry,
            frameworks={SupportedLanguage.TYPESCRIPT: ["jest"]},
        )
    )

    assert result.error is None
    assert result.error_kind is None
    assert result.items == []
    assert registry.calls == []
