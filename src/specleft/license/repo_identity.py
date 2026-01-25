"""Repository identity detection from git remotes.

Parses git remote URLs to extract owner/repo information
for license binding verification.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass
class RepoIdentity:
    """Repository identity extracted from git remote."""

    owner: str
    name: str

    @property
    def canonical(self) -> str:
        """Get canonical owner/repo string."""
        return f"{self.owner}/{self.name}"

    def matches(self, pattern: str) -> bool:
        """Check if this repo matches a license pattern.

        Supports exact match (owner/repo) or wildcard (owner/*).

        Args:
            pattern: License pattern like "owner/repo" or "owner/*"

        Returns:
            True if pattern matches this repository
        """
        if pattern.endswith("/*"):
            # Wildcard: match owner only
            return self.owner.lower() == pattern[:-2].lower()
        # Exact match
        return self.canonical.lower() == pattern.lower()


def detect_repo_identity() -> RepoIdentity | None:
    """Detect repository identity from git remote 'origin'.

    Returns:
        RepoIdentity if detection succeeded, None otherwise
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return parse_remote_url(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def parse_remote_url(url: str) -> RepoIdentity | None:
    """Parse a git remote URL to extract owner and repo name.

    Supports both SSH and HTTPS formats:
    - git@github.com:owner/repo.git
    - git@gitlab.com:owner/repo.git
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git

    Args:
        url: Git remote URL

    Returns:
        RepoIdentity if parsing succeeded, None otherwise
    """
    patterns = [
        # SSH format: git@host:owner/repo.git
        r"git@[^:]+:(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?$",
        # HTTPS format: https://host/owner/repo.git
        r"https?://[^/]+/(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?$",
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return RepoIdentity(
                owner=match.group("owner"),
                name=match.group("name"),
            )
    return None
