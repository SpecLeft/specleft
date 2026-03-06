# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Language detection helpers over a prebuilt file index."""

from __future__ import annotations

from specleft.discovery.file_index import FileIndex
from specleft.discovery.models import SupportedLanguage


def detect_project_languages(
    file_index: FileIndex,
    threshold: float = 0.01,
) -> list[SupportedLanguage]:
    """Return languages whose supported-file ratio exceeds the given threshold."""
    supported_total = sum(
        len(file_index.files_by_language(language)) for language in SupportedLanguage
    )
    if supported_total == 0:
        return []

    detected: list[SupportedLanguage] = []
    for language in SupportedLanguage:
        language_files = file_index.files_by_language(language)
        ratio = len(language_files) / supported_total
        if ratio >= threshold:
            detected.append(language)
    return detected
