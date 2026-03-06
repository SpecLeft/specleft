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
    """Return languages whose file ratio exceeds the given threshold."""
    total_files = file_index.total_files
    if total_files == 0:
        return []

    detected: list[SupportedLanguage] = []
    for language in SupportedLanguage:
        language_files = file_index.files_by_language(language)
        ratio = len(language_files) / total_files
        if ratio >= threshold:
            detected.append(language)
    return detected
