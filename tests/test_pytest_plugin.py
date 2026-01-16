"""Tests for the pytest plugin functionality.

Tests cover:
- Hook execution order
- Metadata collection from @specleft decorated tests
- Runtime marker injection from tags
- Thread-local storage handling
- Handling of missing specs
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


def _write_specs_tree(base_dir: Path) -> Path:
    features_dir = base_dir / "features"
    auth_story_dir = features_dir / "auth" / "login"
    parse_story_dir = features_dir / "parse" / "units"
    auth_story_dir.mkdir(parents=True, exist_ok=True)
    parse_story_dir.mkdir(parents=True, exist_ok=True)

    (features_dir / "auth" / "_feature.md").write_text(
        """
---
feature_id: auth
priority: critical
tags: [core]
---

# Feature: User Authentication
""".strip()
    )
    (auth_story_dir / "_story.md").write_text(
        """
---
story_id: login
priority: high
tags: [auth-flow]
---

# Story: Login
""".strip()
    )
    (auth_story_dir / "login_success.md").write_text(
        """
---
scenario_id: login-success
priority: high
tags: [smoke, critical, auth-flow]
execution_time: fast
---

# Scenario: Successful login

## Steps
- **Given** user has valid credentials
- **When** user logs in
- **Then** user sees dashboard
""".strip()
    )
    (auth_story_dir / "login_failure.md").write_text(
        """
---
scenario_id: login-failure
priority: medium
tags: [regression, negative]
execution_time: fast
---

# Scenario: Failed login

## Steps
- **Given** user has invalid credentials
- **When** user tries to log in
- **Then** user sees error message
""".strip()
    )

    (features_dir / "parse" / "_feature.md").write_text(
        """
---
feature_id: parse
priority: high
tags: [unit]
---

# Feature: Unit Parsing
""".strip()
    )
    (parse_story_dir / "_story.md").write_text(
        """
---
story_id: units
priority: medium
tags: [parsing]
---

# Story: Units
""".strip()
    )
    (parse_story_dir / "extract_unit.md").write_text(
        """
---
scenario_id: extract-unit
priority: medium
tags: [unit, parsing]
execution_time: fast
---

# Scenario: Extract unit from string

## Steps
- **When** extracting unit
- **Then** unit is correct
""".strip()
    )

    return features_dir


if TYPE_CHECKING:
    from pytest import Pytester


@pytest.fixture
def create_specs_tree(pytester: Pytester) -> Path:
    """Create a Markdown specs tree in the test directory."""
    return _write_specs_tree(pytester.path)


@pytest.fixture(autouse=True)
def ensure_specs_tree(create_specs_tree: Path) -> None:
    """Ensure a default specs tree exists for plugin tests."""
    _ = create_specs_tree


class TestPytestConfigure:
    """Tests for pytest_configure hook."""

    def test_specleft_results_initialized(self, pytester: Pytester) -> None:
        """Test that _specleft_results is initialized on config."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_dummy():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_metadata_stored_on_item(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that metadata is stored on test items."""
        pytester.makeconftest(
            """
            def pytest_runtest_setup(item):
                if hasattr(item, '_specleft_metadata'):
                    metadata = item._specleft_metadata
                    assert metadata['feature_id'] == 'auth'
                    assert metadata['scenario_id'] == 'login-success'
            """
        )
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest()
        result.assert_outcomes(passed=1)


class TestMissingSpecsDirectory:
    """Tests for handling missing specs directories."""

    def test_no_specs_directory_runs_all_tests(self, pytester: Pytester) -> None:
        """Test that tests run without validation when specs are missing."""
        features_dir = pytester.path / "features"
        if features_dir.exists():
            for path in features_dir.rglob("*"):
                if path.is_file():
                    path.unlink()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="any-feature", scenario_id="any-scenario")
            def test_without_validation():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)


class TestMarkerInjection:
    """Tests for runtime marker injection from scenario tags."""

    def test_markers_injected_from_tags(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that markers are injected from scenario tags."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-tag", "smoke")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-tag", "critical")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-tag", "missing")
        result.assert_outcomes(skipped=1)

    def test_priority_marker_injected(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that priority markers are injected from spec priority."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-priority", "high")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-priority", "critical")
        result.assert_outcomes(skipped=1)


class TestStepCollection:
    """Tests for step collection during test execution."""

    def test_steps_collected(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that steps are collected during test execution."""
        pytester.makepyfile(
            """
            from specleft import specleft, step

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_with_steps():
                with step("Given user has credentials"):
                    pass
                with step("When user logs in"):
                    pass
                with step("Then user sees dashboard"):
                    pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)


class TestResultPersistence:
    """Tests for result persistence to disk."""

    def test_results_saved_to_disk(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that results are saved to .specleft/results/."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        results_dir = pytester.path / ".specleft" / "results"
        assert results_dir.exists(), "Results directory should exist"

        json_files = list(results_dir.glob("results_*.json"))
        assert len(json_files) == 1, "One results file should exist"

        results_data = json.loads(json_files[0].read_text())
        assert "summary" in results_data
        assert results_data["summary"]["passed"] == 1
        assert results_data["features"][0]["feature_name"] == "User Authentication"
        assert (
            results_data["features"][0]["scenarios"][0]["scenario_name"]
            == "Successful login"
        )


class TestSanitizeMarkerName:
    """Tests for marker name sanitization."""

    def test_hyphen_replaced(self) -> None:
        """Test that hyphens are replaced with underscores."""
        from specleft.pytest_plugin import _sanitize_marker_name

        assert _sanitize_marker_name("auth-flow") == "auth_flow"
