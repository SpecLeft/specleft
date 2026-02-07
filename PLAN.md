# Plan: `specleft guide` — Workflow Guide Command

Issue: https://github.com/SpecLeft/specleft/issues/66
Milestone: v0.2.0 - Agent Feedback
Complexity: Low (3-5 hours)

## Architecture Decision

The issue suggests `src/specleft/cli/guide.py` plus `src/specleft/guide/content.py`. The project
keeps CLI commands in `src/specleft/commands/`, so we will follow the existing pattern:

- Guide content (static data): `src/specleft/commands/guide_content.py`
- CLI command: `src/specleft/commands/guide.py`
- Tests: `tests/commands/test_guide.py`

## Implementation Steps

### Step 1: Create PLAN.md and PROGRESS.md
- Populate `PLAN.md` with this plan.
- Populate `PROGRESS.md` with a tracking table for this issue.

### Step 2: Create guide content module
File: `src/specleft/commands/guide_content.py`

- `GUIDE_VERSION = "1.0"`
- `TASK_MAPPINGS` list of `{task, workflow, action}` mappings
- `WORKFLOWS` dict for `direct_test` and `spec_first`
- `COMMANDS` dict with usage and descriptions for key commands
- `QUICK_START` and `NOTES` lists
- `get_guide_json()` returns the full payload with `specleft_version`

### Step 3: Create guide CLI command
File: `src/specleft/commands/guide.py`

- `@click.command("guide")` with `--format` (`table`/`json`, default `table`)
- JSON output from `get_guide_json()`
- Table output matching the issue's sample format
- Exit code 0 on success
- Static content only (no file I/O or project inspection)

### Step 4: Register command
- Add `guide` import/export in `src/specleft/commands/__init__.py`
- Add `cli.add_command(guide)` in `src/specleft/cli/main.py`

### Step 5: Write tests
File: `tests/commands/test_guide.py`

- Table output contains expected headings and workflow names
- JSON output is valid and includes required keys
- Workflows contain required fields
- Task mappings include required fields and valid workflow refs
- Commands include usage/description
- `guide_version` and `specleft_version` present
- Exit code is 0

### Step 6: Update CLI reference docs
File: `docs/cli-reference.md`

- Add `specleft guide` section with usage and options

### Step 7: Run tests and lint
- `pytest tests/commands/test_guide.py -v`
- `pytest`
- `make lint`

### Step 8: Update PROGRESS.md
- Mark steps completed with summary and timestamp

## Success Criteria

- `specleft guide` displays table format by default
- `specleft guide --format json` outputs valid JSON
- JSON includes `guide_version` and `specleft_version`
- All task types map to a workflow
- All key commands are documented
- Exit code is `0` on success
- Guide content is static (no file I/O, no project inspection)
- Command completes in <100ms
- Tests and lint pass
