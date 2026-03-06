# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Discovery pipeline orchestration."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Protocol

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import FileIndex
from specleft.discovery.framework_detector import FrameworkDetector
from specleft.discovery.language_detect import detect_project_languages
from specleft.discovery.language_registry import LanguageRegistry
from specleft.discovery.miners import default_miners
from specleft.discovery.models import (
    DiscoveryReport,
    MinerErrorKind,
    MinerResult,
    SupportedLanguage,
)


class BaseMiner(Protocol):
    """Protocol for pipeline miner implementations."""

    miner_id: uuid.UUID
    name: str
    languages: frozenset[SupportedLanguage]

    def mine(self, ctx: MinerContext) -> MinerResult: ...


class DiscoveryPipeline:
    """Run registered miners with shared context and failure isolation."""

    def __init__(
        self,
        root: Path,
        languages: list[SupportedLanguage] | None = None,
        *,
        config: DiscoveryConfig | None = None,
        registry: LanguageRegistry | None = None,
        file_index: FileIndex | None = None,
        framework_detector: FrameworkDetector | None = None,
    ) -> None:
        self._root = root.resolve()
        self._config = config if config is not None else DiscoveryConfig.default()
        self._registry = registry if registry is not None else LanguageRegistry()
        self._file_index = (
            file_index
            if file_index is not None
            else FileIndex(self._root, exclude_dirs=self._config.exclude_dirs)
        )
        self._framework_detector = (
            framework_detector
            if framework_detector is not None
            else FrameworkDetector()
        )
        self._miners: dict[uuid.UUID, BaseMiner] = {}
        self._languages = _normalize_languages(languages)

    def register(self, miner: BaseMiner) -> None:
        """Register a miner by unique UUID."""
        if miner.miner_id in self._miners:
            raise ValueError(f"Miner UUID already registered: {miner.miner_id}")
        self._miners[miner.miner_id] = miner

    def run(self) -> DiscoveryReport:
        """Execute all eligible miners and aggregate their results."""
        started = time.perf_counter()

        detected_languages = self._languages
        if detected_languages is None:
            detected_languages = detect_project_languages(self._file_index)

        frameworks = self._framework_detector.detect(self._root, self._file_index)
        context = MinerContext(
            root=self._root,
            registry=self._registry,
            file_index=self._file_index,
            frameworks=frameworks,
            config=self._config,
        )

        language_set = set(detected_languages)
        miner_results: list[MinerResult] = []
        errors: list[str] = []

        for miner in self._miners.values():
            if miner.languages and miner.languages.isdisjoint(language_set):
                continue

            miner_started = time.perf_counter()
            try:
                raw_result = miner.mine(context)
                miner_duration_ms = _elapsed_ms(miner_started)
                result = raw_result.model_copy(
                    update={
                        "miner_id": miner.miner_id,
                        "miner_name": miner.name,
                        "duration_ms": miner_duration_ms,
                    }
                )
            except Exception as exc:
                miner_duration_ms = _elapsed_ms(miner_started)
                error_kind = _error_kind_for(exc)
                error_message = f"{miner.name}: {exc}"
                result = MinerResult(
                    miner_id=miner.miner_id,
                    miner_name=miner.name,
                    items=[],
                    error=error_message,
                    error_kind=error_kind,
                    duration_ms=miner_duration_ms,
                )

            miner_results.append(result)
            if result.error is not None:
                errors.append(result.error)

        total_items = sum(
            len(result.items) for result in miner_results if result.error is None
        )
        duration_ms = _elapsed_ms(started)

        return DiscoveryReport(
            project_root=self._root,
            languages_detected=detected_languages,
            miner_results=miner_results,
            total_items=total_items,
            errors=errors,
            duration_ms=duration_ms,
        )


def build_default_pipeline(
    root: Path,
    languages: list[SupportedLanguage] | None = None,
    config: DiscoveryConfig | None = None,
) -> DiscoveryPipeline:
    """Build pipeline with default config and built-in miners registered."""
    resolved_config = (
        config if config is not None else DiscoveryConfig.from_pyproject(root)
    )
    pipeline = DiscoveryPipeline(root, languages=languages, config=resolved_config)

    for miner in _default_miners():
        pipeline.register(miner)

    return pipeline


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _error_kind_for(exc: Exception) -> MinerErrorKind:
    if isinstance(exc, PermissionError):
        return MinerErrorKind.PERMISSION
    if isinstance(exc, TimeoutError):
        return MinerErrorKind.TIMEOUT
    return MinerErrorKind.UNKNOWN


def _normalize_languages(
    languages: list[SupportedLanguage] | None,
) -> list[SupportedLanguage] | None:
    if languages is None:
        return None

    seen: set[SupportedLanguage] = set()
    normalized: list[SupportedLanguage] = []
    for language in languages:
        if language in seen:
            continue
        seen.add(language)
        normalized.append(language)
    return normalized


def _default_miners() -> list[BaseMiner]:
    return default_miners()
