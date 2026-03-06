# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Discovery miner implementations."""

from specleft.discovery.miners.defaults import default_miners
from specleft.discovery.miners.shared import DocstringMiner, ReadmeOverviewMiner

__all__ = ["DocstringMiner", "ReadmeOverviewMiner", "default_miners"]
