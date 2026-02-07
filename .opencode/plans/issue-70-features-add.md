# Plan: CLI Commands for Adding Features and Scenarios (Issue #70)

## Overview

Add `specleft features add` and `specleft features add-scenario` CLI commands to create features and scenarios directly from the command line, reducing manual markdown editing and improving the experience for AI agents and developers.

**Issue:** https://github.com/SpecLeft/specleft/issues/70
**Milestone:** v0.2.0 - Agent Feedback

---

## Files to Create

| File | Purpose |
|---|---|
| `src/specleft/utils/feature_writer.py` | Core logic for feature file creation and scenario appending |
| `src/specleft/utils/history.py` | Operation logging to `.specleft/history/<feature-id>.json` |
| `tests/commands/test_features_add.py` | Tests for both commands and utility functions |

## Files to Modify

| File | Change |
|---|---|
| `src/specleft/commands/features.py` | Add `add` and `add-scenario` subcommands |
| `docs/cli-reference.md` | Document new commands |
| `PROGRESS.md` | Track implementation progress |

## Dependencies

No new dependencies. Uses existing `python-slugify>=8.0.0`.

---

## Phase 1: Core Utility Module — `feature_writer.py`

**Status:** Pending

### Data Classes

```python
@dataclass
class FeatureAddResult:
    success: bool
    file_path: Path
    markdown_content: str
    error: str | None = None

@dataclass
class ScenarioAddResult:
    success: bool
    file_path: Path
    scenario_id: str
    markdown_diff: str      # The scenario block appended
    test_stub: str | None   # Generated stub if steps present
    error: str | None = None
```

### Functions

- **`generate_scenario_id(title: str) -> str`** — `slugify(title, lowercase=True)`
- **`validate_feature_id(feature_id: str) -> None`** — Validates `^[a-z0-9-]+$`, raises `ValueError`
- **`validate_scenario_id(scenario_id: str) -> None`** — Same validation
- **`validate_step_keywords(steps: list[str]) -> list[str]`** — Returns warning strings for steps not starting with Given/When/Then/And/But
- **`create_feature_file(...) -> FeatureAddResult`** — Creates `features/feature-{id}.md`. Errors if exists. Auto-creates directory.
- **`add_scenario_to_feature(...) -> ScenarioAddResult`** — Appends scenario to feature file via tag window.

### Tag Window Behavior

New feature files include `<!-- specleft:scenario-add -->` markers:

```markdown
## Scenarios

<!-- specleft:scenario-add -->
<!-- specleft:scenario-add -->
```

When appending:
- If tag window exists: insert before closing `<!-- specleft:scenario-add -->` tag
- If no tag window: insert one at end of `## Scenarios` section, wrapping only new scenarios

### Markdown Format

Matches existing `SpecParser._parse_feature_markdown()` expectations:

```markdown
# Feature: User Authentication
priority: critical

Optional description paragraph.

## Scenarios

<!-- specleft:scenario-add -->
### Scenario: User logs in successfully
priority: high
tags: smoke, auth

- **Given** a registered user exists
- **When** they submit valid credentials
- **Then** they are logged in
<!-- specleft:scenario-add -->
```

---

## Phase 2: History Logging — `history.py`

**Status:** Pending

### Functions

- **`log_feature_event(feature_id, action, details)`** — Appends entry to `.specleft/history/<feature-id>.json`
- **`load_feature_history(feature_id) -> list[dict]`** — Reads history

### JSON Entry Schema

```json
{
  "timestamp": "2026-02-06T12:00:00",
  "action": "feature_created",
  "feature_id": "user-auth",
  "details": { "title": "User Authentication", "priority": "critical" }
}
```

Auto-creates `.specleft/history/` directory.

---

## Phase 3: CLI Commands — `features.py`

**Status:** Pending

### `specleft features add`

| Option | Required | Description |
|---|---|---|
| `--id` | Yes* | Feature ID (`[a-z0-9-]+`). Filename: `feature-{id}.md` |
| `--title` | Yes* | Feature title for `# Feature:` header |
| `--priority` | No (default: medium) | critical/high/medium/low |
| `--description` | No | Description paragraph |
| `--dir` | No (default: `features`) | Features directory |
| `--dry-run` | No | Preview without writing |
| `--format` | No (default: table) | table or json |
| `--interactive` | No | Guided prompts (errors if not TTY) |

\*Required unless `--interactive`.

### `specleft features add-scenario`

