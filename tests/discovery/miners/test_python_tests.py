# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for Python test-function discovery miner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import FileIndex
from specleft.discovery.miners.python.tests import PythonTestMiner
from specleft.discovery.models import (
    MinerErrorKind,
    SupportedLanguage,
    TestFunctionMeta as _TestFunctionMeta,
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


def _python_class(name: str, row: int, methods: list[_FakeNode]) -> _FakeNode:
    name_node = _identifier(name, row)
    body = _FakeNode(
        type="block",
        children=list(methods),
        named_children=list(methods),
        start_point=(row + 1, 0),
        end_point=(row + 2, 0),
    )
    return _FakeNode(
        type="class_definition",
        children=[name_node, body],
        named_children=[name_node, body],
        fields={"name": name_node, "body": body},
        start_point=(row, 0),
        end_point=(row + 3, 0),
    )


def _python_test_tree() -> _FakeNode:
    plain = _python_function("test_add", row=0)
    parametrized = _decorated_function(
        name="test_parametrized",
        row=4,
        decorators=['@pytest.mark.parametrize("value", [1, 2])'],
        docstring='"""Parametrized case."""',
    )
    testcase = _python_class(
        "TestMath",
        row=10,
        methods=[
            _python_function("test_subtract", row=11),
            _python_function("helper", row=15),
        ],
    )
    helper = _python_function("helper_function", row=20)

    children = [plain, parametrized, testcase, helper]
    return _FakeNode(
        type="module",
        children=children,
        named_children=children,
        start_point=(0, 0),
        end_point=(24, 0),
    )


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


def test_python_test_miner_extracts_plain_parametrized_and_testcase(
    tmp_path: Path,
) -> None:
    fixture_file = _fixture_dir() / "sample_tests.py"
    test_file = tmp_path / "tests" / "test_sample_tests.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(fixture_file.read_text(encoding="utf-8"), encoding="utf-8")
    non_test_file = tmp_path / "src" / "sample_tests.py"
    non_test_file.parent.mkdir(parents=True)
    non_test_file.write_text("def helper():\n    return 1\n", encoding="utf-8")

    registry = _RegistryStub(
        {
            test_file: (_python_test_tree(), SupportedLanguage.PYTHON),
            non_test_file: (_python_test_tree(), SupportedLanguage.PYTHON),
        }
    )

    result = PythonTestMiner().mine(
        _context(tmp_path, registry, frameworks={SupportedLanguage.PYTHON: ["pytest"]})
    )

    assert result.error is None
    assert result.error_kind is None
    assert len(result.items) == 3
    assert registry.calls == [test_file]
    assert all(item.language == SupportedLanguage.PYTHON for item in result.items)
    assert all(
        isinstance(item.typed_meta(), _TestFunctionMeta) for item in result.items
    )

    by_name = {item.name: item for item in result.items}
    assert set(by_name) == {"test_add", "test_parametrized", "test_subtract"}
    assert by_name["test_add"].metadata["class_name"] is None
    assert by_name["test_subtract"].metadata["class_name"] == "TestMath"
    assert by_name["test_parametrized"].metadata["is_parametrized"] is True
    assert by_name["test_parametrized"].metadata["decorators"] == [
        "pytest.mark.parametrize"
    ]
    assert by_name["test_parametrized"].metadata["has_docstring"] is True
    assert by_name["test_add"].metadata["framework"] == "pytest"
    assert all(item.confidence == 0.9 for item in result.items)


def test_python_test_miner_reports_parse_errors_and_keeps_items(
    tmp_path: Path,
) -> None:
    fixture_file = _fixture_dir() / "sample_tests.py"
    good_file = tmp_path / "tests" / "test_good.py"
    bad_file = tmp_path / "tests" / "test_bad.py"
    good_file.parent.mkdir(parents=True)
    good_file.write_text(fixture_file.read_text(encoding="utf-8"), encoding="utf-8")
    bad_file.write_text("def broken(\n", encoding="utf-8")

    registry = _RegistryStub(
        {
            good_file: (_python_test_tree(), SupportedLanguage.PYTHON),
            bad_file: None,
        }
    )

    result = PythonTestMiner().mine(_context(tmp_path, registry))

    assert result.error_kind == MinerErrorKind.PARSE_ERROR
    assert result.error is not None
    assert "tests/test_bad.py" in result.error
    assert len(result.items) == 3
    assert all(item.metadata["framework"] == "unknown" for item in result.items)
    assert all(item.confidence == 0.7 for item in result.items)
