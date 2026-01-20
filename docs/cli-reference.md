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
