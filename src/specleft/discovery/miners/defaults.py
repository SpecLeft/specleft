# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Default miner registry for discovery pipeline wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from specleft.discovery.miners.shared import DocstringMiner, ReadmeOverviewMiner

if TYPE_CHECKING:
    from specleft.discovery.pipeline import BaseMiner


def default_miners() -> list[BaseMiner]:
    """Return default miners in deterministic execution order."""
    return [ReadmeOverviewMiner(), DocstringMiner()]
