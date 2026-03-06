# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Language-agnostic README overview miner."""

from __future__ import annotations

import uuid
from pathlib import Path

from specleft.discovery.context import MinerContext
from specleft.discovery.models import (
    DiscoveredItem,
    DocstringMeta,
    ItemKind,
    MinerResult,
    SupportedLanguage,
)


class ReadmeOverviewMiner:
    """Extract a single high-level project overview from README content."""

    miner_id = uuid.UUID("2f87e7a5-a362-4adc-a005-84457b6abc04")
    name = "readme_overview"
    languages: frozenset[SupportedLanguage] = frozenset()

    def mine(self, ctx: MinerContext) -> MinerResult:
        readme_paths = (
            Path("README.md"),
            Path("README.rst"),
            Path("README.txt"),
        )

        items: list[DiscoveredItem] = []
        for rel_path in readme_paths:
            abs_path = ctx.root / rel_path
            if not abs_path.is_file():
                continue

            try:
                raw_text = abs_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            first_line = next(
                (line.strip() for line in raw_text.splitlines() if line.strip()),
                "Project overview",
            )
            item = DiscoveredItem(
                kind=ItemKind.DOCSTRING,
                name="project_overview",
                file_path=rel_path,
                line_number=1,
                language=None,
                raw_text=first_line,
                metadata=DocstringMeta(
                    target_kind="module",
                    target_name="README",
                    text=first_line,
                ).model_dump(),
                confidence=0.3,
            )
            items.append(item)
            break

        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            duration_ms=0,
        )
