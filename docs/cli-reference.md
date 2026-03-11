# SpecLeft CLI Reference

## Features

### `specleft features validate`

Validate Markdown specs.

```bash
specleft features validate [OPTIONS]

Options:
  --dir PATH            Path to features directory (default: features)
  --format [table|json] Output format (default: table)
  --strict              Treat warnings as errors
```

### `specleft features list`

List features, stories, and scenarios.

```bash
specleft features list [OPTIONS]

Options:
  --dir PATH            Path to features directory (default: features)
  --format [table|json] Output format (default: table)
```

### `specleft features stats`

Show aggregate statistics for specs.

```bash
specleft features stats [OPTIONS]

Options:
  --dir PATH            Path to features directory (default: features)
  -t, --tests-dir PATH  Path to tests directory (default: tests)
  --format [table|json] Output format (default: table)
```

### `specleft features add`

Create a new feature markdown file.

```bash
specleft features add [OPTIONS]

Options:
  --id TEXT               Feature ID (optional; defaults to a slug from the title)
  --title TEXT            Feature title (required)
  --priority [critical|high|medium|low]  Feature priority (default: medium)
  --description TEXT      Feature description
  --dir PATH              Path to features directory (default: features)
  --dry-run               Preview without writing files
  --format [table|json]   Output format (default: table)
  --interactive           Use guided prompts (requires TTY)
```

### `specleft features add-scenario`

Append a scenario to an existing feature file.

```bash
specleft features add-scenario [OPTIONS]

Options:
  --feature TEXT          Feature ID to append scenario to
  --title TEXT            Scenario title
  --id TEXT               Scenario ID (optional; defaults to a slug from the title)
  --step TEXT             Scenario step (repeatable)
  --priority [critical|high|medium|low]  Scenario priority
  --tags TEXT             Comma-separated tags
  --dir PATH              Path to features directory (default: features)
  --tests-dir PATH         Directory for generated test files (default: tests)
  --dry-run               Preview without writing files
  --format [table|json]   Output format (default: table)
  --interactive           Use guided prompts (requires TTY)
  --add-test [stub|skeleton]  Generate a test stub or skeleton
  --preview-test          Print the generated test content
```

## Contract

### `specleft contract`

Show the SpecLeft Agent Contract.

```bash
specleft contract [OPTIONS]

Options:
  --format [table|json] Output format (default: table)
```

### `specleft contract test`

Verify Agent Contract guarantees.

```bash
specleft contract test [OPTIONS]

Options:
  --format [table|json] Output format (default: table)
  --verbose             Show detailed check results
```

## Doctor

### `specleft doctor`

Verify SpecLeft installation and environment.

```bash
specleft doctor [OPTIONS]

Options:
  --format [table|json]  Output format (default: table)
  --verbose              Show detailed diagnostic information
  --verify-skill         Verify .specleft/SKILL.md checksum and template freshness
  --pretty               Pretty-print JSON output
```

## Skill

### `specleft skill`

Manage SpecLeft skill files.

```bash
specleft skill --help
```

### `specleft skill verify`

Verify SKILL.md integrity and freshness.

```bash
specleft skill verify [OPTIONS]

Options:
  --format [table|json]  Output format (default: table)
  --pretty               Pretty-print JSON output
```

### `specleft skill update`

Regenerate SKILL.md and checksum from the current SpecLeft version.

```bash
specleft skill update [OPTIONS]

Options:
  --format [table|json]  Output format (default: table)
  --pretty               Pretty-print JSON output
```

## Init

### `specleft init`

Initialize SpecLeft directories and example specs.

```bash
specleft init [OPTIONS]

Options:
  --example             Create example specs
  --blank               Create empty directory structure only
  --dry-run             Show what would be created
  --force               Regenerate SKILL.md if it was modified
  --format [table|json] Output format (default: table)
```

## Start

### `specleft start`

Discovery-first entrypoint for existing codebases. Runs health checks, scans code,
discovers features, and compares discovered scenarios against existing specs.

```bash
specleft start [OPTIONS] [PROJECT_ROOT]

Options:
  --format [table|json]  Output format (default: auto-detect TTY)
  --save                 Write draft specs to .specleft/specs/_discovered/
  --specs-dir PATH       Existing specs dir to compare against
  --pretty               Pretty-print JSON output
```

`--save` stages drafts in `.specleft/specs/_discovered/` only. It does not
promote them automatically to active specs.

To generate and write specs directly, use `specleft discover`.

## Discover

### `specleft discover`

Run the full discovery pipeline and stage generated draft specs.

```bash
specleft discover [OPTIONS] [PROJECT_ROOT]

Options:
  --format [table|json]    Output format (default: auto-detect TTY)
  --dry-run                Preview without writing files
  --output-dir PATH        Override staging dir (default: .specleft/specs/_discovered/)
  --language [python|typescript]
                           Limit languages (repeatable)
  --specs-dir PATH         Existing specs dir for traceability matching
  --pretty                 Pretty-print JSON output
```

Table output example:

