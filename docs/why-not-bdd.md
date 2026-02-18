# Why SpecLeft Is Not a Conventional BDD Tool

BDD tools are well-established and solve a real problem, but they make trade-offs that don't fit many modern teams.

Here's the practical difference.

## General BDD model

- Specs are the tests
- Behavior is executed through step-definition glue
- Runtime interpretation of text drives execution
- Tests live outside your normal test framework
- Refactoring behavior often means refactoring text and glue

This works well when:

- QAs own specs
- Developers implement glue
- The organization is committed to BDD ceremony

It breaks down when:

- Tests are already written
- Developers want code-first workflows
- Specs are evolving, incomplete, or exploratory
- Teams want gradual adoption

## SpecLeft's model

- Specs describe intent, not execution
- Tests remain native pytest functions
- Skeletons are generated once, then owned by humans
- No runtime interpretation of text
- No glue layer to maintain

In short:

| BDD Tool | SpecLeft |
|---|---|
| Specs executed at runtime | Specs generate skeleton test |
| Text-driven execution | Code-driven execution |
| Glue code required | Plain pytest |
| Heavy ceremony | Incremental adoption |
| All-in or nothing | Opt-in per test |

SpecLeft is not "BDD without Gherkin Given/When/Then".
It's TDD with better alignment and visibility.

