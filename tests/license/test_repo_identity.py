"""Tests for repository identity detection."""

from __future__ import annotations

from specleft.license.repo_identity import RepoIdentity, parse_remote_url


class TestRepoIdentity:
    """Tests for RepoIdentity class."""

    def test_canonical_format(self) -> None:
        repo = RepoIdentity(owner="owner", name="repo")
        assert repo.canonical == "owner/repo"

    def test_matches_exact(self) -> None:
        """owner/repo matches owner/repo."""
        repo = RepoIdentity(owner="owner", name="repo")
        assert repo.matches("owner/repo") is True

    def test_matches_exact_case_insensitive(self) -> None:
        """Owner/Repo matches owner/repo."""
        repo = RepoIdentity(owner="Owner", name="Repo")
        assert repo.matches("owner/repo") is True

        repo2 = RepoIdentity(owner="owner", name="repo")
        assert repo2.matches("Owner/Repo") is True

    def test_matches_wildcard(self) -> None:
        """owner/* matches owner/anything."""
        repo = RepoIdentity(owner="owner", name="any-repo")
        assert repo.matches("owner/*") is True

    def test_matches_wildcard_case_insensitive(self) -> None:
        """Owner/* matches owner/repo."""
        repo = RepoIdentity(owner="owner", name="repo")
        assert repo.matches("Owner/*") is True

        repo2 = RepoIdentity(owner="Owner", name="repo")
        assert repo2.matches("owner/*") is True

    def test_no_match_different_owner(self) -> None:
        """owner/* does not match other/repo."""
        repo = RepoIdentity(owner="other", name="repo")
        assert repo.matches("owner/*") is False

    def test_no_match_different_repo(self) -> None:
        """owner/repo does not match owner/other."""
        repo = RepoIdentity(owner="owner", name="repo")
        assert repo.matches("owner/other") is False


class TestParseRemoteUrl:
    """Tests for parse_remote_url function."""

    def test_parse_ssh_github(self) -> None:
        """git@github.com:owner/repo.git"""
        result = parse_remote_url("git@github.com:owner/repo.git")
        assert result is not None
        assert result.owner == "owner"
        assert result.name == "repo"

    def test_parse_ssh_gitlab(self) -> None:
        """git@gitlab.com:owner/repo.git"""
        result = parse_remote_url("git@gitlab.com:owner/repo.git")
        assert result is not None
        assert result.owner == "owner"
        assert result.name == "repo"

    def test_parse_https_github(self) -> None:
        """https://github.com/owner/repo"""
        result = parse_remote_url("https://github.com/owner/repo")
        assert result is not None
        assert result.owner == "owner"
        assert result.name == "repo"

    def test_parse_https_with_git(self) -> None:
        """https://github.com/owner/repo.git"""
        result = parse_remote_url("https://github.com/owner/repo.git")
        assert result is not None
        assert result.owner == "owner"
        assert result.name == "repo"

    def test_parse_no_git_suffix(self) -> None:
        """Handles missing .git suffix."""
        result = parse_remote_url("git@github.com:owner/repo")
        assert result is not None
        assert result.owner == "owner"
        assert result.name == "repo"

    def test_parse_invalid_url(self) -> None:
        """Returns None for malformed URLs."""
        assert parse_remote_url("not-a-valid-url") is None
        assert parse_remote_url("") is None
        assert parse_remote_url("ftp://example.com/repo") is None

    def test_parse_http_url(self) -> None:
        """http:// URLs are supported."""
        result = parse_remote_url("http://github.com/owner/repo")
        assert result is not None
        assert result.owner == "owner"
        assert result.name == "repo"
