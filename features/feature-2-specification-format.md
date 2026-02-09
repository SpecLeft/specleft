# Feature: Feature 2: Specification Format
priority: critical

## Scenarios

### Scenario: Minimal valid feature file
- Given a feature file exists under `.specleft/specs/`
- When it contains at least one scenario with a priority
- Then it is considered valid by SpecLeft
- And missing metadata fields are treated as null

### Scenario: Optional metadata does not block usage
- Given a feature file includes optional metadata
- When SpecLeft parses the file
- Then metadata is included in JSON output
- And absence of metadata does not cause errors
