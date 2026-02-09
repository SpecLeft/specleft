"""Tests for specleft.utils.feature_writer."""

from __future__ import annotations

from pathlib import Path

from specleft.utils.feature_writer import (
    add_scenario_to_feature,
    create_feature_file,
    generate_feature_id,
    generate_scenario_id,
    validate_feature_id,
    validate_step_keywords,
)


class TestFeatureWriter:
    """Basic unit tests for feature writer utilities."""

    def test_generate_scenario_id(self) -> None:
        assert (
            generate_scenario_id("User Logs In Successfully")
            == "user-logs-in-successfully"
        )

    def test_generate_feature_id(self) -> None:
        assert generate_feature_id("CLI Authoring") == "cli-authoring"

    def test_validate_feature_id_invalid(self) -> None:
        try:
            validate_feature_id("Invalid ID")
        except ValueError as exc:
            assert "Feature ID must match" in str(exc)
        else:
            raise AssertionError("Expected ValueError")

    def test_validate_step_keywords_warns(self) -> None:
        warnings = validate_step_keywords(
            [
                "Given a valid user",
                "Tap submit",
            ]
        )
        assert len(warnings) == 1
        assert "Tap submit" in warnings[0]

    def test_create_feature_file_dry_run(self, tmp_path: Path) -> None:
        base_dir = tmp_path
        result = create_feature_file(
            features_dir=base_dir / "features",
            feature_id="cli-authoring",
            title="CLI Authoring",
            dry_run=True,
        )
        assert result.success is True
        assert "# Feature: CLI Authoring" in result.markdown_content
        assert not result.file_path.exists()

    def test_add_scenario_without_tag_window(self, tmp_path: Path) -> None:
        base_dir = tmp_path
        features_dir = base_dir / "features"
        features_dir.mkdir(exist_ok=True)
        feature_path = features_dir / "cli-authoring.md"
        feature_path.write_text("# Feature: CLI Authoring\n\n## Scenarios\n\n")

        result = add_scenario_to_feature(
            features_dir=features_dir,
            feature_id="cli-authoring",
            title="Append scenario",
            steps=["Given a scenario", "When appended", "Then it is added"],
            dry_run=False,
        )
        assert result.success is True
        content = feature_path.read_text()
        assert "<!-- specleft:scenario-add -->" in content
        assert "### Scenario: Append scenario" in content
