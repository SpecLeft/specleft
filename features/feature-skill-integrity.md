# Feature: Skill File Integrity Verification

## Scenarios

### Scenario: Skill command group is discoverable
priority: high

- Given the SpecLeft CLI is available
- When `specleft skill --help` is invoked
- Then the output lists `verify` and `update` subcommands

### Scenario: Verify reports pass after init
priority: high

- Given `specleft init` has generated `.specleft/SKILL.md`
- And a matching `.specleft/SKILL.md.sha256` exists
- When `specleft skill verify --format json` is invoked
- Then the integrity status is `pass`

### Scenario: Verify reports modified on hash mismatch
priority: high

- Given `.specleft/SKILL.md` content is modified after generation
- And `.specleft/SKILL.md.sha256` still has the previous hash
- When `specleft skill verify --format json` is invoked
- Then the integrity status is `modified`

### Scenario: Verify reports outdated for non-canonical but checksum-valid content
priority: medium

- Given `.specleft/SKILL.md` matches its checksum file
- But the content differs from the current packaged template
- When `specleft skill verify --format json` is invoked
- Then the integrity status is `outdated`

### Scenario: Skill update repairs modified integrity state
priority: high

- Given `.specleft/SKILL.md` and `.specleft/SKILL.md.sha256` are inconsistent
- When `specleft skill update --format json` is invoked
- Then `specleft skill verify --format json` reports integrity `pass`
