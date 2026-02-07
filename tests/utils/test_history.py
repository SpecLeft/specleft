"""Tests for specleft.utils.history."""

from __future__ import annotations

from pathlib import Path

import pytest

from specleft.utils.history import load_feature_history, log_feature_event


class TestHistory:
    """Basic history logging tests."""

    def test_log_and_load_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        entries = log_feature_event(
            "feature-cli-authoring",
            "feature_created",
            {"title": "CLI Feature Authoring"},
        )

        assert len(entries) == 1
        assert entries[0]["action"] == "feature_created"

        loaded = load_feature_history("feature-cli-authoring")
        assert len(loaded) == 1
        assert loaded[0]["details"]["title"] == "CLI Feature Authoring"
