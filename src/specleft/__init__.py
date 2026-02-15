# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""SpecLeft - Specification-driven test management for pytest."""

from specleft.version import SPECLEFT_VERSION
from specleft.decorators import StepResult, shared_step, specleft, step
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

__version__ = SPECLEFT_VERSION
__all__ = [
    "ExecutionTime",
    "FeatureSpec",
    "Priority",
    "ScenarioSpec",
    "SpecDataRow",
    "SpecStep",
    "SpecsConfig",
    "StepResult",
    "StepType",
    "StorySpec",
    "shared_step",
    "specleft",
    "step",
]
