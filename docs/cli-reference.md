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

## Enforce

### `specleft enforce`

Validate a cryptographic policy file and enforce coverage/priority rules against the repository's test specifications.

```bash
specleft enforce [POLICY_FILE] [OPTIONS]

Arguments:
  POLICY_FILE           Path to policy YAML file (default: .specleft/policies/policy.yml)

Options:
  --dir PATH                  Path to features directory (default: .specleft/specs/)
  --format [table|json]       Output format (default: table)
  --ignore-feature-id TEXT    Exclude feature from enforcement (Enforce+ tier only, repeatable)
  --tests PATH                Path to tests directory (default: tests/)
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Policy satisfied - all checks passed |
| 1 | Policy violated - missing scenarios or coverage below threshold |
| 2 | License issue - invalid signature, expired, evaluation ended, or repo mismatch |

#### Policy Types

**Core Policy** - Priority-based enforcement only
- Validates that scenarios with specified priorities are implemented
- Does not support `--ignore-feature-id` flag

**Enforce Policy** - Full enforcement with coverage thresholds
- Includes priority enforcement
- Adds coverage threshold validation
- Supports `--ignore-feature-id` flag for excluding features
- May include evaluation period for trial licenses

#### Examples

```bash
# Enforce with default policy location
specleft enforce

# Enforce with specific policy file
specleft enforce .specleft/policies/policy-core.yml

# Enforce with JSON output
specleft enforce --format json

# Exclude a feature from enforcement (Enforce tier only)
specleft enforce --ignore-feature-id legacy-api

# Exclude multiple features
specleft enforce --ignore-feature-id legacy-api --ignore-feature-id deprecated-feature
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

## License

### `specleft license status`

Show license status and the validated policy file.

```bash
specleft license status [OPTIONS]

Options:
  --file PATH   License policy file to check (default: .specleft/policies/policy.yml)
```

Example:

```bash
specleft license status --file .specleft/policies/policy.yml
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
