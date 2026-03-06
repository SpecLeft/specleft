# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for project language detection."""

from __future__ import annotations

from pathlib import Path

from specleft.discovery.file_index import FileIndex
from specleft.discovery.language_detect import detect_project_languages
from specleft.discovery.models import SupportedLanguage


def test_detect_project_languages_uses_ratio_threshold(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x=1")
    (tmp_path / "b.py").write_text("x=2")
    (tmp_path / "c.py").write_text("x=3")
    (tmp_path / "d.ts").write_text("const x = 1;")
    (tmp_path / "notes.md").write_text("notes")

    index = FileIndex(tmp_path)

    assert set(detect_project_languages(index)) == {
        SupportedLanguage.PYTHON,
        SupportedLanguage.TYPESCRIPT,
    }
    assert set(detect_project_languages(index, threshold=0.7)) == set()


def test_detect_project_languages_empty_index_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("no supported files")
    index = FileIndex(tmp_path)

    assert detect_project_languages(index) == []
