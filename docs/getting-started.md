# SpecLeft Getting Started

## Install

```bash
pip install -e ".[dev]"
```

## Create Specs

```bash
mkdir -p features/calculator/addition
```

Create `features/calculator/_feature.md`, `features/calculator/addition/_story.md`, and a scenario file like `features/calculator/addition/basic_addition.md`.

## Generate Tests

```bash
specleft test skeleton --features-dir features --output-dir tests
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
