from __future__ import annotations

from pathlib import Path

import pytest

from specleft.utils.specs_dir import resolve_specs_dir


def test_resolve_specs_dir_prefers_explicit_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "custom").mkdir()
    assert resolve_specs_dir("custom") == Path("custom")


def test_resolve_specs_dir_prefers_specleft_specs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specleft" / "specs").mkdir(parents=True)
    (tmp_path / "features").mkdir()
    assert resolve_specs_dir(None) == Path(".specleft/specs")


def test_resolve_specs_dir_falls_back_to_features(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "features").mkdir()
    assert resolve_specs_dir(None) == Path("features")
