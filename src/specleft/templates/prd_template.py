# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""PRD template models and loader."""

from __future__ import annotations

import re
from pathlib import Path

import click
import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class PRDFeaturesConfig(BaseModel):
    heading_level: int | list[int] = 2
    patterns: list[str] = Field(
        default_factory=lambda: ["Feature: {title}", "Feature {title}"]
    )
    contains: list[str] = Field(default_factory=list)
    match_mode: str = "any"
    exclude: list[str] = Field(
        default_factory=lambda: [
            "Overview",
            "Goals",
            "Non-Goals",
            "Open Questions",
            "Notes",
        ]
    )

    @field_validator("heading_level")
    @classmethod
    def validate_heading_level(cls, value: int | list[int]) -> int | list[int]:
        _validate_heading_levels(value)
        return value

    @field_validator("match_mode")
    @classmethod
    def validate_match_mode(cls, value: str) -> str:
        _validate_match_mode(value)
        return value


class PRDScenariosConfig(BaseModel):
    heading_level: list[int] = Field(default_factory=lambda: [3, 4])
    patterns: list[str] = Field(default_factory=lambda: ["Scenario: {title}"])
    contains: list[str] = Field(default_factory=list)
    match_mode: str = "any"
    step_keywords: list[str] = Field(
        default_factory=lambda: ["Given", "When", "Then", "And", "But"]
    )

    @field_validator("heading_level")
    @classmethod
    def validate_heading_level(cls, value: list[int]) -> list[int]:
        _validate_heading_levels(value)
        return value

    @field_validator("match_mode")
    @classmethod
    def validate_match_mode(cls, value: str) -> str:
        _validate_match_mode(value)
        return value


class PRDPrioritiesConfig(BaseModel):
    patterns: list[str] = Field(
        default_factory=lambda: ["priority: {value}", "Priority: {value}"]
    )
    mapping: dict[str, str] = Field(default_factory=dict)


class PRDTemplate(BaseModel):
    version: str = "1.0"
    features: PRDFeaturesConfig = Field(default_factory=PRDFeaturesConfig)
    scenarios: PRDScenariosConfig = Field(default_factory=PRDScenariosConfig)
    priorities: PRDPrioritiesConfig = Field(default_factory=PRDPrioritiesConfig)


def _validate_heading_levels(levels: int | list[int]) -> None:
    values = [levels] if isinstance(levels, int) else list(levels)
    if not values:
        raise ValueError("Heading levels cannot be empty")
    invalid = [
        level
        for level in values
        if not isinstance(level, int) or level < 1 or level > 6
    ]
    if invalid:
        raise ValueError("Heading levels must be integers between 1 and 6")


def _validate_match_mode(mode: str) -> None:
    valid = {"any", "all", "patterns", "contains"}
    if mode not in valid:
        raise ValueError("Match mode must be one of: any, all, patterns, contains")


def _literal_to_regex(text: str) -> str:
    parts: list[str] = []
    in_whitespace = False
    for char in text:
        if char.isspace():
            if not in_whitespace:
                parts.append(r"\s+")
                in_whitespace = True
            continue
        in_whitespace = False
        parts.append(re.escape(char))
    return "".join(parts)


def compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a template pattern into a regex with named groups."""
    placeholder_regex = re.compile(r"{([^}]+)}")
    placeholders = list(placeholder_regex.finditer(pattern))
    if not placeholders:
        raise ValueError("Pattern must include {title} or {value}")

    seen: set[str] = set()
    compiled_parts: list[str] = ["^"]
    last_index = 0

    for index, match in enumerate(placeholders):
        name = match.group(1)
        if name not in {"title", "value"}:
            raise ValueError(f"Unknown placeholder '{{{name}}}'")
        if name in seen:
            raise ValueError(f"Duplicate placeholder '{{{name}}}' is not supported")
        seen.add(name)

        literal = pattern[last_index : match.start()]
        compiled_parts.append(_literal_to_regex(literal))

        is_last = index == len(placeholders) - 1
        trailing_literal = pattern[match.end() :] if is_last else ""
        is_terminal = is_last and not trailing_literal
        group_pattern = r".+" if is_terminal else r".+?"
        compiled_parts.append(f"(?P<{name}>{group_pattern})")
        last_index = match.end()

    compiled_parts.append(_literal_to_regex(pattern[last_index:]))
    compiled_parts.append("$")

    return re.compile("".join(compiled_parts))


def _validate_patterns(patterns: list[str], *, context: str) -> None:
    for pattern in patterns:
        try:
            compile_pattern(pattern)
        except ValueError as exc:
            raise click.ClickException(
                f"Invalid {context} pattern '{pattern}': {exc}"
            ) from exc


def load_template(path: Path) -> PRDTemplate:
    """Load a PRD template from a YAML file."""
    try:
        raw = path.read_text()
    except OSError as exc:
        raise click.ClickException(
            f"Unable to read template file at {path}: {exc}"
        ) from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        location = ""
        mark = getattr(exc, "problem_mark", None)
        if mark is not None:
            location = f" (line {mark.line + 1}, column {mark.column + 1})"
        raise click.ClickException(
            f"Invalid YAML in template {path}{location}. Ensure the file is valid YAML."
        ) from exc

    if data is None:
        raise click.ClickException(f"Template file is empty: {path}")

    try:
        template = PRDTemplate.model_validate(data)
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(item) for item in error.get('loc', []))}: {error.get('msg')}"
            for error in exc.errors()
        )
        raise click.ClickException(
            f"Invalid template structure in {path}: {errors}"
        ) from exc

    _validate_patterns(template.features.patterns, context="feature")
    _validate_patterns(template.scenarios.patterns, context="scenario")
    _validate_patterns(template.priorities.patterns, context="priority")

    return template


def default_template() -> PRDTemplate:
    return PRDTemplate()
