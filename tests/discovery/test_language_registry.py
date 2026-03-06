# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for language registry and parser abstraction."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specleft.discovery.language_registry import LanguageRegistry, SUPPORTED_EXTENSIONS
from specleft.discovery.models import SupportedLanguage


def test_supported_extensions_map() -> None:
    assert SUPPORTED_EXTENSIONS[".py"] == SupportedLanguage.PYTHON
    assert SUPPORTED_EXTENSIONS[".ts"] == SupportedLanguage.TYPESCRIPT
    assert SUPPORTED_EXTENSIONS[".tsx"] == SupportedLanguage.TYPESCRIPT
    assert SUPPORTED_EXTENSIONS[".js"] == SupportedLanguage.JAVASCRIPT


def test_detect_language_matches_supported_extensions() -> None:
    registry = LanguageRegistry()
    assert registry.detect_language(Path("module.py")) == SupportedLanguage.PYTHON
    assert registry.detect_language(Path("main.ts")) == SupportedLanguage.TYPESCRIPT
    assert registry.detect_language(Path("client.mjs")) == SupportedLanguage.JAVASCRIPT


def test_detect_language_skips_unsupported_extension() -> None:
    assert LanguageRegistry().detect_language(Path("notes.txt")) is None
    assert LanguageRegistry().detect_language(Path("script.rb")) is None


@pytest.mark.parametrize(
    ("filename", "expected_language"),
    [
        ("sample.py", SupportedLanguage.PYTHON),
        ("sample.ts", SupportedLanguage.TYPESCRIPT),
    ],
)
def test_parse_uses_parse_source_and_returns_detected_language(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    filename: str,
    expected_language: SupportedLanguage,
) -> None:
    path = tmp_path / filename
    path.write_text("x = 1")

    registry = LanguageRegistry()
    monkeypatch.setattr(
        registry,
        "parse_source",
        lambda _source, _language: "fake-root",
    )

    result = registry.parse(path)
    assert result is not None
    root_node, language = result
    assert root_node == "fake-root"
    assert language == expected_language


def test_parse_returns_none_for_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("x")

    assert LanguageRegistry().parse(path) is None


def test_parse_returns_none_on_parse_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "sample.ts"
    path.write_text("const x = 1;")

    registry = LanguageRegistry()

    def broken(source: bytes, _language: SupportedLanguage) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(registry, "parse_source", broken)
    assert registry.parse(path) is None


def test_parse_returns_none_on_corrupt_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "corrupt.py"
    path.write_bytes(b"\x80\x81\x82")

    registry = LanguageRegistry()

    class FakeParser:
        def parse(self, _source: bytes) -> SimpleNamespace:
            return SimpleNamespace(root_node=SimpleNamespace(has_error=True))

    monkeypatch.setattr(registry, "_parser_for", lambda _language: FakeParser())
    assert registry.parse(path) is None


def test_parser_and_language_are_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = LanguageRegistry()
    calls: dict[str, int] = {"language": 0}

    def fake_language_for(self: LanguageRegistry, language: SupportedLanguage) -> str:
        calls["language"] += 1
        return f"fake-{language.value}"

    class FakeParser:
        def __init__(self) -> None:
            self.language: str | None = None

        def set_language(self, language: str) -> None:
            self.language = language

        def parse(self, source: bytes) -> SimpleNamespace:
            return SimpleNamespace(root_node=f"root({source!s})")

    parser = FakeParser()

    def fake_parser_class() -> FakeParser:
        return parser

    monkeypatch.setattr(LanguageRegistry, "_language_for", fake_language_for)

    fake_tree_sitter = SimpleNamespace(Parser=fake_parser_class)
    monkeypatch.setitem(sys.modules, "tree_sitter", fake_tree_sitter)

    first = registry._parser_for(SupportedLanguage.PYTHON)
    second = registry._parser_for(SupportedLanguage.PYTHON)

    assert first is second
    assert first is parser
    assert calls["language"] == 1


def test_javascript_uses_javascript_grammar_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = LanguageRegistry()
    calls: dict[str, int] = {"ts": 0, "js": 0}

    def fake_ts_loader() -> str:
        calls["ts"] += 1
        return "ts-language"

    def fake_js_loader() -> str:
        calls["js"] += 1
        return "js-language"

    fake_typescript_module = SimpleNamespace(
        language_typescript=fake_ts_loader,
        language_javascript=fake_js_loader,
    )
    monkeypatch.setitem(sys.modules, "tree_sitter_typescript", fake_typescript_module)

    js_language = registry._language_for(SupportedLanguage.JAVASCRIPT)
    ts_language = registry._language_for(SupportedLanguage.TYPESCRIPT)

    assert js_language == "js-language"
    assert ts_language == "ts-language"
    assert calls["js"] == 1
    assert calls["ts"] == 1
