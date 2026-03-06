# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Language-agnostic git history miner."""

from __future__ import annotations

import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from specleft.discovery.context import MinerContext
from specleft.discovery.miners.shared.common import elapsed_ms
from specleft.discovery.models import (
    DiscoveredItem,
    GitCommitMeta,
    ItemKind,
    MinerErrorKind,
    MinerResult,
    SupportedLanguage,
)

_SEPARATOR = "---END---"
_NOISE_CONVENTIONAL_TYPES = frozenset({"chore", "ci", "build", "docs", "style", "test"})
_SOURCE_SUFFIXES = frozenset({".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"})
_CONVENTIONAL_PREFIX = re.compile(r"^(?P<kind>[a-z]+)(?:\([^)]+\))?(?:!)?:\s*")


@dataclass(frozen=True)
class _CommitRecord:
    commit_hash: str
    subject: str
    body: str | None
    changed_files: list[str]


class GitHistoryMiner:
    """Extract discovery signals from recent git commit history."""

    miner_id = uuid.UUID("f1c93075-4e3c-44b8-bef6-9c0bc25b6c42")
    name = "git_history"
    languages: frozenset[SupportedLanguage] = frozenset()

    def mine(self, ctx: MinerContext) -> MinerResult:
        started = time.perf_counter()
        process = _run_git_log(ctx.root, ctx.config.max_git_commits)
        if process is None:
            return _git_error_result(
                miner_id=self.miner_id,
                miner_name=self.name,
                error="git executable not found",
                duration_ms=elapsed_ms(started),
            )

        if process.returncode != 0:
            error = process.stderr.strip() or "not a git repository"
            return _git_error_result(
                miner_id=self.miner_id,
                miner_name=self.name,
                error=error,
                duration_ms=elapsed_ms(started),
            )

        items = _items_from_log(process.stdout)
        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=items,
            duration_ms=elapsed_ms(started),
        )


def _run_git_log(
    root: Path, max_commits: int
) -> subprocess.CompletedProcess[str] | None:
    command = [
        "git",
        "-C",
        str(root),
        "log",
        "--no-merges",
        "--format=%H%n%s%n%b%n---END---",
        "--name-only",
        "-n",
        str(max_commits),
    ]
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None


def _items_from_log(log_output: str) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []
    for record in _parse_records(log_output):
        conventional_type = _conventional_type(record.subject)
        if conventional_type in _NOISE_CONVENTIONAL_TYPES:
            continue

        source_files = [path for path in record.changed_files if _is_source_path(path)]
        if not source_files:
            continue

        metadata = GitCommitMeta(
            commit_hash=record.commit_hash[:7],
            subject=record.subject,
            body=record.body,
            changed_files=source_files,
            conventional_type=conventional_type,
            file_prefixes=_collect_file_prefixes(source_files),
        )
        items.append(
            DiscoveredItem(
                kind=ItemKind.GIT_COMMIT,
                name=record.subject,
                file_path=None,
                line_number=None,
                language=None,
                raw_text=record.body,
                metadata=metadata.model_dump(),
                confidence=0.5,
            )
        )
    return items


def _parse_records(log_output: str) -> list[_CommitRecord]:
    lines = log_output.splitlines()
    records: list[_CommitRecord] = []
    cursor = 0
    total_lines = len(lines)

    while cursor < total_lines:
        while cursor < total_lines and not _is_full_hash(lines[cursor]):
            cursor += 1
        if cursor >= total_lines:
            break

        commit_hash = lines[cursor].strip()
        cursor += 1
        if cursor >= total_lines:
            break

        subject = lines[cursor].strip()
        cursor += 1

        body_lines: list[str] = []
        while cursor < total_lines and lines[cursor].strip() != _SEPARATOR:
            body_lines.append(lines[cursor].rstrip())
            cursor += 1
        if cursor < total_lines and lines[cursor].strip() == _SEPARATOR:
            cursor += 1

        changed_files: list[str] = []
        while cursor < total_lines and not _is_full_hash(lines[cursor]):
            file_path = lines[cursor].strip()
            if file_path:
                changed_files.append(file_path)
            cursor += 1

        body = "\n".join(body_lines).strip() or None
        records.append(
            _CommitRecord(
                commit_hash=commit_hash,
                subject=subject,
                body=body,
                changed_files=changed_files,
            )
        )

    return records


def _is_full_hash(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) != 40:
        return False
    return all(character in "0123456789abcdef" for character in stripped.lower())


def _conventional_type(subject: str) -> str | None:
    match = _CONVENTIONAL_PREFIX.match(subject.strip().lower())
    if not match:
        return None
    return match.group("kind")


def _is_source_path(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in _SOURCE_SUFFIXES


def _collect_file_prefixes(paths: list[str]) -> list[str]:
    prefixes: list[str] = []
    seen: set[str] = set()
    for path in paths:
        parent = Path(path).parent.as_posix()
        prefix = parent if parent != "." else path
        if prefix in seen:
            continue
        seen.add(prefix)
        prefixes.append(prefix)
    return prefixes


def _git_error_result(
    *,
    miner_id: uuid.UUID,
    miner_name: str,
    error: str,
    duration_ms: int,
) -> MinerResult:
    return MinerResult(
        miner_id=miner_id,
        miner_name=miner_name,
        items=[],
        error=error,
        error_kind=MinerErrorKind.NOT_INSTALLED,
        duration_ms=duration_ms,
    )
