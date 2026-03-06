# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""TypeScript/JavaScript-specific discovery miners."""

from specleft.discovery.miners.typescript.jsdoc import extract_jsdoc_items
from specleft.discovery.miners.typescript.routes import TypeScriptRouteMiner
from specleft.discovery.miners.typescript.tests import TypeScriptTestMiner

__all__ = ["TypeScriptRouteMiner", "TypeScriptTestMiner", "extract_jsdoc_items"]
