# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for git history discovery miner."""

from __future__ import annotations

import subprocess
from pathlib import Path

import specleft.discovery.miners.shared.git_history as git_history_module
from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.file_index import FileIndex
from specleft.discovery.language_registry import LanguageRegistry
from specleft.discovery.miners.shared.git_history import GitHistoryMiner
from specleft.discovery.models import GitCommitMeta, MinerErrorKind


def _context(root: Path, *, max_git_commits: int = 200) -> MinerContext:
    return MinerContext(
        root=root,
        registry=LanguageRegistry(),
        file_index=FileIndex(root),
        frameworks={},
        config=DiscoveryConfig(max_git_commits=max_git_commits),
    )


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "specleft-tests@example.com")
    _git(repo, "config", "user.name", "SpecLeft Tests")


def _commit(
    repo: Path,
    *,
    subject: str,
    files: dict[str, str],
    body: str | None = None,
) -> str:
    for rel_path, content in files.items():
        absolute = repo / rel_path
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_text(content, encoding="utf-8")

    _git(repo, "add", *sorted(files))
    command = ["commit", "-m", subject]
    if body is not None:
        command.extend(["-m", body])
    _git(repo, *command)
    return _git(repo, "rev-parse", "--short=7", "HEAD")


def test_git_history_miner_parses_metadata_and_filters_noise(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)

    _commit(
        repo,
        subject="chore: update lockfile",
        files={"package-lock.json": '{"lockfileVersion": 3}'},
    )
    expected_hash = _commit(
        repo,
        subject="feat: add login endpoint",
        body="Implements JWT-based authentication.",
        files={
            "src/auth/login.py": "def login() -> None:\n    pass\n",
            "tests/test_login.py": "def test_login() -> None:\n    assert True\n",
        },
    )
    _commit(
        repo,
        subject="docs: update onboarding guide",
        files={"docs/onboarding.md": "# onboarding\n"},
    )

    result = GitHistoryMiner().mine(_context(repo))

    assert result.error is None
    assert result.error_kind is None
    assert len(result.items) == 1

    item = result.items[0]
    metadata = item.typed_meta()
    assert isinstance(metadata, GitCommitMeta)
    assert metadata.commit_hash == expected_hash
    assert metadata.subject == "feat: add login endpoint"
    assert metadata.body == "Implements JWT-based authentication."
    assert metadata.changed_files == ["src/auth/login.py", "tests/test_login.py"]
    assert metadata.conventional_type == "feat"
    assert metadata.file_prefixes == ["src/auth", "tests"]
    assert item.language is None
    assert item.file_path is None
    assert item.confidence == 0.5


def test_git_history_miner_uses_configured_commit_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(
        repo,
        subject="feat: initial endpoint",
        files={"src/api.py": "def endpoint() -> None:\n    pass\n"},
    )
    _commit(
        repo,
        subject="fix: tighten validation",
        files={"src/api.py": "def endpoint() -> int:\n    return 1\n"},
    )

    result = GitHistoryMiner().mine(_context(repo, max_git_commits=1))

    assert [item.name for item in result.items] == ["fix: tighten validation"]


def test_git_history_miner_excludes_merge_commits(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(
        repo,
        subject="feat: base endpoint",
        files={"src/service.py": "def base() -> None:\n    pass\n"},
    )

    _git(repo, "checkout", "-b", "feature/login")
    _commit(
        repo,
        subject="feat: add login flow",
        files={"src/login.py": "def login() -> None:\n    pass\n"},
    )

    _git(repo, "checkout", "main")
    _commit(
        repo,
        subject="fix: harden auth checks",
        files={"src/auth.py": "def auth() -> None:\n    pass\n"},
    )
    _git(repo, "merge", "--no-ff", "feature/login", "-m", "Merge feature/login")

    result = GitHistoryMiner().mine(_context(repo))

    subjects = [item.name for item in result.items]
    assert "Merge feature/login" not in subjects
    assert "feat: add login flow" in subjects
    assert "fix: harden auth checks" in subjects


def test_git_history_miner_returns_not_installed_error_for_non_repo(
    tmp_path: Path,
) -> None:
    result = GitHistoryMiner().mine(_context(tmp_path))

    assert result.items == []
    assert result.error is not None
    assert result.error_kind == MinerErrorKind.NOT_INSTALLED


def test_git_history_miner_returns_parse_error_for_malformed_log_output(
    tmp_path: Path, monkeypatch
) -> None:
    malformed_stdout = "\n".join(
        [
            "a" * 40,
            "feat: malformed stream",
            "body line without separator",
        ]
    )
    process = subprocess.CompletedProcess(
        args=["git"],
        returncode=0,
        stdout=malformed_stdout,
        stderr="",
    )

    monkeypatch.setattr(git_history_module, "_run_git_log", lambda *_: process)

    result = GitHistoryMiner().mine(_context(tmp_path))

    assert result.items == []
    assert result.error_kind == MinerErrorKind.PARSE_ERROR
    assert result.error is not None
    assert "missing '---END---' marker" in result.error
    assert "commit aaaaaaa" in result.error
