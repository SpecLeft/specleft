"""Utilities for discovering specleft-decorated tests."""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestDiscoveryResult:
    """Result of pytest test discovery."""

    total_tests: int
    specleft_tests: int
    specleft_scenario_ids: frozenset[str]
    error: str | None = None


@dataclass(frozen=True)
class FileSpecleftResult:
    """Result of finding @specleft tests in a file."""

    count: int
    scenario_ids: frozenset[str]


def extract_specleft_scenario_id(decorator: ast.expr) -> str | None:
    """Extract scenario_id from a @specleft(...) decorator."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if (
            isinstance(func, ast.Name)
            and func.id == "specleft"
            or isinstance(func, ast.Attribute)
            and func.attr == "specleft"
        ):
            return get_scenario_id_from_call(decorator)
    return None


def get_scenario_id_from_call(call: ast.Call) -> str | None:
    """Extract scenario_id from a function call's arguments."""
    for keyword in call.keywords:
        if keyword.arg == "scenario_id" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        return str(call.args[1].value)
    return None


def extract_skip_flag(decorator: ast.expr) -> bool:
    if not isinstance(decorator, ast.Call):
        return False
    for keyword in decorator.keywords:
        if keyword.arg == "skip" and isinstance(keyword.value, ast.Constant):
            return bool(keyword.value.value)
    return False


def extract_specleft_calls(tree: ast.AST) -> dict[str, dict[str, object]]:
    scenario_map: dict[str, dict[str, object]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            scenario_id = extract_specleft_scenario_id(decorator)
            if scenario_id is None:
                continue
            scenario_map[scenario_id] = {
                "function": node.name,
                "skip": extract_skip_flag(decorator),
            }
    return scenario_map


def find_specleft_tests_in_file(file_path: Path) -> FileSpecleftResult:
    """Parse a Python file to find @specleft decorated test functions."""
    content = file_path.read_text()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return FileSpecleftResult(count=0, scenario_ids=frozenset())

    count = 0
    scenario_ids: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                scenario_id = extract_specleft_scenario_id(decorator)
                if scenario_id is not None:
                    count += 1
                    scenario_ids.add(scenario_id)

    return FileSpecleftResult(count=count, scenario_ids=frozenset(scenario_ids))


def discover_pytest_tests(tests_dir: str = "tests") -> TestDiscoveryResult:
    """Discover pytest tests and identify @specleft-decorated tests."""
    tests_path = Path(tests_dir)
    if not tests_path.exists():
        return TestDiscoveryResult(
            total_tests=0,
            specleft_tests=0,
            specleft_scenario_ids=frozenset(),
            error=f"Tests directory not found: {tests_dir}",
        )

    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q", tests_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout
    except FileNotFoundError:
        return TestDiscoveryResult(
            total_tests=0,
            specleft_tests=0,
            specleft_scenario_ids=frozenset(),
            error="pytest not found. Install pytest to discover tests.",
        )
    except subprocess.TimeoutExpired:
        return TestDiscoveryResult(
            total_tests=0,
            specleft_tests=0,
            specleft_scenario_ids=frozenset(),
            error="Test discovery timed out.",
        )

    total_tests = 0
    for line in output.strip().split("\n"):
        line = line.strip()
        if "::" in line and not line.startswith("<"):
            total_tests += 1
        elif "test" in line.lower() and "collected" in line.lower():
            match = re.search(r"(\d+)\s+tests?\s+collected", line, re.IGNORECASE)
            if match:
                total_tests = int(match.group(1))
                break

    specleft_tests = 0
    specleft_scenario_ids: set[str] = set()

    for py_file in tests_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        try:
            file_results = find_specleft_tests_in_file(py_file)
            specleft_tests += file_results.count
            specleft_scenario_ids.update(file_results.scenario_ids)
        except Exception:
            continue

    return TestDiscoveryResult(
        total_tests=total_tests,
        specleft_tests=specleft_tests,
        specleft_scenario_ids=frozenset(specleft_scenario_ids),
    )
