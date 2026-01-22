"""Tests for specleft.utils.text module."""

from __future__ import annotations

from specleft.utils.text import to_snake_case


class TestToSnakeCase:
    """Tests for to_snake_case helper function."""

    def test_simple_hyphenated(self) -> None:
        """Test converting hyphenated string."""
        assert to_snake_case("login-success") == "login_success"

    def test_already_snake_case(self) -> None:
        """Test string that's already snake_case."""
        assert to_snake_case("login_success") == "login_success"

    def test_camel_case(self) -> None:
        """Test converting camelCase."""
        assert to_snake_case("loginSuccess") == "login_success"

    def test_with_spaces(self) -> None:
        """Test converting string with spaces."""
        assert to_snake_case("login success") == "login_success"

    def test_mixed_format(self) -> None:
        """Test converting mixed format string."""
        assert to_snake_case("Login-Success Test") == "login_success_test"

    def test_multiple_hyphens(self) -> None:
        """Test handling multiple consecutive hyphens."""
        assert to_snake_case("login--success") == "login_success"
