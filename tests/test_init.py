"""Ensure package exports for coverage."""

from __future__ import annotations

import specleft

from specleft.version import SPECLEFT_VERSION


def test_package_exports() -> None:
    assert specleft.__version__ == SPECLEFT_VERSION
    assert specleft.specleft is not None
    assert specleft.step is not None
    assert specleft.shared_step is not None
    assert specleft.StepResult is not None
    assert specleft.SpecsConfig is not None
