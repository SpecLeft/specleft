# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for discovery docstring/JSDoc miner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import FileIndex
from specleft.discovery.miners.shared.docstrings import DocstringMiner
from specleft.discovery.models import DocstringMeta, SupportedLanguage


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


def _string_expr(value: str, row: int) -> _FakeNode:
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


def _identifier(value: str, row: int) -> _FakeNode:
    return _FakeNode(
        type="identifier",
        text_value=value,
        start_point=(row, 0),
        end_point=(row, len(value)),
    )


def _python_function(name: str, docstring: str, start_row: int) -> _FakeNode:
    name_node = _identifier(name, start_row)
    body_doc = _string_expr(docstring, start_row + 1)
    body = _FakeNode(
        type="block",
        children=[body_doc],
        named_children=[body_doc],
        start_point=(start_row + 1, 0),
        end_point=(start_row + 1, 0),
    )
    return _FakeNode(
        type="function_definition",
        children=[name_node, body],
        named_children=[name_node, body],
        fields={"name": name_node, "body": body},
        start_point=(start_row, 0),
        end_point=(start_row + 2, 0),
    )


def _python_class(name: str, docstring: str, start_row: int) -> _FakeNode:
    name_node = _identifier(name, start_row)
    body_doc = _string_expr(docstring, start_row + 1)
    body = _FakeNode(
        type="block",
        children=[body_doc],
        named_children=[body_doc],
        start_point=(start_row + 1, 0),
        end_point=(start_row + 1, 0),
    )
    return _FakeNode(
        type="class_definition",
        children=[name_node, body],
        named_children=[name_node, body],
        fields={"name": name_node, "body": body},
        start_point=(start_row, 0),
        end_point=(start_row + 2, 0),
    )


def _python_module_tree() -> _FakeNode:
    module_doc = _string_expr('"""Auth module docs."""', 0)
    class_node = _python_class("AuthService", '"""Class docs."""', 2)
    init_fn = _python_function("__init__", '"""Init."""', 5)
    create_user_fn = _python_function(
        "create_user",
        '"""Create a new user with the given credentials."""',
        8,
    )
    class_body = class_node.child_by_field_name("body")
    assert class_body is not None
    class_body.children.extend([init_fn, create_user_fn])
    class_body.named_children.extend([init_fn, create_user_fn])

    top_function = _python_function("validate_credentials", '"""Validate login."""', 12)
    return _FakeNode(
        type="module",
        children=[module_doc, class_node, top_function],
        named_children=[module_doc, class_node, top_function],
        start_point=(0, 0),
        end_point=(15, 0),
    )


def _jsdoc_comment(text: str, row: int) -> _FakeNode:
    return _FakeNode(
        type="comment",
        text_value=text,
        start_point=(row, 0),
        end_point=(row, len(text)),
    )


def _typescript_function(name: str, row: int) -> _FakeNode:
    name_node = _identifier(name, row)
    return _FakeNode(
        type="function_declaration",
        children=[name_node],
        named_children=[name_node],
        fields={"name": name_node},
        start_point=(row, 0),
        end_point=(row + 1, 0),
    )


def _javascript_tree(function_name: str) -> _FakeNode:
    comment = _jsdoc_comment("/** Creates a new user */", 0)
    function = _typescript_function(function_name, 1)
    return _FakeNode(
        type="program",
        children=[comment, function],
        named_children=[comment, function],
        start_point=(0, 0),
        end_point=(2, 0),
    )


def _context(
    root: Path,
    registry: _RegistryStub,
    source_dirs: tuple[str, ...] = ("src",),
) -> MinerContext:
    return MinerContext(
        root=root,
        registry=registry,  # type: ignore[arg-type]
        file_index=FileIndex(root),
        frameworks={},
        config=DiscoveryConfig(source_dirs=source_dirs),
    )


def test_python_docstrings_include_module_class_and_functions(tmp_path: Path) -> None:
    source_file = tmp_path / "src" / "auth.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        '"""Auth module docs."""\nclass AuthService:\n    """Class docs."""\n',
        encoding="utf-8",
    )
    excluded_test_file = tmp_path / "src" / "test_auth.py"
    excluded_test_file.write_text('"""should be skipped"""', encoding="utf-8")

    registry = _RegistryStub(
        {
            source_file: (_python_module_tree(), SupportedLanguage.PYTHON),
            excluded_test_file: (_python_module_tree(), SupportedLanguage.PYTHON),
        }
    )
    miner = DocstringMiner()

    result = miner.mine(_context(tmp_path, registry))

    assert result.error is None
    assert result.error_kind is None
    assert all(item.language == SupportedLanguage.PYTHON for item in result.items)
    assert "module:auth" in {item.name for item in result.items}
    assert "class:AuthService" in {item.name for item in result.items}
    assert "function:create_user" in {item.name for item in result.items}
    assert "function:validate_credentials" in {item.name for item in result.items}
    assert "function:__init__" not in {item.name for item in result.items}
    assert all(isinstance(item.typed_meta(), DocstringMeta) for item in result.items)

    module_item = next(item for item in result.items if item.name == "module:auth")
    assert module_item.metadata["target_kind"] == "module"
    assert module_item.language == SupportedLanguage.PYTHON
    assert registry.calls == [source_file]


def test_jsdoc_uses_language_per_extension(tmp_path: Path) -> None:
    ts_file = tmp_path / "src" / "auth.ts"
    js_file = tmp_path / "src" / "auth.js"
    ts_file.parent.mkdir(parents=True)
    ts_file.write_text("/** Creates a new user */\nexport function createUser() {}\n")
    js_file.write_text("/** Creates a helper */\nfunction createHelper() {}\n")

    registry = _RegistryStub(
        {
            ts_file: (_javascript_tree("createUser"), SupportedLanguage.TYPESCRIPT),
            js_file: (_javascript_tree("createHelper"), SupportedLanguage.JAVASCRIPT),
        }
    )

    result = DocstringMiner().mine(_context(tmp_path, registry))

    by_name = {item.name: item for item in result.items}
    assert by_name["function:createUser"].language == SupportedLanguage.TYPESCRIPT
    assert by_name["function:createHelper"].language == SupportedLanguage.JAVASCRIPT
    assert by_name["function:createUser"].metadata["text"] == "Creates a new user"


def test_source_dirs_scope_and_test_patterns_are_respected(tmp_path: Path) -> None:
    inside_source = tmp_path / "app" / "module.py"
    outside_source = tmp_path / "src" / "outside.py"
    ts_test = tmp_path / "app" / "auth.test.ts"
    inside_source.parent.mkdir(parents=True)
    outside_source.parent.mkdir(parents=True, exist_ok=True)

    inside_source.write_text('"""inside"""')
    outside_source.write_text('"""outside"""')
    ts_test.write_text("/** should skip */\nfunction x() {}\n")

    registry = _RegistryStub(
        {
            inside_source: (_python_module_tree(), SupportedLanguage.PYTHON),
            outside_source: (_python_module_tree(), SupportedLanguage.PYTHON),
            ts_test: (_javascript_tree("x"), SupportedLanguage.TYPESCRIPT),
        }
    )

    result = DocstringMiner().mine(_context(tmp_path, registry, source_dirs=("app",)))

    assert all(item.file_path == Path("app/module.py") for item in result.items)
    assert registry.calls == [inside_source]
