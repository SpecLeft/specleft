# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""TypeScript/JavaScript framework policy resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from specleft.discovery.frameworks.types import FrameworkRule
from specleft.discovery.frameworks.typescript.rules import JestRule, VitestRule
from specleft.discovery.models import SupportedLanguage

if TYPE_CHECKING:
    from specleft.discovery.framework_detector import DetectionContext


@dataclass(frozen=True)
class TypeScriptFrameworkPolicy:
    """Resolve TS/JS frameworks where file patterns are source of truth."""

    language: SupportedLanguage = SupportedLanguage.TYPESCRIPT
    rules: tuple[FrameworkRule, ...] = cast(
        tuple[FrameworkRule, ...],
        (JestRule(), VitestRule()),
    )

    def detect(self, ctx: DetectionContext) -> list[str]:
        signals = {rule.name: rule.signals(ctx) for rule in self.rules}

        pattern_hits = [rule.name for rule in self.rules if signals[rule.name].pattern]
        if pattern_hits:
            return pattern_hits

        return [rule.name for rule in self.rules if signals[rule.name].manifest]
