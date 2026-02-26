# SpecLeft CLI Reference

## Setup
`export SPECLEFT_COMPACT=1`
All commands below run in compact mode.

## Workflow
1. specleft next --limit 1
2. Implement test logic
3. specleft features validate
4. specleft skill verify
5. pytest
6. Repeat

## Quick checks
- Validation: check exit code first, parse JSON only on failure
- Coverage: `specleft coverage --threshold 100` and check exit code
- Status: `specleft status` for progress snapshots

## Safety
- Always `--dry-run` before writing files
- Never use `--force` unless explicitly requested
- Exit codes: 0 = success, 1 = error, 2 = cancelled
- Commands are deterministic and safe to retry

---

## Features

### Validate specs
`specleft features validate --format json [--dir PATH] [--strict]`
Validate before generating tests. `--strict` treats warnings as errors.

### List features
`specleft features list --format json [--dir PATH]`

### Show stats
`specleft features stats --format json [--dir PATH] [--tests-dir PATH]`

### Add a feature
`specleft features add --format json --id FEATURE_ID --title "Title" [--priority PRIORITY] [--description TEXT] [--dir PATH] [--dry-run]`
Creates `<features-dir>/feature-id.md`. Never overwrites existing files.
Use `--interactive` for guided prompts (TTY only).

### Add a scenario
`specleft features add-scenario --format json --feature FEATURE_ID --title "Title" [--id SCENARIO_ID] [--step "Given ..."] [--step "When ..."] [--step "Then ..."] [--priority PRIORITY] [--tags "tag1,tag2"] [--dir PATH] [--tests-dir PATH] [--dry-run] [--add-test MODE] [--preview-test]`
Appends to feature file. `--add-test` generates a test file.
`--preview-test` shows test content without writing. Use `--interactive`
for guided prompts (TTY only).

## Status and Planning

### Show status
`specleft status --format json [--dir PATH] [--feature ID] [--story ID] [--unimplemented] [--implemented]`

### Next scenario to implement
`specleft next --format json [--dir PATH] [--limit N] [--priority PRIORITY] [--feature ID] [--story ID]`

### Coverage metrics
`specleft coverage --format json [--dir PATH] [--threshold N] [--output PATH]`
`--threshold N` exits non-zero if coverage drops below `N%`.

## Test Generation

### Generate skeleton tests
`specleft test skeleton --format json [-f FEATURES_DIR] [-o OUTPUT_DIR] [--dry-run] [--force] [--single-file] [--skip-preview]`
Always run `--dry-run` first. Never overwrite without `--force`.

### Generate stub tests
`specleft test stub --format json [-f FEATURES_DIR] [-o OUTPUT_DIR] [--dry-run] [--force] [--single-file] [--skip-preview]`
Minimal test scaffolding with the same overwrite safety rules.

### Generate test report
`specleft test report --format json [-r RESULTS_FILE] [-o OUTPUT_PATH] [--open-browser]`
Builds an HTML report from `.specleft/results/`.

## Planning

### Generate specs from PRD
`specleft plan --format json [--from PATH] [--dry-run] [--analyze] [--template PATH]`
`--analyze` inspects PRD structure without writing files.
`--template` uses a YAML section-matching template.

## Contract

### Show contract
`specleft contract --format json`

### Verify contract
`specleft contract test --format json [--verbose]`
Run to verify deterministic and safe command guarantees.

## Skill Command Group

### Show skill commands
`specleft skill --help`
Displays skill lifecycle subcommands (`verify`, `update`).

### Verify skill integrity
`specleft skill verify --format json`
Returns `pass`, `modified`, or `outdated` integrity status.

### Update skill files
`specleft skill update --format json`
Regenerates `.specleft/SKILL.md` and `.specleft/SKILL.md.sha256`.

### Verify within doctor checks
`specleft doctor --verify-skill --format json`
Adds skill integrity status to standard environment diagnostics.

## Guide

### Show workflow guide
`specleft guide --format json`
