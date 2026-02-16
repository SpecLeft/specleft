# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Command group modules for the SpecLeft CLI."""

from __future__ import annotations

from specleft.commands.contract import contract
from specleft.commands.coverage import coverage
from specleft.commands.doctor import doctor
from specleft.commands.enforce import enforce
from specleft.commands.features import features
from specleft.commands.guide import guide
from specleft.commands.init import init
from specleft.commands.license import license_group
from specleft.commands.mcp import mcp
from specleft.commands.next import next_command
from specleft.commands.plan import plan
from specleft.commands.skill import skill_group
from specleft.commands.status import status
from specleft.commands.test import test

__all__ = [
    "contract",
    "coverage",
    "doctor",
    "enforce",
    "features",
    "guide",
    "init",
    "license_group",
    "mcp",
    "next_command",
    "plan",
    "skill_group",
    "status",
    "test",
]
