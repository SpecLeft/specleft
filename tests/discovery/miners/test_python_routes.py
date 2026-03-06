# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for Python API-route discovery miner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import FileIndex
from specleft.discovery.miners.python.routes import PythonRouteMiner
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


def _docstring_expr(value: str, row: int) -> _FakeNode:
    string_node = _FakeNode(
        type="string",
        text_value=value,
        start_point=(row, 0),
        end_point=(row, len(value)),
    )
    return _FakeNode(
        type="expression_statement",
        children=[string_node],
        named_children=[string_node],
        start_point=(row, 0),
        end_point=(row, len(value)),
    )


def _python_function(name: str, row: int, docstring: str | None = None) -> _FakeNode:
    name_node = _identifier(name, row)
    body_children: list[_FakeNode] = []
    if docstring is not None:
        body_children.append(_docstring_expr(docstring, row + 1))
    body = _FakeNode(
        type="block",
        children=list(body_children),
        named_children=list(body_children),
        start_point=(row + 1, 0),
        end_point=(row + 2, 0),
    )
    return _FakeNode(
        type="function_definition",
        children=[name_node, body],
        named_children=[name_node, body],
        fields={"name": name_node, "body": body},
        start_point=(row, 0),
        end_point=(row + 3, 0),
    )


def _decorated_function(
    *,
    name: str,
    row: int,
    decorators: list[str],
    docstring: str | None = None,
) -> _FakeNode:
    decorator_nodes: list[_FakeNode] = []
    for index, decorator in enumerate(decorators):
        decorator_nodes.append(
            _FakeNode(
                type="decorator",
                text_value=decorator,
                start_point=(row + index, 0),
                end_point=(row + index, len(decorator)),
            )
        )

    function_node = _python_function(
        name=name,
        row=row + len(decorator_nodes),
        docstring=docstring,
    )
    children = [*decorator_nodes, function_node]
    return _FakeNode(
        type="decorated_definition",
        children=children,
        named_children=children,
        fields={"definition": function_node},
        start_point=(row, 0),
        end_point=function_node.end_point,
    )


def _module(children: list[_FakeNode]) -> _FakeNode:
    return _FakeNode(
        type="module",
        children=list(children),
        named_children=list(children),
        start_point=(0, 0),
        end_point=(max((child.end_point[0] for child in children), default=0) + 1, 0),
    )


def _fastapi_route_tree() -> _FakeNode:
    return _module(
        [
            _decorated_function(
                name="get_user",
                row=0,
                decorators=['@app.get("/users/{id}", response_model=UserResponse)'],
                docstring='"""Retrieve a user by ID"""',
            ),
            _decorated_function(
                name="create_user",
                row=6,
                decorators=['@app.post("/users")'],
            ),
            _decorated_function(
                name="update_user",
                row=12,
                decorators=['@router.patch("/users/{id}")'],
            ),
        ]
    )


def _flask_route_tree() -> _FakeNode:
    return _module(
        [
            _decorated_function(
                name="items",
                row=0,
                decorators=['@bp.route("/items", methods=["GET", "POST"])'],
            ),
            _decorated_function(
                name="health",
                row=6,
                decorators=['@app.route("/health")'],
            ),
        ]
    )


def test_python_route_miner_extracts_fastapi_routes_with_response_model(
    tmp_path: Path,
) -> None:
    fixture = _fixture_dir() / "sample_api.py"
    api_file = tmp_path / "src" / "sample_api.py"
    api_file.parent.mkdir(parents=True)
    api_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    registry = _RegistryStub(
        {api_file: (_fastapi_route_tree(), SupportedLanguage.PYTHON)}
    )

    result = PythonRouteMiner().mine(
        _context(tmp_path, registry, frameworks={SupportedLanguage.PYTHON: ["fastapi"]})
    )

    assert result.error is None
    assert result.error_kind is None
    assert registry.calls == [api_file]
    assert len(result.items) == 3
    assert all(item.language == SupportedLanguage.PYTHON for item in result.items)
    assert all(isinstance(item.typed_meta(), _ApiRouteMeta) for item in result.items)

    by_name = {item.name: item for item in result.items}
    assert set(by_name) == {"GET /users/{id}", "POST /users", "PATCH /users/{id}"}
    assert by_name["GET /users/{id}"].metadata["framework"] == "fastapi"
    assert by_name["GET /users/{id}"].metadata["response_model"] == "UserResponse"
    assert by_name["GET /users/{id}"].metadata["has_docstring"] is True
    assert by_name["GET /users/{id}"].metadata["docstring"] == "Retrieve a user by ID"