```text
Scanning project...
✓ Detected: Python (pytest), 847 files, 142 test functions

Discovering features...
✓ Found 14 features, 47 scenarios

Your project vs your specs:
┌──────────────────────────┬───────────┬─────────────┐
│ Feature                  │ Code      │ Specs       │
├──────────────────────────┼───────────┼─────────────┤
│ user-authentication      │ 12 tests  │ none        │
│ payment-processing       │ 8 tests   │ 6 specs     │
└──────────────────────────┴───────────┴─────────────┘
  ✓ Python (pytest) — 142 test functions
  ✓ API routes      — 24 routes
  ✓ Docstrings      — 67 items
  ✓ Git history     — 200 commits

Generating draft specs...

  Feature                  Scenarios  Written to
  ───────────────────────  ─────────  ──────────────────────────────────────
  user-authentication      8          .specleft/specs/_discovered/user-authentication.md
  payment-processing       5          .specleft/specs/_discovered/payment-processing.md

  14 features, 47 scenarios written to .specleft/specs/_discovered
  Review drafts, then promote with: specleft discover promote
```

JSON output schema:

```json
{
  "project": {
    "root": "/path/to/project",
    "languages": ["python"],
    "test_frameworks": ["pytest"],
    "files_scanned": 847
  },
  "discovery": {
    "features": 14,
    "scenarios": 47,
    "items_by_kind": {
      "test_function": 142,
      "api_route": 24,
      "docstring": 67,
      "git_commit": 200
    }
  },
  "comparison": [
    {
      "feature_id": "user-authentication",
      "name": "User Authentication",
      "code_scenarios": 12,
      "spec_scenarios": 0
    }
  ],
  "saved": false,
  "features": [
    {
      "feature_id": "user-authentication",
      "name": "User Authentication",
      "scenario_count": 8,
      "output_file": ".specleft/specs/_discovered/user-authentication.md",
      "confidence": 0.8
    }
  ],
  "total_features": 14,
  "total_scenarios": 47,
  "output_dir": ".specleft/specs/_discovered",
  "dry_run": false,
  "written": [".specleft/specs/_discovered/user-authentication.md"],
  "errors": []
}
```

### `specleft discover promote`

Promote draft specs into the active specs directory. Draft files remain in staging.

```bash
specleft discover promote [OPTIONS] [FEATURE_ID...]

Options:
  --all              Promote every staged draft file
  --specs-dir PATH   Destination specs dir (default: resolve_specs_dir())
  --overwrite        Replace existing files at destination
  --dry-run          Preview without writing files
  --format [table|json]
  --pretty
```

## Status

### `specleft status`

Show implemented vs skipped scenarios.

```bash
specleft status [OPTIONS]

Options:
  --dir PATH            Path to features directory (default: features)
  --format [table|json] Output format (default: table)
  --feature TEXT        Filter by feature ID
  --story TEXT          Filter by story ID
  --unimplemented       Show only unimplemented scenarios
  --implemented         Show only implemented scenarios
```

## Next

### `specleft next`

Show next scenarios to implement.

```bash
specleft next [OPTIONS]

Options:
  --dir PATH            Path to features directory (default: features)
  --limit INTEGER       Number of tests to show (default: 5)
  --format [table|json] Output format (default: table)
  --priority TEXT       Filter by priority (critical, high, medium, low)
  --feature TEXT        Filter by feature ID
  --story TEXT          Filter by story ID
```

## Coverage

### `specleft coverage`

Show coverage metrics for specs.

```bash
specleft coverage [OPTIONS]

Options:
  --dir PATH            Path to features directory (default: features)
  --format [table|json|badge] Output format (default: table)
  --threshold INTEGER   Exit non-zero if coverage below threshold
  --output PATH         Output file for badge format
```

## Guide

### `specleft guide`

Display the SpecLeft workflow guide.

```bash
specleft guide [OPTIONS]

Options:
  --format [table|json] Output format (default: table)
```

## Tests

### `specleft test skeleton`

Generate skeleton test files from Markdown specs.

```bash
specleft test skeleton [OPTIONS]

Options:
  -f, --features-dir PATH   Path to features directory (default: features)
  -o, --output-dir PATH     Output directory (default: tests)
  --single-file             Generate all tests in one file
  --skip-preview            Skip preview before creation
  --dry-run                 Show what would be created
  --format [table|json]     Output format (default: table)
  --force                   Overwrite existing test files
```

### `specleft test stub`

Generate stub test files from Markdown specs.

```bash
specleft test stub [OPTIONS]

Options:
  -f, --features-dir PATH   Path to features directory (default: features)
  -o, --output-dir PATH     Output directory (default: tests)
  --single-file             Generate all tests in one file
  --skip-preview            Skip preview before creation
  --dry-run                 Show what would be created
  --format [table|json]     Output format (default: table)
  --force                   Overwrite existing test files
```

### `specleft test report`

Generate an HTML report from test results.

```bash
specleft test report [OPTIONS]

Options:
  -r, --results-file PATH   Specific results JSON file (default: latest)
  -o, --output PATH         Output HTML file (default: report.html)
  --open-browser            Open report in browser after generation
  --format [table|json]     Output format (default: table)
```

## Plan

### `specleft plan`

Generate feature specs from a PRD.

```bash
specleft plan [OPTIONS]

Options:
  --from PATH             Path to the PRD file (default: prd.md)
  --format [table|json]   Output format (default: table)
  --dry-run               Preview without writing files
  --analyze               Analyze PRD structure without writing files
  --template PATH         Path to a PRD template YAML file
```

Examples:

```bash
# Analyze PRD structure
specleft plan --analyze

# Use a custom template
specleft plan --template .specleft/templates/prd-template.yml

# Use contains + match_mode in a template (case-insensitive)
# features:
#   contains: ["capability"]
#   match_mode: "contains"
# scenarios:
#   contains: ["acceptance"]
#   match_mode: "any"

# Analyze with JSON output
specleft plan --analyze --format json
```
