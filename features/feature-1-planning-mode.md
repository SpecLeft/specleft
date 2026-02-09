# Feature: Feature 1: Planning Mode

priority: critical

## Scenarios

### Scenario: Generate feature files from PRD
priority: critical
- Given a repository contains a `prd.md`
- When `specleft plan` is executed
- Then feature files are created under `.specleft/specs/`
- And each feature maps to a user-visible capability
- And no code or test files are modified

### Scenario: Derive feature filenames from PRD headings
priority: critical
- Given the PRD contains multiple feature sections
- When feature files are generated
- Then filenames are derived as slugs from feature titles
- And existing feature files are not overwritten

### Scenario: Handle missing PRD gracefully

- Given no PRD file exists in the repository
- When `specleft plan` is executed
- Then a clear warning is emitted
- And no feature files are created

### Scenario: Validate PRD template definitions
priority: high
- Given a PRD template file defines headings and patterns
- When the template is loaded for planning
- Then invalid heading levels are rejected with a clear error
- And invalid patterns are rejected with a clear error

### Scenario: Analyze PRD structure without writing files
priority: high
- Given a PRD contains headings that mix features and notes
- When `specleft plan --analyze` is executed
- Then the output classifies headings as feature, excluded, or ambiguous
- And no feature files are created

### Scenario: Generate features with a custom PRD template
priority: high
- Given a PRD template defines custom feature and scenario patterns
- When `specleft plan --template <file.yml>` is executed
- Then features are generated using the custom patterns
- And priorities are normalized using the template mapping

### Scenario: Trace async test execution

- Given a test function decorated with @specleft and @pytest.mark.asyncio
- When the async test is executed with pytest
- Then the test runs successfully
- And step results are properly recorded
- And the async function is awaited correctly