def test_python_route_miner_extracts_flask_routes_and_default_methods(
    tmp_path: Path,
) -> None:
    fixture = _fixture_dir() / "sample_api.py"
    api_file = tmp_path / "src" / "sample_api.py"
    api_file.parent.mkdir(parents=True)
    api_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    registry = _RegistryStub(
        {api_file: (_flask_route_tree(), SupportedLanguage.PYTHON)}
    )

    result = PythonRouteMiner().mine(
        _context(tmp_path, registry, frameworks={SupportedLanguage.PYTHON: ["flask"]})
    )

    assert result.error is None
    assert result.error_kind is None
    assert len(result.items) == 2

    by_path = {item.metadata["path"]: item for item in result.items}
    assert by_path["/items"].metadata["http_method"] == ["GET", "POST"]
    assert by_path["/items"].metadata["framework"] == "flask"
    assert by_path["/health"].metadata["http_method"] == ["GET"]


def test_python_route_miner_extracts_django_path_and_re_path(tmp_path: Path) -> None:
    api_file = tmp_path / "src" / "urls.py"
    api_file.parent.mkdir(parents=True)
    api_file.write_text(
        "\n".join(
            [
                "from django.urls import path, re_path",
                "",
                "def user_detail(request, user_id: int):",
                '    """Show one user."""',
                "    return None",
                "",
                "def legacy_view(request, slug: str):",
                "    return None",
                "",
                "urlpatterns = [",
                '    path("users/<int:user_id>/", user_detail, name="user-detail"),',
                '    re_path(r"^legacy/(?P<slug>[-\\\\w]+)/$", legacy_view),',
                "]",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry = _RegistryStub({api_file: (_module([]), SupportedLanguage.PYTHON)})

    result = PythonRouteMiner().mine(
        _context(tmp_path, registry, frameworks={SupportedLanguage.PYTHON: ["django"]})
    )

    assert result.error is None
    assert result.error_kind is None
    assert len(result.items) == 2
    assert all(item.metadata["framework"] == "django" for item in result.items)

    by_path = {item.metadata["path"]: item for item in result.items}
    assert by_path["users/<int:user_id>/"].name == "GET users/<int:user_id>/"
    assert by_path["users/<int:user_id>/"].metadata["handler_name"] == "user_detail"
    assert by_path["users/<int:user_id>/"].metadata["has_docstring"] is True
    legacy_item = next(
        item for item in result.items if item.metadata["path"].startswith("^legacy/")
    )
    assert legacy_item.name.startswith("GET ^legacy/")


def test_python_route_miner_reports_parse_failures_and_keeps_valid_items(
    tmp_path: Path,
) -> None:
    fixture = _fixture_dir() / "sample_api.py"
    good_file = tmp_path / "src" / "good.py"
    bad_file = tmp_path / "src" / "bad.py"
    good_file.parent.mkdir(parents=True)
    good_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    bad_file.write_text("def broken(\n", encoding="utf-8")

    registry = _RegistryStub(
        {
            good_file: (_fastapi_route_tree(), SupportedLanguage.PYTHON),
            bad_file: None,
        }
    )

    result = PythonRouteMiner().mine(
        _context(tmp_path, registry, frameworks={SupportedLanguage.PYTHON: ["fastapi"]})
    )

    assert result.error_kind == MinerErrorKind.PARSE_ERROR
    assert result.error is not None
    assert "src/bad.py" in result.error
    assert len(result.items) == 3


def test_python_route_miner_skips_when_no_supported_framework(tmp_path: Path) -> None:
    fixture = _fixture_dir() / "sample_api.py"
    api_file = tmp_path / "src" / "sample_api.py"
    api_file.parent.mkdir(parents=True)
    api_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    registry = _RegistryStub(
        {api_file: (_fastapi_route_tree(), SupportedLanguage.PYTHON)}
    )
    result = PythonRouteMiner().mine(
        _context(tmp_path, registry, frameworks={SupportedLanguage.PYTHON: ["pytest"]})
    )

    assert result.error is None
    assert result.error_kind is None
    assert result.items == []
    assert registry.calls == []
