# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Utilities for creating and updating feature markdown files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from slugify import slugify

SCENARIO_TAG = "<!-- specleft:scenario-add -->"
ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
STEP_KEYWORD_PATTERN = re.compile(
    r"^\s*[-*]?\s*(?:\*\*)?(Given|When|Then|And|But)(?:\*\*)?\b",
    re.IGNORECASE,
)
STEP_FORMAT_PATTERN = re.compile(
    r"^(?:\*\*)?(Given|When|Then|And|But)(?:\*\*)?\s+(.+)$",
    re.IGNORECASE,
)


@dataclass
class FeatureAddResult:
    success: bool
    file_path: Path
    markdown_content: str
    error: str | None = None


@dataclass
class ScenarioAddResult:
    success: bool
    file_path: Path
    scenario_id: str
    markdown_diff: str
    test_stub: str | None = None
    error: str | None = None


def generate_scenario_id(title: str) -> str:
    return slugify(title, lowercase=True)


def validate_feature_id(feature_id: str) -> None:
    if not ID_PATTERN.match(feature_id):
        raise ValueError(
            "Feature ID must match ^[a-z0-9-]+$ (lowercase letters, digits, dashes)"
        )


def validate_scenario_id(scenario_id: str) -> None:
    if not ID_PATTERN.match(scenario_id):
        raise ValueError(
            "Scenario ID must match ^[a-z0-9-]+$ (lowercase letters, digits, dashes)"
        )


def validate_step_keywords(steps: list[str]) -> list[str]:
    warnings: list[str] = []
    for step in steps:
        if not STEP_KEYWORD_PATTERN.match(step.strip()):
            warnings.append(
                "Step does not start with Given/When/Then/And/But: " + step.strip()
            )
    return warnings


def _feature_file_path(features_dir: Path, feature_id: str) -> Path:
    if feature_id.startswith("feature-"):
        filename = f"{feature_id}.md"
    else:
        filename = f"feature-{feature_id}.md"
    return features_dir / filename


def create_feature_file(
    *,
    features_dir: Path,
    feature_id: str,
    title: str,
    priority: str = "medium",
    description: str | None = None,
    dry_run: bool = False,
) -> FeatureAddResult:
    validate_feature_id(feature_id)
    file_path = _feature_file_path(features_dir, feature_id)

    if file_path.exists():
        return FeatureAddResult(
            success=False,
            file_path=file_path,
            markdown_content="",
            error=f"Feature file already exists: {file_path}",
        )

    markdown_content = _build_feature_markdown(
        title=title,
        priority=priority,
        description=description,
    )

    if not dry_run:
        features_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(markdown_content)

    return FeatureAddResult(
        success=True,
        file_path=file_path,
        markdown_content=markdown_content,
    )


def add_scenario_to_feature(
    *,
    features_dir: Path,
    feature_id: str,
    title: str,
    scenario_id: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    steps: list[str] | None = None,
    dry_run: bool = False,
) -> ScenarioAddResult:
    validate_feature_id(feature_id)
    file_path = _feature_file_path(features_dir, feature_id)
    if not file_path.exists():
        return ScenarioAddResult(
            success=False,
            file_path=file_path,
            scenario_id="",
            markdown_diff="",
            error=f"Feature file not found: {file_path}",
        )

    resolved_id = scenario_id or generate_scenario_id(title)
    validate_scenario_id(resolved_id)

    scenario_block = _build_scenario_markdown(
        title=title,
        priority=priority,
        tags=tags,
        steps=steps,
    )

    content = file_path.read_text()
    if _has_tag_window(content):
        updated = _insert_scenario_in_tag_window(content, scenario_block)
    else:
        updated = _insert_tag_window_with_scenario(content, scenario_block)

    if not dry_run:
        file_path.write_text(updated)

    return ScenarioAddResult(
        success=True,
        file_path=file_path,
        scenario_id=resolved_id,
        markdown_diff=scenario_block,
        test_stub=None,
    )


def _build_feature_markdown(
    *, title: str, priority: str, description: str | None
) -> str:
    lines: list[str] = [f"# Feature: {title}", "", f"priority: {priority}"]
    if description:
        lines.extend(["", description.strip()])
    lines.extend(["", "## Scenarios", "", SCENARIO_TAG, SCENARIO_TAG, ""])
    return "\n".join(lines)


def _build_scenario_markdown(
    *,
    title: str,
    priority: str | None,
    tags: list[str] | None,
    steps: list[str] | None,
) -> str:
    lines: list[str] = [f"### Scenario: {title}"]
    if priority:
        lines.append(f"priority: {priority}")
    if tags:
        cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
        if cleaned_tags:
            lines.append(f"tags: {', '.join(cleaned_tags)}")
    if steps:
        lines.append("")
        for step in steps:
            lines.append(_format_step_line(step))
    lines.append("")
    return "\n".join(lines)


def _format_step_line(step: str) -> str:
    raw = step.strip()
    if raw.startswith("-"):
        raw = raw.lstrip("-").strip()
    match = STEP_FORMAT_PATTERN.match(raw)
    if not match:
        return f"- {raw}"
    keyword = match.group(1).capitalize()
    remainder = match.group(2).strip()
    return f"- **{keyword}** {remainder}"


def _has_tag_window(content: str) -> bool:
    first = content.find(SCENARIO_TAG)
    if first == -1:
        return False
    return content.find(SCENARIO_TAG, first + len(SCENARIO_TAG)) != -1


def _insert_scenario_in_tag_window(content: str, scenario_block: str) -> str:
    first = content.find(SCENARIO_TAG)
    second = content.find(SCENARIO_TAG, first + len(SCENARIO_TAG))
    insert_at = second
    prefix = content[:insert_at]
    suffix = content[insert_at:]
    if not prefix.endswith("\n"):
        prefix += "\n"
    if not prefix.endswith("\n\n"):
        prefix += "\n"
    insertion = scenario_block.rstrip() + "\n"
    return prefix + insertion + suffix


def _insert_tag_window_with_scenario(content: str, scenario_block: str) -> str:
    match = re.search(r"^##\s+Scenarios\s*$", content, re.MULTILINE)
    insertion = f"\n\n{SCENARIO_TAG}\n{scenario_block.rstrip()}\n{SCENARIO_TAG}\n"
    if not match:
        return content.rstrip() + insertion

    section_end = match.end()
    next_heading = re.search(r"^##\s+\S+", content[section_end:], re.MULTILINE)
    if next_heading:
        insert_at = section_end + next_heading.start()
        prefix = content[:insert_at].rstrip()
        suffix = content[insert_at:].lstrip("\n")
        return prefix + insertion + suffix

    return content.rstrip() + insertion
