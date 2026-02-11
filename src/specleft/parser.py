# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""SpecLeft Markdown Parser.

Parses feature specifications from Markdown files with YAML frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import frontmatter
from slugify import slugify

from specleft.schema import (
    ExecutionTime,
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecDataRow,
    SpecsConfig,
    SpecStep,
    StepType,
    StorySpec,
)
from specleft.templates.prd_template import (
    PRDTemplate,
    compile_pattern,
    default_template,
)


class SpecParser:
    """Parser for SpecLeft Markdown specifications."""

    FEATURE_FILE = "_feature.md"
    STORY_FILE = "_story.md"

    STEP_PATTERN = re.compile(
        r"^\s*[-*]\s+\*\*(Given|When|Then|And|But)\*\*\s+(.+)$",
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(self, template: PRDTemplate | None = None) -> None:
        self._template = template or default_template()
        self._feature_patterns = [
            compile_pattern(p) for p in self._template.features.patterns
        ]

    def parse_directory(self, features_dir: Path) -> SpecsConfig:
        """Parse all specifications from a features directory."""
        if not features_dir.exists():
            raise FileNotFoundError(f"Features directory not found: {features_dir}")

        features: list[FeatureSpec] = []

        for feature_path in sorted(features_dir.iterdir()):
            if feature_path.is_dir() and not feature_path.name.startswith("."):
                feature = self._parse_feature_dir(feature_path)
                if feature:
                    features.append(feature)
            elif feature_path.is_file() and feature_path.suffix == ".md":
                feature = self._parse_feature_markdown(feature_path)
                if feature:
                    features.append(feature)

        return SpecsConfig(features=features)

    def _parse_feature_dir(self, feature_dir: Path) -> FeatureSpec | None:
        """Parse a feature directory."""
        feature_file = feature_dir / self.FEATURE_FILE

        if feature_file.exists():
            feature = self._parse_feature_file(feature_file)
        else:
            feature = FeatureSpec(
                feature_id=feature_dir.name.lower().replace("_", "-"),
                name=feature_dir.name.replace("_", " ").title(),
            )

        feature.source_dir = feature_dir

        for story_dir in sorted(feature_dir.iterdir()):
            if story_dir.is_dir() and not story_dir.name.startswith("_"):
                story = self._parse_story_dir(story_dir)
                if story:
                    feature.stories.append(story)

        return feature if feature.stories else None

    def _parse_feature_markdown(self, filepath: Path) -> FeatureSpec | None:
        """Parse a single feature markdown file."""
        raw_content = filepath.read_text()
        body, metadata = self._split_metadata_block(raw_content)
        title = self._extract_feature_heading(body)
        if not title:
            return None

        priority = self._parse_priority(metadata.get("priority"))
        tags = self._normalize_tags(metadata.get("tags"))
        assumptions = self._normalize_list(metadata.get("assumptions"))
        open_questions = self._normalize_list(metadata.get("open_questions"))

        feature = FeatureSpec(
            feature_id=metadata.get("feature_id", filepath.stem),
            name=title,
            description=self._extract_description_from_body(body),
            component=metadata.get("component"),
            owner=metadata.get("owner"),
            priority=priority or Priority.MEDIUM,
            tags=tags,
            confidence=metadata.get("confidence"),
            source=metadata.get("source"),
            assumptions=assumptions,
            open_questions=open_questions,
            raw_metadata=metadata,
        )

        feature.source_file = filepath

        scenarios = self._parse_feature_scenarios(body, filepath)
        story = StorySpec(
            story_id="default",
            name="Default",
            scenarios=scenarios,
        )
        feature.stories.append(story)
        return feature

    def _parse_story_dir(self, story_dir: Path) -> StorySpec | None:
        """Parse a story directory."""
        story_file = story_dir / self.STORY_FILE

        if story_file.exists():
            story = self._parse_story_file(story_file)
        else:
            story = StorySpec(
                story_id=story_dir.name.lower().replace("_", "-"),
                name=story_dir.name.replace("_", " ").title(),
            )

        story.source_dir = story_dir

        for scenario_file in sorted(story_dir.glob("*.md")):
            if scenario_file.name.startswith("_"):
                continue
            scenario = self._parse_scenario_file(scenario_file)
            if scenario:
                story.scenarios.append(scenario)

        return story if story.scenarios else None

    def _parse_feature_file(self, filepath: Path) -> FeatureSpec:
        """Parse a _feature.md file."""
        post = frontmatter.load(filepath)
        metadata = post.metadata

        priority = self._parse_priority(metadata.get("priority")) or Priority.MEDIUM
        assumptions = self._normalize_list(metadata.get("assumptions"))
        open_questions = self._normalize_list(metadata.get("open_questions"))
        tags = self._normalize_tags(metadata.get("tags"))

        return FeatureSpec(
            feature_id=metadata.get("feature_id", filepath.parent.name),
            name=self._extract_title(post.content) or filepath.parent.name,
            description=self._extract_description(post.content),
            component=metadata.get("component"),
            owner=metadata.get("owner"),
            priority=priority,
            tags=tags,
            confidence=metadata.get("confidence"),
            source=metadata.get("source"),
            assumptions=assumptions,
            open_questions=open_questions,
            raw_metadata=metadata,
        )

    def _parse_story_file(self, filepath: Path) -> StorySpec:
        """Parse a _story.md file."""
        post = frontmatter.load(filepath)
        metadata = post.metadata

        priority = self._parse_priority(metadata.get("priority")) or Priority.MEDIUM
        tags = self._normalize_tags(metadata.get("tags"))
        return StorySpec(
            story_id=metadata.get("story_id", filepath.parent.name),
            name=self._extract_title(post.content) or filepath.parent.name,
            description=self._extract_description(post.content),
            priority=priority,
            tags=tags,
        )

    def _parse_scenario_file(self, filepath: Path) -> ScenarioSpec:
        """Parse a scenario.md file."""
        post = frontmatter.load(filepath)
        metadata = post.metadata
        content = post.content

        scenario_id = metadata.get(
            "scenario_id", filepath.stem.lower().replace("_", "-")
        )
        steps = self._parse_steps(content)
        test_data = self._parse_test_data_table(content)
        priority_value = metadata.get("priority")

        priority = self._parse_priority(priority_value)
        tags = self._normalize_tags(metadata.get("tags"))
        execution_time = self._parse_execution_time(metadata.get("execution_time"))

        return ScenarioSpec(
            scenario_id=scenario_id,
            name=self._extract_title(content) or filepath.stem.replace("_", " "),
            description=self._extract_description(content),
            priority=priority or Priority.MEDIUM,
            priority_raw=priority,
            tags=tags,
            execution_time=execution_time,
            steps=steps,
            test_data=test_data,
            source_file=filepath,
            raw_metadata=metadata,
        )

    def _extract_title(self, content: str) -> str | None:
        """Extract the first H1 title from Markdown content."""
        match = re.search(
            r"^#\s+(?:Scenario:|Story:|Feature:)?\s*(.+)$",
            content,
            re.MULTILINE,
        )
        return match.group(1).strip() if match else None

    def _extract_description(self, content: str) -> str | None:
        """Extract description (first paragraph after title)."""
        lines = content.split("\n")
        in_description = False
        description_lines: list[str] = []

        for line in lines:
            if line.startswith("# "):
                in_description = True
                continue
            if in_description:
                if (
                    line.startswith("#")
                    or line.startswith("## Steps")
                    or line.startswith("## Test Data")
                ):
                    break
                if line.strip():
                    description_lines.append(line.strip())
                elif description_lines:
                    break

        return " ".join(description_lines) if description_lines else None

    def _parse_steps(self, content: str) -> list[SpecStep]:
        """Parse Gherkin steps from Markdown content."""
        steps: list[SpecStep] = []

        steps_match = re.search(r"## Steps\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if not steps_match:
            return steps

        for match in self.STEP_PATTERN.finditer(steps_match.group(1)):
            step_type = match.group(1).lower()
            description = match.group(2).strip()
            description = re.sub(r"`([^`]+)`", r"\1", description)

            steps.append(SpecStep(type=StepType(step_type), description=description))

        return steps

    def _parse_test_data_table(self, content: str) -> list[SpecDataRow]:
        """Parse test data table from Markdown content."""
        test_data: list[SpecDataRow] = []

        data_match = re.search(r"## Test Data\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if not data_match:
            return test_data

        lines = [
            line.strip() for line in data_match.group(1).split("\n") if line.strip()
        ]
        if len(lines) < 3:
            return test_data

        header_line = lines[0]
        if not header_line.startswith("|"):
            return test_data

        headers = [header.strip() for header in header_line.strip("|").split("|")]

        for line in lines[2:]:
            if not line.startswith("|"):
                continue

            values = [value.strip() for value in line.strip("|").split("|")]
            if len(values) != len(headers):
                continue

            params: dict[str, Any] = {}
            description = None

            for header, value in zip(headers, values, strict=False):
                if header.lower() == "description":
                    description = value
                else:
                    params[header] = self._convert_value(value)

            if params:
                test_data.append(SpecDataRow(params=params, description=description))

        return test_data

    def _parse_feature_scenarios(
        self, content: str, source_file: Path
    ) -> list[ScenarioSpec]:
        scenarios: list[ScenarioSpec] = []
        for match in re.finditer(r"^###\s+Scenario:\s*(.+)$", content, re.MULTILINE):
            title = match.group(1).strip()
            block = content[match.end() :]
            next_header = re.search(r"^###\s+Scenario:", block, re.MULTILINE)
            if next_header:
                block = block[: next_header.start()]
            scenarios.append(self._parse_scenario_block(title, block, source_file))
        return scenarios

    def _parse_scenario_block(
        self, title: str, block: str, source_file: Path
    ) -> ScenarioSpec:
        priority = self._parse_priority(self._extract_scenario_priority(block))
        steps = self._extract_scenario_steps(block)
        scenario_id = slugify(title)
        return ScenarioSpec(
            scenario_id=scenario_id,
            name=title,
            description=self._extract_scenario_description(block),
            priority=priority or Priority.MEDIUM,
            priority_raw=priority,
            tags=[],
            execution_time=ExecutionTime.FAST,
            steps=steps,
            test_data=[],
            source_file=source_file,
            raw_metadata={},
        )

    def _extract_feature_heading(self, content: str) -> str | None:
        """Extract the feature title from an H1 heading.

        Tries each compiled feature pattern from the PRD template against
        the first ``# …`` line.  When no pattern matches, falls back to
        using the raw H1 text so that files produced by ``specleft plan``
        (which may omit the ``Feature:`` prefix) are still parsed.
        """
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if not h1_match:
            return None

        heading_text = h1_match.group(1).strip()

        # Try each compiled template pattern against the heading text.
        for pattern in self._feature_patterns:
            m = pattern.match(heading_text)
            if m and "title" in m.groupdict():
                return m.group("title").strip()

        # Fallback: use the raw heading as the title.
        return heading_text

    def _extract_description_from_body(self, content: str) -> str | None:
        lines = [line.rstrip() for line in content.split("\n")]
        for index, line in enumerate(lines):
            if line.startswith("# "):
                remainder = lines[index + 1 :]
                return self._extract_paragraph(remainder)
        return self._extract_paragraph(lines)

    def _extract_paragraph(self, lines: list[str]) -> str | None:
        description_lines: list[str] = []
        for line in lines:
            if line.startswith("#"):
                break
            if line.strip():
                description_lines.append(line.strip())
            elif description_lines:
                break
        return " ".join(description_lines) if description_lines else None

    def _extract_scenario_priority(self, block: str) -> str | None:
        match = re.search(r"^priority:\s*([\w-]+)$", block, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_scenario_steps(self, block: str) -> list[SpecStep]:
        steps: list[SpecStep] = []
        for line in block.splitlines():
            match = re.match(
                r"^\s*[-*]\s+(?:\*\*)?(Given|When|Then|And|But)(?:\*\*)?\s+(.+)$", line
            )
            if not match:
                continue
            step_type = match.group(1).lower()
            description = re.sub(r"`([^`]+)`", r"\1", match.group(2).strip())
            steps.append(SpecStep(type=StepType(step_type), description=description))
        return steps

    def _extract_scenario_description(self, block: str) -> str | None:
        for line in block.splitlines():
            if line.strip().startswith("-"):
                break
            if line.strip().startswith("priority:"):
                continue
            if line.strip():
                return line.strip()
        return None

    def _split_metadata_block(self, content: str) -> tuple[str, dict[str, Any]]:
        match = re.search(r"\n---\s*\n([\s\S]+?)\n---\s*$", content)
        if not match:
            return content, {}
        raw = match.group(0)
        try:
            metadata = frontmatter.loads(raw + "\n").metadata
        except Exception:
            return content, {}
        body = content[: match.start()].rstrip()
        return body, metadata

    def _parse_priority(self, value: str | None) -> Priority | None:
        if not value:
            return None
        try:
            return Priority(str(value).lower())
        except ValueError:
            return None

    def _parse_execution_time(self, value: str | None) -> ExecutionTime:
        if not value:
            return ExecutionTime.FAST
        try:
            return ExecutionTime(str(value).lower())
        except ValueError:
            return ExecutionTime.FAST

    def _normalize_list(self, value: Any) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    def _normalize_tags(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type."""
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        if value.lower() in ("none", "null", ""):
            return None
        return value
