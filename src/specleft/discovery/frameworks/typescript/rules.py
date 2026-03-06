# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""TypeScript/JavaScript framework detection rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from specleft.discovery.frameworks.types import FrameworkSignals
from specleft.discovery.models import SupportedLanguage

if TYPE_CHECKING:
    from specleft.discovery.framework_detector import DetectionContext


@dataclass(frozen=True)
class JestRule:
    """Detect Jest via manifest and config-file patterns."""

    name: str = "jest"
    language: SupportedLanguage = SupportedLanguage.TYPESCRIPT

    def signals(self, ctx: DetectionContext) -> FrameworkSignals:
        manifest = "jest" in ctx.typescript_manifest_frameworks
        pattern = bool(ctx.jest_configs)
        return FrameworkSignals(manifest=manifest, pattern=pattern, confirmed=pattern)


@dataclass(frozen=True)
class VitestRule:
    """Detect Vitest via manifest and vite+test patterns."""

    name: str = "vitest"
    language: SupportedLanguage = SupportedLanguage.TYPESCRIPT

    def signals(self, ctx: DetectionContext) -> FrameworkSignals:
        manifest = "vitest" in ctx.typescript_manifest_frameworks
        pattern = bool(ctx.vite_configs and ctx.vitest_tests)
        return FrameworkSignals(manifest=manifest, pattern=pattern, confirmed=pattern)
