# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared miner context built once per pipeline run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.file_index import FileIndex
from specleft.discovery.language_registry import LanguageRegistry
from specleft.discovery.models import SupportedLanguage


@dataclass(frozen=True)
class MinerContext:
    """Immutable context passed to every miner."""

    root: Path
    registry: LanguageRegistry
    file_index: FileIndex
    frameworks: dict[SupportedLanguage, list[str]]
    config: DiscoveryConfig