| Option | Required | Description |
|---|---|---|
| `--feature` | Yes | Feature ID to add to |
| `--title` | Yes* | Scenario title |
| `--id` | No | Scenario ID (auto-generated from title if omitted) |
| `--step` | No | Step text, repeatable. User includes Given/When/Then keywords |
| `--priority` | No | Priority level |
| `--tags` | No | Comma-separated tags |
| `--dir` | No (default: features) | Features directory |
| `--dry-run` | No | Preview without writing |
| `--format` | No (default: table) | table or json |
| `--interactive` | No | Guided prompts (errors if not TTY) |
| `--add-test` | No | `stub` or `skeleton`. Auto-generates test file after scenario is added |
| `--preview-test` | No | Prints preview of generated test (works with or without `--dry-run`) |

### Validation Rules

1. **Feature ID**: `^[a-z0-9-]+$`
2. **Scenario ID**: `^[a-z0-9-]+$`
3. **Steps**: Warn if not starting with Given/When/Then/And/But
4. **`--add-test skeleton`** with no steps: Error — "No steps found for test skeleton. Add steps to scenario or select '--add-test stub'"
5. **`--interactive`** on non-TTY: Error — "Interactive mode requires a terminal. Use explicit options instead."
6. **`features add`**: Error if file already exists
7. **`features add-scenario`**: Error if feature file doesn't exist

### Output Formats

**Table (default):** Human-readable summary with file path, IDs, content preview

**JSON:** Machine-readable with `success`, `action`, `feature_id`, `scenario_id`, `file_path`, `steps_count`, `dry_run`

**Error JSON:**
```json
{
  "success": false,
  "action": "add_scenario",
  "error": "Feature file not found: features/feature-user-auth.md",
  "suggestion": "Run 'specleft features add --id user-auth --title \"...\"' first"
}
```

### Post-Success Flow (add-scenario, table mode)

- If `--add-test` provided: auto-generate and write test file
- If `--add-test` not provided and not `--format json`: prompt "Generate test skeleton? [Y/n]"
- If `--preview-test`: print test content to stdout

---

## Phase 4: Tests — `test_features_add.py`

**Status:** Pending

### TestFeatureWriter (unit tests)

- `test_generate_scenario_id` — slug generation from various titles
- `test_validate_feature_id_valid` / `test_validate_feature_id_invalid`
- `test_validate_step_keywords_warns` — warnings for non-Gherkin steps
- `test_create_feature_file` — file creation, content structure verification
- `test_create_feature_file_exists_error`
- `test_create_feature_file_dry_run` — no file written
- `test_create_feature_file_auto_creates_dir`
- `test_add_scenario_with_tag_window` — appends within existing tags
- `test_add_scenario_without_tag_window` — inserts tag window
- `test_add_scenario_auto_id` — ID generated from title
- `test_add_scenario_dry_run`
- `test_add_scenario_missing_feature_error`

### TestFeaturesAddCommand (CLI integration)

- `test_add_basic`
- `test_add_json_output`
- `test_add_dry_run`
- `test_add_duplicate_error`
- `test_add_invalid_id`
- `test_add_interactive` (mocked input)

### TestFeaturesAddScenarioCommand (CLI integration)

- `test_add_scenario_basic`
- `test_add_scenario_with_steps`
- `test_add_scenario_json`
- `test_add_scenario_dry_run`
- `test_add_scenario_missing_feature`
- `test_add_scenario_auto_id`
- `test_add_scenario_with_tags_and_priority`
- `test_add_test_stub`
- `test_add_test_skeleton_no_steps_error`
- `test_add_test_skeleton_with_steps`
- `test_preview_test`

### TestHistory (unit tests)

- `test_log_and_load_history`
- `test_history_creates_directory`

---

## Phase 5: Documentation and Cleanup

**Status:** Pending

- [ ] Update `docs/cli-reference.md` with `features add` and `features add-scenario` sections
- [ ] Update `PROGRESS.md` to mark phases complete
- [ ] Run `make lint` and fix any issues
- [ ] Run full test suite and confirm green

---

## Acceptance Criteria (from issue + refinements)

- [ ] `specleft features add` creates properly formatted feature files
- [ ] `specleft features add-scenario` appends scenarios to existing features
- [ ] `--dry-run` shows preview without modifying files
- [ ] `--format json` outputs machine-readable JSON
- [ ] `--interactive` provides guided prompts
- [ ] Scenario ID auto-generated from title when `--id` omitted
- [ ] Validation errors provide helpful messages
- [ ] Integration with `specleft test skeleton` via prompt
- [ ] Commands follow existing CLI patterns (`--dir`, `--format`)
- [ ] All file mutations are visible and reported to the user (table and JSON)
- [ ] Operations logged in `.specleft/history/<feature-id>.json`
- [ ] `--add-test stub|skeleton` generates test files for agents
- [ ] `--add-test skeleton` without steps returns validation error
- [ ] `--preview-test` shows test preview (with or without `--dry-run`)
- [ ] `--interactive` errors on non-TTY
