"""SpecLeft Test Revisor - updates test files based on spec changes."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from specleft.spec_differ import StepDiff


@dataclass(frozen=True)
class RevisionPlan:
    """Plan for revising a scenario's steps."""

    scenario_id: str
    additions: tuple[StepDiff, ...]
    removals: tuple[StepDiff, ...]
    modifications: tuple[StepDiff, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.additions or self.removals or self.modifications)


class TestFunctionRevisor:
    """Revises test functions based on spec diffs."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.splitlines()

    def build_revision_plan(
        self, scenario_id: str, diffs: Sequence[StepDiff]
    ) -> RevisionPlan:
        """Build a plan for revising a scenario based on diffs."""
        additions = tuple(diff for diff in diffs if diff.type == "added")
        removals = tuple(diff for diff in diffs if diff.type == "removed")
        modifications = tuple(diff for diff in diffs if diff.type == "modified")
        return RevisionPlan(
            scenario_id=scenario_id,
            additions=additions,
            removals=removals,
            modifications=modifications,
        )

    def revise_test_file(self, plan: RevisionPlan) -> str:
        """Apply revisions to a test file."""
        if not plan.has_changes:
            return self.source

        updated_lines = list(self.lines)
        scenario_range = self._find_scenario_range(updated_lines, plan.scenario_id)
        if scenario_range is None:
            return self.source

        start, end = scenario_range
        scenario_lines = updated_lines[start:end]
        step_block = self._find_step_block(scenario_lines)
        if step_block is None:
            return self.source

        step_start, step_end, indent = step_block
        step_block_lines = scenario_lines[step_start:step_end]

        for diff in sorted(
            plan.removals, key=lambda item: item.old_index or 0, reverse=True
        ):
            step_block_lines = self._skip_step(step_block_lines, diff)

        for diff in sorted(plan.modifications, key=lambda item: item.old_index or 0):
            step_block_lines = self._mark_modified(step_block_lines, diff)

        for diff in sorted(plan.additions, key=lambda item: item.new_index or 0):
            step_block_lines = self._add_step(step_block_lines, diff, indent)

        scenario_lines[step_start:step_end] = step_block_lines
        updated_lines[start:end] = scenario_lines
        return "\n".join(updated_lines)

    def _find_scenario_range(
        self, lines: list[str], scenario_id: str
    ) -> tuple[int, int] | None:
        decorator_index: int | None = None
        for index, line in enumerate(lines):
            if f'scenario_id="{scenario_id}"' in line:
                decorator_index = index
                break
        if decorator_index is None:
            return None

        function_index: int | None = None
        for index in range(decorator_index, len(lines)):
            if lines[index].lstrip().startswith("def test_"):
                function_index = index
                break
        if function_index is None:
            return None

        base_indent = len(lines[function_index]) - len(lines[function_index].lstrip())
        for index in range(function_index + 1, len(lines)):
            line = lines[index]
            if line.strip() and (len(line) - len(line.lstrip()) <= base_indent):
                return function_index, index
        return function_index, len(lines)

    def _find_step_block(
        self, scenario_lines: list[str], base_indent: int = 4
    ) -> tuple[int, int, str] | None:
        step_start: int | None = None
        step_indent = " " * base_indent
        for index, line in enumerate(scenario_lines):
            if "specleft.step(" in line:
                step_indent = line[: len(line) - len(line.lstrip())]
                step_start = index
                break
        if step_start is None:
            return None

        step_end = len(scenario_lines)
        for index in range(step_start + 1, len(scenario_lines)):
            line = scenario_lines[index]
            if line.strip() and not line.startswith(step_indent):
                step_end = index
                break
        return step_start, step_end, step_indent

    @staticmethod
    def _parse_step_description(line: str) -> str | None:
        stripped = line.strip()
        if not stripped.startswith("with specleft.step("):
            return None
        match = re.search(r"specleft\.step\(\s*\"([^\"]+)\"", stripped)
        if match:
            return match.group(1)
        match = re.search(r"specleft\.step\(\s*'([^']+)'", stripped)
        if match:
            return match.group(1)
        return None

    @classmethod
    def _skip_step(cls, block_lines: list[str], diff: StepDiff) -> list[str]:
        for index, line in enumerate(block_lines):
            description = cls._parse_step_description(line)
            if description != diff.step_description:
                continue
            if "skip=True" in line:
                return block_lines
            replacement = line.rstrip()
            if replacement.endswith(":"):
                replacement = replacement[:-1]
            replacement = f'{replacement}, skip=True, reason="Removed from spec"):\n'
            block_lines[index] = replacement
            return block_lines
        return block_lines

    @classmethod
    def _mark_modified(cls, block_lines: list[str], diff: StepDiff) -> list[str]:
        index = diff.old_index
        if index is None:
            return block_lines
        step_positions = []
        for line_index, line in enumerate(block_lines):
            if cls._parse_step_description(line) is not None:
                step_positions.append(line_index)
        if index >= len(step_positions):
            return block_lines
        line_index = step_positions[index]
        line = block_lines[line_index].rstrip()
        if line.endswith(":"):
            line = line[:-1]
        if "skip=True" not in line:
            line = f'{line}, skip=True, reason="Modified in spec")'
        block_lines[line_index] = f"{line}:\n"
        return block_lines

    @staticmethod
    def _add_step(block_lines: list[str], diff: StepDiff, indent: str) -> list[str]:
        description = diff.step_description
        addition = [
            f'{indent}with specleft.step("{description}"):',
            f"{indent}    pass  # TODO: Implement step logic",
            "",
        ]

        insertion_index = len(block_lines)
        if diff.new_index is not None:
            target_position = diff.new_index * 2
            insertion_index = min(max(target_position, 0), len(block_lines))
        updated_lines = (
            block_lines[:insertion_index] + addition + block_lines[insertion_index:]
        )
        return updated_lines
