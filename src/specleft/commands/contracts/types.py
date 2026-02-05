# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Contract-related data types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractCheckResult:
    """Result of a contract test check."""

    category: str
    name: str
    status: str
    message: str | None = None
