# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Static guide content for specleft guide command."""

from __future__ import annotations

from specleft import __version__

GUIDE_VERSION = "1.0"

TASK_MAPPINGS = [
    {
        "task": "Bug fix / regression",
        "workflow": "direct_test",
        "action": "Write regression test, fix code",
    },
    {
        "task": "New feature",
        "workflow": "spec_first",
        "action": "Create feature spec, then skeleton",
    },
    {
        "task": "New scenario",
        "workflow": "spec_first",
        "action": "Append scenario to existing feature",
    },
    {
        "task": "Refactor / cleanup",
        "workflow": "direct_test",
        "action": "Run existing tests, refactor safely",
    },
    {
        "task": "Chore / config",
        "workflow": "direct_test",
        "action": "Make change, verify tests pass",
    },
]

WORKFLOWS = {
    "direct_test": {
        "description": "Write tests and code directly without spec changes",
        "use_when": [
            "Bug fix or regression",
            "Refactor or cleanup",
            "Chore or config change",
        ],
    },
    "spec_first": {
        "description": "Create or update specs before implementation",
        "use_when": [
            "New feature",
            "New scenario for existing feature",
        ],
    },
}

COMMANDS = {
    "status": {
        "usage": "specleft status [--format json]",
        "description": "Check what's implemented vs skipped",
    },
    "next": {
        "usage": "specleft next [--format json]",
        "description": "Get next unimplemented scenario",
    },
    "coverage": {
        "usage": "specleft coverage [--format json]",
        "description": "View coverage metrics",
    },
    "features_add": {
        "usage": "specleft features add",
        "description": "Add a new feature file",
    },
    "features_add_scenario": {
        "usage": "specleft features add-scenario",
        "description": "Add a scenario to an existing feature",
    },
    "test_skeleton": {
        "usage": "specleft test skeleton [--dry-run]",
        "description": "Generate test scaffolding from specs",
    },
    "test_stub": {
        "usage": "specleft test stub [--dry-run]",
        "description": "Generate test stubs from specs",
    },
    "features_validate": {
        "usage": "specleft features validate [--format json] ",
        "description": "Validate feature spec syntax",
    },
}

QUICK_START = [
    "specleft status --format json",
    "specleft next --format json",
    "specleft test skeleton --dry-run",
]

NOTES = [
    "All commands support --format json for programmatic use",
    "Use --dry-run where available to preview changes",
    "Skeleton tests are generated in skipped state by default",
]

COMMAND_ORDER = [
    "status",
    "next",
    "coverage",
    "features_add",
    "features_add_scenario",
    "test_skeleton",
    "test_stub",
    "features_validate",
]


def get_guide_json() -> dict[str, object]:
    """Return guide content as a JSON-serializable dict."""
    return {
        "guide_version": GUIDE_VERSION,
        "specleft_version": __version__,
        "workflows": WORKFLOWS,
        "task_mapping": TASK_MAPPINGS,
        "commands": COMMANDS,
        "quick_start": QUICK_START,
        "notes": NOTES,
    }
