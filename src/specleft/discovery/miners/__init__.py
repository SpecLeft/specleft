# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Discovery miner implementations."""

from specleft.discovery.miners.defaults import default_miners
from specleft.discovery.miners.python.routes import PythonRouteMiner
from specleft.discovery.miners.python.tests import PythonTestMiner
from specleft.discovery.miners.shared.docstrings import DocstringMiner
from specleft.discovery.miners.shared.readme import ReadmeOverviewMiner
from specleft.discovery.miners.typescript.routes import TypeScriptRouteMiner
from specleft.discovery.miners.typescript.tests import TypeScriptTestMiner

__all__ = [
    "DocstringMiner",
    "PythonRouteMiner",
    "PythonTestMiner",
    "ReadmeOverviewMiner",
    "TypeScriptRouteMiner",
    "TypeScriptTestMiner",
    "default_miners",
]
