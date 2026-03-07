# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared discovery data models."""

from __future__ import annotations

import uuid
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from specleft.schema import SpecStep


class SupportedLanguage(str, Enum):
    """Languages supported by the discovery pipeline."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"


class ItemKind(str, Enum):
    """Item kinds produced by discovery miners."""

    TEST_FUNCTION = "test_function"
    API_ROUTE = "api_route"
    DOCSTRING = "docstring"
    GIT_COMMIT = "git_commit"


class TestFunctionMeta(BaseModel):
    """Metadata for discovered test functions."""

    framework: str
    class_name: str | None = None
    decorators: list[str] = Field(default_factory=list)
    has_docstring: bool = False
    docstring: str | None = None
    is_parametrized: bool = False
    call_style: str | None = None
    has_todo: bool = False


class ApiRouteMeta(BaseModel):
    """Metadata for discovered API route definitions."""

    http_method: str | list[str]
    path: str
    framework: str
    handler_name: str | None = None
    has_docstring: bool = False
    docstring: str | None = None
    response_model: str | None = None
    is_file_based_route: bool = False


class DocstringMeta(BaseModel):
    """Metadata for discovered docstrings."""

    target_kind: str
    target_name: str | None = None
    text: str


class GitCommitMeta(BaseModel):
    """Metadata for git commit records."""

    commit_hash: str
    subject: str
    body: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    conventional_type: str | None = None
    file_prefixes: list[str] = Field(default_factory=list)


METADATA_MODELS: dict[ItemKind, type[BaseModel]] = {
    ItemKind.TEST_FUNCTION: TestFunctionMeta,
    ItemKind.API_ROUTE: ApiRouteMeta,
    ItemKind.DOCSTRING: DocstringMeta,
    ItemKind.GIT_COMMIT: GitCommitMeta,
}

DEFAULT_DISCOVERY_OUTPUT_DIR = Path(".specleft/specs/_discovered")


class MinerErrorKind(str, Enum):
    """Categories for structured miner errors."""

    NOT_INSTALLED = "not_installed"
    PARSE_ERROR = "parse_error"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class DiscoveredItem(BaseModel):
    """A unit discovered by a miner."""

    kind: ItemKind
    name: str
    file_path: Path | None
    line_number: int | None = None
    language: SupportedLanguage | None
    raw_text: str | None = None
    metadata: dict[str, Any]
    confidence: float

    @model_validator(mode="after")
    def validate_metadata_keys(self) -> DiscoveredItem:
        model_cls = METADATA_MODELS.get(self.kind)
        if model_cls is not None:
            model_cls.model_validate(self.metadata)
        return self

    def typed_meta(self) -> BaseModel:
        """Return metadata materialised into the typed model."""
        model_cls = METADATA_MODELS[self.kind]
        return model_cls.model_validate(self.metadata)


class MinerResult(BaseModel):
    """Output from a single miner run."""

    miner_id: uuid.UUID
    miner_name: str
    items: list[DiscoveredItem]
    error: str | None = None
    error_kind: MinerErrorKind | None = None
    duration_ms: int


class DiscoveryReport(BaseModel):
    """Aggregated discovery output."""

    project_root: Path
    languages_detected: list[SupportedLanguage]
    miner_results: list[MinerResult]
    total_items: int
    errors: list[str]
    duration_ms: int

    @cached_property
    def all_items(self) -> list[DiscoveredItem]:
        """Flatten items across all successful miner results."""
        return [
            item
            for result in self.miner_results
            if result.error is None
            for item in result.items
        ]

    @cached_property
    def items_by_kind(self) -> dict[ItemKind, list[DiscoveredItem]]:
        """Group all items by kind."""
        grouped: dict[ItemKind, list[DiscoveredItem]] = {}
        for item in self.all_items:
            grouped.setdefault(item.kind, []).append(item)
        return grouped


class DraftScenario(BaseModel):
    """Draft scenario representation for phase-2 generation."""

    title: str
    priority: str = "medium"
    steps: list[SpecStep]
    source_items: list[DiscoveredItem]


class DraftFeature(BaseModel):
    """Draft feature representation for phase-2 generation."""

    feature_id: str
    name: str
    scenarios: list[DraftScenario]
    source_items: list[DiscoveredItem]
    confidence: float


class DraftSpec(BaseModel):
    """Container for generated draft specs."""

    features: list[DraftFeature]
    output_dir: Path = DEFAULT_DISCOVERY_OUTPUT_DIR
    generated_at: str
