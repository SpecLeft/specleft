# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for discovery framework detection."""

from __future__ import annotations

from pathlib import Path

from specleft.discovery.file_index import FileIndex
from specleft.discovery.framework_detector import FrameworkDetector
from specleft.discovery.models import SupportedLanguage


def test_framework_detector_detects_pytest_from_pyproject_and_patterns(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text("""
[tool.pytest.ini_options]
addopts = ["-q"]
""".strip())
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text(
        "def test_ok() -> None:\n    assert True\n"
    )

    index = FileIndex(tmp_path)
    frameworks = FrameworkDetector().detect(tmp_path, index)

    assert frameworks == {SupportedLanguage.PYTHON: ["pytest"]}


def test_framework_detector_returns_unknown_for_pytest_manifest_without_tests(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text("""
[tool.pytest.ini_options]
addopts = ["-q"]
""".strip())
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "module.py").write_text("def value() -> int:\n    return 1\n")

    index = FileIndex(tmp_path)
    frameworks = FrameworkDetector().detect(tmp_path, index)

    assert frameworks == {SupportedLanguage.PYTHON: ["unknown"]}


def test_framework_detector_detects_jest_and_vitest_by_patterns(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.json").write_text(
        '{"devDependencies": {"jest": "^29.0.0", "vitest": "^1.0.0"}}'
    )
    (tmp_path / "jest.config.ts").write_text("export default {}\n")
    (tmp_path / "vite.config.ts").write_text("export default {}\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "math.test.ts").write_text("describe('x', () => {})\n")

    index = FileIndex(tmp_path)
    frameworks = FrameworkDetector().detect(tmp_path, index)

    assert frameworks == {SupportedLanguage.TYPESCRIPT: ["jest", "vitest"]}


def test_framework_detector_detects_specleft_repo_pytest_only() -> None:
    root = Path(__file__).resolve().parents[2]
    index = FileIndex(root)

    frameworks = FrameworkDetector().detect(root, index)

    assert frameworks == {SupportedLanguage.PYTHON: ["pytest"]}


def test_framework_detector_supports_injected_policies(tmp_path: Path) -> None:
    class _CustomPolicy:
        language = SupportedLanguage.PYTHON

        def detect(self, ctx: object) -> list[str]:
            _ = ctx
            return ["custom-framework"]

    index = FileIndex(tmp_path)
    detector = FrameworkDetector(policies=(_CustomPolicy(),))

    frameworks = detector.detect(tmp_path, index)

    assert frameworks == {SupportedLanguage.PYTHON: ["custom-framework"]}
