# SpecLeft Getting Started

## Quickstart (existing codebase)

```bash
specleft start
```

If you already have code, `specleft start` is faster. It discovers specs from
your existing tests, routes, and docstrings.

## Install

```bash
pip install -e ".[dev]"
```

## Create Specs (greenfield alternative)

```bash
mkdir -p .specleft/specs/calculator/addition
```

Create `.specleft/specs/calculator/_feature.md`, `.specleft/specs/calculator/addition/_story.md`, and a scenario file like `.specleft/specs/calculator/addition/basic_addition.md`.

## Generate Tests

```bash
specleft test skeleton --features-dir .specleft/specs --output-dir tests
```

Preview without writing files:

```bash
specleft test skeleton --dry-run --format json
```

Preview initialization plan:

```bash
specleft init --dry-run --format json
```

## Run Tests

```bash
pytest
```

## Generate Report

```bash
specleft test report --open-browser
```

Preview report data as JSON:

```bash
specleft test report --format json
```
