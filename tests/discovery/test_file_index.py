# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for discovery file index abstraction."""

from __future__ import annotations

from pathlib import Path

from specleft.discovery.file_index import DEFAULT_EXCLUDE_DIRS, FileIndex
from specleft.discovery.models import SupportedLanguage


def _seed_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text("print('ok')")
    (root / "src" / "helpers.ts").write_text("const a = 1;")

    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_auth.py").write_text("def test_ok():\n    assert True\n")
    (tests_dir / "test_cache_service.py").write_text(
        "def test_cache():\n    assert True\n"
    )

    (root / "notes.md").write_text("just notes")

    (root / ".venv").mkdir()
    (root / ".venv" / "tmp.py").write_text("print('skip')")

    (root / "node_modules").mkdir()
    (root / "node_modules" / "a.js").write_text("console.log(1)")


def test_file_index_walk_counts_and_filters(tmp_path: Path) -> None:
    _seed_tree(tmp_path)
    index = FileIndex(tmp_path)

    assert index.root == tmp_path
    assert index.total_files == 5
    assert {path.as_posix() for path in index._files} == {
        "src/main.py",
        "src/helpers.ts",
        "tests/test_auth.py",
        "tests/test_cache_service.py",
        "notes.md",
    }


def test_file_index_by_language_only_includes_supported_languages(
    tmp_path: Path,
) -> None:
    _seed_tree(tmp_path)
    index = FileIndex(tmp_path)

    assert index.files_by_language(SupportedLanguage.PYTHON) == [
        Path("src/main.py"),
        Path("tests/test_auth.py"),
        Path("tests/test_cache_service.py"),
    ]
    assert index.files_by_language(SupportedLanguage.TYPESCRIPT) == [
        Path("src/helpers.ts")
    ]
    assert index.files_by_language(SupportedLanguage.JAVASCRIPT) == []


def test_files_matching_respects_patterns(tmp_path: Path) -> None:
    _seed_tree(tmp_path)
    index = FileIndex(tmp_path)

    matches = index.files_matching("test_*.py")
    assert [path.name for path in matches] == [
        "test_auth.py",
        "test_cache_service.py",
    ]


def test_files_under_returns_subset_of_root(tmp_path: Path) -> None:
    _seed_tree(tmp_path)
    index = FileIndex(tmp_path)

    assert index.files_under("src") == [
        Path("src/helpers.ts"),
        Path("src/main.py"),
    ]
    assert index.files_under("tests") == [
        Path("tests/test_auth.py"),
        Path("tests/test_cache_service.py"),
    ]


def test_exclude_dirs_are_skipped_by_default() -> None:
    assert ".venv" in DEFAULT_EXCLUDE_DIRS
    assert "node_modules" in DEFAULT_EXCLUDE_DIRS
    assert "*.egg-info" in DEFAULT_EXCLUDE_DIRS
