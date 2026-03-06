# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for TypeScript/JavaScript test-function discovery miner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import FileIndex
from specleft.discovery.miners.typescript.tests import TypeScriptTestMiner
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


def _statement_block(statements: list[_FakeNode], row: int) -> _FakeNode:
    return _FakeNode(
        type="statement_block",
        children=list(statements),
        named_children=list(statements),
        start_point=(row, 0),
        end_point=(row + 1, 0),
    )


def _arrow_function(body: _FakeNode, row: int) -> _FakeNode:
    return _FakeNode(
        type="arrow_function",
        children=[body],
        named_children=[body],
        fields={"body": body},
        start_point=(row, 0),
        end_point=(row + 1, 0),
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


def _typescript_test_tree() -> _FakeNode:
    it_call = _call_expression(
        _identifier("it", 3),
        [
            _string("'logs in valid user'", 3),
            _arrow_function(_statement_block([], 3), 3),
        ],
        3,
    )
    todo_call = _call_expression(
        _member_expression("it", "todo", 4),
        [_string("'pending test'", 4)],
        4,
    )
    test_call = _call_expression(
        _identifier("test", 5),
        [
            _string("'does thing'", 5),
            _arrow_function(_statement_block([], 5), 5),
        ],
        5,
    )
    helper_call = _call_expression(
        _identifier("expect", 6),
        [_string("'not a test call'", 6)],
        6,
    )

    block = _statement_block(
        [
            _expression_statement(it_call, 3),
            _expression_statement(todo_call, 4),
            _expression_statement(test_call, 5),
            _expression_statement(helper_call, 6),
        ],
        2,
    )
    describe_call = _call_expression(
        _identifier("describe", 2),
        [
            _string("'Auth'", 2),
            _arrow_function(block, 2),
        ],
        2,
    )

    root_statement = _expression_statement(describe_call, 2)
    return _FakeNode(
        type="program",
        children=[root_statement],
        named_children=[root_statement],
        start_point=(0, 0),
        end_point=(8, 0),
    )


def _javascript_test_tree() -> _FakeNode:
    call = _call_expression(
        _identifier("test", 1),
        [
            _string("'handles js path'", 1),
            _arrow_function(_statement_block([], 1), 1),
        ],
        1,
    )
    statement = _expression_statement(call, 1)
    return _FakeNode(
        type="program",
        children=[statement],
        named_children=[statement],
        start_point=(0, 0),
        end_point=(3, 0),
    )


def _single_test_tree(name: str, row: int = 1) -> _FakeNode:
    call = _call_expression(
        _identifier("test", row),
        [
            _string(f"'{name}'", row),
            _arrow_function(_statement_block([], row), row),
        ],
        row,
    )
    statement = _expression_statement(call, row)
    return _FakeNode(
        type="program",
        children=[statement],
        named_children=[statement],
        start_point=(0, 0),
        end_point=(row + 2, 0),
    )


def test_typescript_test_miner_extracts_describe_context_and_call_styles(
    tmp_path: Path,
) -> None:
    ts_file = tmp_path / "tests" / "auth.spec.ts"
    js_file = tmp_path / "tests" / "helpers.test.js"
    ignored = tmp_path / "src" / "helpers.ts"

    ts_file.parent.mkdir(parents=True)
    ignored.parent.mkdir(parents=True)

    ts_file.write_text("describe('Auth', () => { it('x', () => {}) })\n")
    js_file.write_text("test('js', () => {})\n")
    ignored.write_text("export const helper = 1\n")

    registry = _RegistryStub(
        {
            ts_file: (_typescript_test_tree(), SupportedLanguage.TYPESCRIPT),
            js_file: (_javascript_test_tree(), SupportedLanguage.JAVASCRIPT),
            ignored: (_javascript_test_tree(), SupportedLanguage.TYPESCRIPT),
        }
    )

    result = TypeScriptTestMiner().mine(
        _context(
            tmp_path,
            registry,
            frameworks={
                SupportedLanguage.TYPESCRIPT: ["jest"],
                SupportedLanguage.JAVASCRIPT: ["vitest"],
            },
        )
    )

    assert result.error is None
    assert result.error_kind is None
    assert registry.calls == [ts_file, js_file]
    assert len(result.items) == 4
    assert all(
        isinstance(item.typed_meta(), _TestFunctionMeta) for item in result.items
    )

    by_name = {item.name: item for item in result.items}
    assert set(by_name) == {
        "logs in valid user",
        "pending test",
        "does thing",
        "handles js path",
    }

    assert by_name["logs in valid user"].metadata["class_name"] == "Auth"
    assert by_name["pending test"].metadata["class_name"] == "Auth"
    assert by_name["pending test"].metadata["has_todo"] is True
    assert by_name["pending test"].metadata["call_style"] == "it"
    assert by_name["does thing"].metadata["call_style"] == "test"

    assert by_name["logs in valid user"].language == SupportedLanguage.TYPESCRIPT
    assert by_name["handles js path"].language == SupportedLanguage.JAVASCRIPT

    assert by_name["logs in valid user"].metadata["framework"] == "jest"
    assert by_name["handles js path"].metadata["framework"] == "vitest"

    assert by_name["logs in valid user"].confidence == 0.9
    assert by_name["pending test"].confidence == 0.9
    assert by_name["handles js path"].confidence == 0.7


def test_typescript_test_miner_reports_parse_failures_and_keeps_valid_items(
    tmp_path: Path,
) -> None:
    good_file = tmp_path / "tests" / "ok.test.ts"
    bad_file = tmp_path / "tests" / "bad.spec.js"

    good_file.parent.mkdir(parents=True)
    good_file.write_text("test('ok', () => {})\n")
    bad_file.write_text("test('broken'\n")

    registry = _RegistryStub(
        {
            good_file: (_single_test_tree("ok path"), SupportedLanguage.TYPESCRIPT),
            bad_file: None,
        }
    )

    result = TypeScriptTestMiner().mine(_context(tmp_path, registry))

    assert result.error_kind == MinerErrorKind.PARSE_ERROR
    assert result.error is not None
    assert "tests/bad.spec.js" in result.error
    assert len(result.items) == 1
    assert result.items[0].name == "ok path"
    assert result.items[0].metadata["framework"] == "unknown"
    assert result.items[0].metadata["call_style"] == "test"
    assert result.items[0].confidence == 0.7
