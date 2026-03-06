# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Docstring/JSDoc miner orchestration."""

from __future__ import annotations

import time
import uuid

from specleft.discovery.context import MinerContext
from specleft.discovery.miners.python.docstrings import extract_python_items
from specleft.discovery.miners.shared.common import (
    candidate_source_files,
    elapsed_ms,
    is_test_file,
)
from specleft.discovery.miners.typescript.jsdoc import extract_jsdoc_items
from specleft.discovery.models import DiscoveredItem, MinerResult, SupportedLanguage


class DocstringMiner:
    """Extract Python docstrings and TypeScript/JavaScript JSDoc comments."""

    miner_id = uuid.UUID("dcc2e631-67e7-4af7-b8ba-ca3397ccae0b")
    name = "docstrings"
    languages = frozenset(
        {
            SupportedLanguage.PYTHON,
            SupportedLanguage.TYPESCRIPT,
            SupportedLanguage.JAVASCRIPT,
        }
    )

    def mine(self, ctx: MinerContext) -> MinerResult:
        started = time.perf_counter()
        items: list[DiscoveredItem] = []

        for rel_path in candidate_source_files(ctx):
            if is_test_file(rel_path):
                continue

            abs_path = ctx.root / rel_path
            parsed = ctx.registry.parse(abs_path)
            if parsed is None:
                continue

            try:
                source_bytes = abs_path.read_bytes()
            except OSError:
                continue

            root_node, language = parsed
            if language == SupportedLanguage.PYTHON:
                items.extend(extract_python_items(root_node, source_bytes, rel_path))
            elif language in (
                SupportedLanguage.TYPESCRIPT,
                SupportedLanguage.JAVASCRIPT,
            ):
                items.extend(
                    extract_jsdoc_items(root_node, source_bytes, rel_path, language)
                )

        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            duration_ms=elapsed_ms(started),
        )
