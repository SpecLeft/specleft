# Feature: Feature 5: Policy Enforcement
priority: critical

## Scenarios

### Scenario: Enforce critical and high priority scenarios
- Given a signed policy requiring critical and high scenarios to be implemented
- And one or more such scenarios are unimplemented
- When `specleft enforce <policy.yml>` is executed
- Then the command exits with a non-zero status
- And the failure message explains which intent was violated

### Scenario: Pass enforcement when intent is satisfied
- Given all critical and high priority scenarios are implemented
- When enforcement is executed
- Then the command exits successfully

### Scenario: Reject invalid or unsigned policies
- Given a policy file has an invalid or missing signature
- When enforcement is executed
- Then enforcement fails with a clear error
- And no intent evaluation is performed
