# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared miners used by multiple discovery workflows."""

from __future__ import annotations

__all__ = ["DocstringMiner", "ReadmeOverviewMiner"]


def __getattr__(name: str) -> object:
    if name == "DocstringMiner":
        from specleft.discovery.miners.shared.docstrings import DocstringMiner

        return DocstringMiner
    if name == "ReadmeOverviewMiner":
        from specleft.discovery.miners.shared.readme import ReadmeOverviewMiner

        return ReadmeOverviewMiner
    raise AttributeError(name)
