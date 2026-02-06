# Progress: Flexible PRD Parsing (Issue #68)

## Status: Not Started

## Execution Phases

### Phase 1: PRD Template Model + Loader
- [x] Create `src/specleft/templates/prd_template.py` with Pydantic models (`PRDTemplate`, `PRDFeaturesConfig`, `PRDScenariosConfig`, `PRDPrioritiesConfig`)
- [x] Implement `compile_pattern()` for `{title}`/`{value}` to regex conversion
- [x] Implement `load_template()` YAML reader with validation and error reporting
- [x] Implement `default_template()` factory function
- [x] Validate heading levels are 1-6, patterns compile correctly
- **Status:** Complete

### Phase 2: Refactor Extraction Functions
- [x] Refactor `_extract_feature_titles()` to accept `PRDTemplate` parameter
- [x] Refactor `_extract_prd_scenarios()` to accept `PRDTemplate` parameter
- [x] Make `is_feature_heading()` template-driven (level + pattern matching)
- [x] Make `extract_scenario_title()` template-driven
- [x] Make `is_step_line()` use `template.scenarios.step_keywords`
- [x] Make `extract_priority()` use `template.priorities.patterns` + mapping
- [x] Verify all 8 existing tests pass unchanged (backwards compatibility)
- **Status:** Complete

### Phase 3: Implement `--analyze` Mode
- [x] Add `--analyze` flag to `plan` Click command
- [x] Implement `_analyze_prd()` function with heading classification (`feature`, `scenario`, `excluded`, `ambiguous`)
- [x] Implement orphan content detection
- [x] Implement summary counts + actionable suggestions generation
- [x] Implement JSON output for `--analyze --format json`
- [x] Implement human-readable table output for `--analyze` (default)
- [x] Ensure read-only behavior (never writes files)
- **Status:** Complete

### Phase 4: Implement `--template` Mode
- [x] Add `--template` option to `plan` Click command
- [x] Wire template loading into extraction pipeline
- [x] Include template metadata (`path`, `version`) in JSON output
- [x] Verify composability: `--template` + `--dry-run`, `--template` + `--analyze`, `--template` + `--analyze` + `--format json`
- **Status:** Complete

### Phase 5: Tests
- [x] Write unit tests for `PRDTemplate` model and loader (`tests/commands/test_prd_template.py`)
- [x] Write `TestAnalyzeMode` tests in `tests/commands/test_plan.py`
- [x] Write `TestTemplateMode` tests in `tests/commands/test_plan.py`
- [x] Confirm all existing `TestPlanCommand` tests still pass
- [x] Full test suite green
- **Status:** Complete

### Phase 6: Documentation + Cleanup
- [x] Create `.specleft/templates/prd-template.yml` default reference file
- [x] Update `docs/cli-reference.md` with `plan --analyze` and `plan --template` documentation
- [x] Run `make lint` and fix any issues
- [x] Run full test suite and confirm green
- [x] Update this file to mark all phases complete
- **Status:** Complete

### Phase 7: Template Match Mode + Contains
- [x] Add `contains` + `match_mode` to feature/scenario template configs
- [x] Update extraction + analysis logic for match mode semantics (case-insensitive)
- [x] Update validation + defaults in templates
- [x] Extend unit + acceptance tests for match_mode/contains
- [x] Update template reference + docs
- [ ] Run lint and full test suite
- **Status:** In Progress
