# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Python framework policy resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from specleft.discovery.frameworks.python.rules import PytestRule, UnittestRule
from specleft.discovery.frameworks.types import FrameworkRule
from specleft.discovery.models import SupportedLanguage

if TYPE_CHECKING:
    from specleft.discovery.framework_detector import DetectionContext


@dataclass(frozen=True)
class PythonFrameworkPolicy:
    """Resolve Python frameworks with explicit ambiguity handling."""

    language: SupportedLanguage = SupportedLanguage.PYTHON
    rules: tuple[FrameworkRule, ...] = cast(
        tuple[FrameworkRule, ...],
        (PytestRule(), UnittestRule()),
    )

    def detect(self, ctx: DetectionContext) -> list[str]:
        signals = {rule.name: rule.signals(ctx) for rule in self.rules}
        pytest_signals = signals.get("pytest")

        # Explicit pytest config with no test files is ambiguous.
        if pytest_signals and pytest_signals.manifest and not ctx.python_test_files:
            return ["unknown"]

        frameworks: list[str] = []
        for rule in self.rules:
            evidence = signals[rule.name]
            if (evidence.manifest or evidence.pattern or evidence.confirmed) and (
                evidence.confirmed
            ):
                frameworks.append(rule.name)

        return frameworks
