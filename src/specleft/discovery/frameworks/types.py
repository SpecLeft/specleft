# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared types for framework detection rules and policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from specleft.discovery.models import SupportedLanguage

if TYPE_CHECKING:
    from specleft.discovery.framework_detector import DetectionContext


@dataclass(frozen=True)
class FrameworkSignals:
    """Signals collected for one framework candidate."""

    manifest: bool = False
    pattern: bool = False
    confirmed: bool = False


class FrameworkRule(Protocol):
    """Rule contract for one framework within one language."""

    name: str
    language: SupportedLanguage

    def signals(self, ctx: DetectionContext) -> FrameworkSignals: ...


class LanguagePolicy(Protocol):
    """Policy contract for resolving frameworks of a language."""

    language: SupportedLanguage

    def detect(self, ctx: DetectionContext) -> list[str]: ...
