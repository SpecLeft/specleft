"""SpecLeft Spec Differ - detects changes between specs and tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from specleft.schema import ScenarioSpec


@dataclass(frozen=True)
class StepDiff:
    """Represents a difference in steps."""

    type: Literal["added", "removed", "modified"]
    step_description: str
    new_index: int | None = None
    old_index: int | None = None


class SpecDiffer:
    """Compares spec steps with test steps."""

    def diff_scenario(
        self, spec: ScenarioSpec, test_steps: Sequence[str]
    ) -> list[StepDiff]:
        """Find differences between spec steps and test steps."""
        diffs: list[StepDiff] = []
        spec_steps = [
            f"{step.type.value.capitalize()} {step.description}" for step in spec.steps
        ]
        test_steps_list = list(test_steps)

        min_len = min(len(spec_steps), len(test_steps_list))
        for index in range(min_len):
            spec_step = spec_steps[index]
            test_step = test_steps_list[index]
            if spec_step == test_step:
                continue
            spec_in_tests = spec_step in test_steps_list
            test_in_specs = test_step in spec_steps
            if not spec_in_tests and not test_in_specs:
                diffs.append(
                    StepDiff(
                        type="modified",
                        step_description=spec_step,
                        new_index=index,
                        old_index=index,
                    )
                )
                continue
            if test_in_specs:
                diffs.append(
                    StepDiff(
                        type="removed", step_description=test_step, old_index=index
                    )
                )
            if spec_in_tests:
                diffs.append(
                    StepDiff(type="added", step_description=spec_step, new_index=index)
                )

        if len(test_steps_list) > min_len:
            for index in range(min_len, len(test_steps_list)):
                diffs.append(
                    StepDiff(
                        type="removed",
                        step_description=test_steps_list[index],
                        old_index=index,
                    )
                )

        if len(spec_steps) > min_len:
            for index in range(min_len, len(spec_steps)):
                diffs.append(
                    StepDiff(
                        type="added",
                        step_description=spec_steps[index],
                        new_index=index,
                    )
                )

        return diffs
