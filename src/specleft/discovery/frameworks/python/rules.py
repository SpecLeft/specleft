# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Python framework detection rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from specleft.discovery.frameworks import io
from specleft.discovery.frameworks.types import FrameworkSignals
from specleft.discovery.models import SupportedLanguage

if TYPE_CHECKING:
    from specleft.discovery.framework_detector import DetectionContext


@dataclass(frozen=True)
class PytestRule:
    """Detect pytest using manifest + file pattern confirmation."""

    name: str = "pytest"
    language: SupportedLanguage = SupportedLanguage.PYTHON

    def signals(self, ctx: DetectionContext) -> FrameworkSignals:
        manifest = io.manifest_signals_pytest(ctx.pyproject) or any(
            io.is_pytest_requirement_line(line) for line in ctx.requirements_lines
        )
        pattern = bool(ctx.python_test_files or ctx.conftest_files)
        return FrameworkSignals(manifest=manifest, pattern=pattern, confirmed=pattern)


@dataclass(frozen=True)
class UnittestRule:
    """Detect unittest using requirement hints + class confirmation."""

    name: str = "unittest"
    language: SupportedLanguage = SupportedLanguage.PYTHON

    def signals(self, ctx: DetectionContext) -> FrameworkSignals:
        manifest = any("unittest" in line for line in ctx.requirements_lines)
        confirmed = ctx.has_unittest_testcases
        return FrameworkSignals(
            manifest=manifest,
            pattern=confirmed,
            confirmed=confirmed,
        )
