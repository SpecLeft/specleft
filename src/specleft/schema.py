"""Pydantic models for features.json schema validation.

This module defines the schema for features.json which describes test features,
scenarios, and their metadata. The schema is designed to be extensible with
generic metadata at all levels.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class StepType(str, Enum):
    """Valid step types for test steps (BDD-style)."""

    GIVEN = "given"
    WHEN = "when"
    THEN = "then"
    AND = "and"


class Priority(str, Enum):
    """Priority levels for features and scenarios."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExecutionSpeed(str, Enum):
    """Expected execution speed for scenarios."""

    FAST = "fast"  # < 1 second
    MEDIUM = "medium"  # 1-10 seconds
    SLOW = "slow"  # > 10 seconds


class TestType(str, Enum):
    """Types of tests for categorization."""

    SMOKE = "smoke"
    REGRESSION = "regression"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    UNIT = "unit"


class ExternalReference(BaseModel):
    """Generic external system reference.

    Used to link features/scenarios to external systems like Jira, GitHub,
    ADO, Linear, etc. without hardcoding specific integrations.
    """

    system: str = Field(
        ..., description="External system name (e.g., 'jira', 'github', 'ado')"
    )
    id: str = Field(..., description="Ticket/issue ID in the external system")
    url: HttpUrl | None = Field(
        default=None, description="URL to the ticket/issue in the external system"
    )


class StepMetadata(BaseModel):
    """Metadata at step level.

    Provides configuration for individual test steps.
    """

    timeout_seconds: int | None = Field(
        default=None, gt=0, description="Maximum execution time for this step"
    )
    retry_on_failure: bool = Field(
        default=False, description="Whether to retry this step if it fails"
    )
    continue_on_failure: bool = Field(
        default=False, description="Continue test execution if this step fails"
    )
    custom: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata for extensibility"
    )


class ScenarioMetadata(BaseModel):
    """Metadata at scenario level.

    Provides detailed configuration and categorization for test scenarios.
    """

    test_type: TestType | None = Field(
        default=None, description="Type of test (smoke, regression, etc.)"
    )
    execution_time: ExecutionSpeed = Field(
        default=ExecutionSpeed.MEDIUM, description="Expected execution time category"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="External dependencies (e.g., ['database', 'redis'])",
    )
    external_references: list[ExternalReference] = Field(
        default_factory=list, description="Links to external tracking systems"
    )
    author: str | None = Field(default=None, description="Test author")
    created_date: str | None = Field(
        default=None, description="Creation date (ISO 8601)"
    )
    updated_date: str | None = Field(
        default=None, description="Last update date (ISO 8601)"
    )
    flaky: bool = Field(
        default=False, description="Mark test as flaky for special handling"
    )
    skip: bool = Field(default=False, description="Skip this scenario by default")
    skip_reason: str | None = Field(
        default=None, description="Reason for skipping this scenario"
    )
    custom: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata for extensibility"
    )


class FeatureMetadata(BaseModel):
    """Metadata at feature level.

    Provides ownership, categorization, and documentation links for features.
    """

    owner: str | None = Field(
        default=None, description="Team or person responsible for this feature"
    )
    component: str | None = Field(
        default=None, description="Component or module this feature belongs to"
    )
    priority: Priority = Field(
        default=Priority.MEDIUM, description="Default priority for all scenarios"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization"
    )
    external_references: list[ExternalReference] = Field(
        default_factory=list, description="Links to external tracking systems"
    )
    links: dict[str, HttpUrl] = Field(
        default_factory=dict,
        description="Named links (e.g., {'documentation': 'https://...'})",
    )
    custom: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata for extensibility"
    )


class TestStep(BaseModel):
    """Individual test step (given/when/then).

    Represents a single step in a test scenario with BDD-style type and description.
    """

    type: StepType = Field(..., description="Step type (given/when/then/and)")
    description: str = Field(min_length=1, description="Step description")
    metadata: StepMetadata | None = Field(
        default=None, description="Optional step-level metadata"
    )


class TestDataRow(BaseModel):
    """Single row of test data for parameterization.

    Used for data-driven testing where the same scenario runs with different inputs.
    """

    params: dict[str, Any] = Field(
        ..., description="Parameter values for this test case"
    )
    description: str | None = Field(
        default=None, description="Human-readable description of this test case"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata for this test case"
    )


class Scenario(BaseModel):
    """Test scenario with steps.

    A scenario represents a single test case within a feature, with its own
    steps, priority, tags, and optional test data for parameterization.
    """

    id: str = Field(
        pattern=r"^[a-z0-9-]+$",
        description="Unique scenario identifier (lowercase, hyphens allowed)",
    )
    name: str = Field(..., description="Human-readable scenario name")
    description: str | None = Field(
        default=None, description="Detailed description of the scenario"
    )
    priority: Priority = Field(
        default=Priority.MEDIUM, description="Priority level for this scenario"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and pytest marker injection",
    )
    metadata: ScenarioMetadata | None = Field(
        default=None, description="Optional scenario-level metadata"
    )
    steps: list[TestStep] = Field(
        ..., min_length=1, description="List of test steps"
    )
    test_data: list[TestDataRow] = Field(
        default_factory=list, description="Test data for parameterization"
    )


class Feature(BaseModel):
    """Feature containing scenarios.

    A feature represents a high-level functionality area with one or more
    test scenarios. Features are identified by uppercase IDs.
    """

    id: str = Field(
        pattern=r"^[A-Z0-9-]+$",
        description="Unique feature identifier (uppercase, hyphens allowed)",
    )
    name: str = Field(..., description="Human-readable feature name")
    description: str | None = Field(
        default=None, description="Detailed description of the feature"
    )
    metadata: FeatureMetadata | None = Field(
        default=None, description="Optional feature-level metadata"
    )
    scenarios: list[Scenario] = Field(
        ..., min_length=1, description="List of test scenarios"
    )

    @model_validator(mode="after")
    def validate_unique_scenario_ids(self) -> Feature:
        """Ensure scenario IDs are unique within the feature."""
        scenario_ids = [s.id for s in self.scenarios]
        duplicates = [sid for sid in scenario_ids if scenario_ids.count(sid) > 1]
        if duplicates:
            raise ValueError(
                f"Duplicate scenario IDs in feature '{self.id}': {set(duplicates)}"
            )
        return self


class FeaturesConfig(BaseModel):
    """Root configuration containing all features.

    This is the top-level model for features.json files. It contains a version
    string and a list of features.
    """

    version: str = Field(default="1.0", description="Schema version")
    features: list[Feature] = Field(
        ..., min_length=1, description="List of features"
    )

    @model_validator(mode="after")
    def validate_unique_feature_ids(self) -> FeaturesConfig:
        """Ensure feature IDs are unique."""
        feature_ids = [f.id for f in self.features]
        duplicates = [fid for fid in feature_ids if feature_ids.count(fid) > 1]
        if duplicates:
            raise ValueError(f"Duplicate feature IDs: {set(duplicates)}")
        return self

    @classmethod
    def from_file(cls, filepath: str | Path) -> FeaturesConfig:
        """Load and validate features.json.

        Args:
            filepath: Path to the features.json file.

        Returns:
            Validated FeaturesConfig instance.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            pydantic.ValidationError: If the JSON doesn't match the schema.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Features file not found: {filepath}")

        with path.open() as f:
            data = json.load(f)
        return cls.model_validate(data)
