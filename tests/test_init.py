"""Ensure package exports for coverage."""

from __future__ import annotations

import specleft


def test_package_exports() -> None:
    assert specleft.__version__ == "0.2.0"
    assert specleft.specleft
    assert specleft.step
    assert specleft.shared_step
    assert specleft.StepResult
    assert specleft.SpecsConfig
