# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Default miner registry for discovery pipeline wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from specleft.discovery.miners.python.tests import PythonTestMiner
from specleft.discovery.miners.shared.docstrings import DocstringMiner
from specleft.discovery.miners.shared.readme import ReadmeOverviewMiner
from specleft.discovery.miners.typescript.tests import TypeScriptTestMiner

if TYPE_CHECKING:
    from specleft.discovery.pipeline import BaseMiner


def default_miners() -> list[BaseMiner]:
    """Return default miners in deterministic execution order."""
    return [
        ReadmeOverviewMiner(),
        PythonTestMiner(),
        TypeScriptTestMiner(),
        DocstringMiner(),
    ]
