# Agent Workflow: GitHub Issue to PR

Step-by-step workflow for AI coding agents working from the SpecLeft Kanban board.
Designed for autonomous execution with full traceability back to the originating issue.

---

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`)
- Repository cloned and on `main` branch
- Development environment set up per [CONTRIBUTING.md](CONTRIBUTING.md)
- Access to the [SpecLeft GitHub Project board](https://github.com/orgs/SpecLeft/projects/1)

---

## Step 1: Pick the Next Issue

Retrieve the top item from the SpecLeft Kanban board:

```bash
gh project item-list 1 --owner SpecLeft --limit 1
```

Note the issue number (e.g., `#92`) from the output. All subsequent commands reference this number.

---

## Step 2: Understand the Issue

View the full issue details:

```bash
gh issue view <NUMBER> --repo SpecLeft/specleft
```

For machine-readable output:

```bash
gh issue view <NUMBER> --repo SpecLeft/specleft --json title,body,labels,assignees,milestone
```

Read the full issue body. Identify:
- Acceptance criteria (look for `- [ ]` checkboxes)
- Referenced specs, PRDs, or feature files
- Labels indicating issue type (bug, feature, enhancement)

---

## Step 3: Clarify and Create Implementation Notes

### If clarification is needed

Post questions as a comment:

```bash
gh issue comment <NUMBER> --repo SpecLeft/specleft --body "## Questions

- Q1: ...
- Q2: ..."
```

Wait for owner response before proceeding.

### Create the Implementation Notes comment

Once scope is clear, create a single Implementation Notes comment that will be updated throughout development:

```bash
gh issue comment <NUMBER> --repo SpecLeft/specleft --body "## Implementation Notes

**Branch:** \`<NUMBER>-<short-description>\`
**Approach:** <brief summary of implementation approach>

### Decisions
- <key technical decision and rationale>

### Tasks
_To be added after planning._"
```

### Capture the comment ID

Store the comment ID for later updates:

```bash
COMMENT_ID=$(gh api repos/SpecLeft/specleft/issues/<NUMBER>/comments --jq '.[-1].id')
```

This `COMMENT_ID` is used in all subsequent comment updates. Keep it for the duration of the session.

---

## Step 4: Create a Linked Branch

Use `gh issue develop` to create a branch with automatic issue linkage:

```bash
gh issue develop <NUMBER> --repo SpecLeft/specleft --name <NUMBER>-<short-description> --base main
```

Branch naming convention: `<issue-number>-<kebab-case-description>`

Examples:
- `92-add-plan-template-support`
- `85-skeleton-bug`
- `68-flexible-prd-parsing`

---

## Step 5: Checkout Locally

```bash
git fetch origin
git checkout <NUMBER>-<short-description>
```

---

## Step 6: Load Implementation Instructions

Read the implementation skill and agent profile:

- [.llm/instructions.md](.llm/instructions.md) -- phase-based implementation template
- [.llm/profile.md](.llm/profile.md) -- agent profile and working style
- [docs/SKILL.md](docs/SKILL.md) -- SpecLeft agent task execution skill

Follow the phase-based approach defined in `.llm/instructions.md`. Use the SpecLeft-specific commands from `docs/SKILL.md` when working with feature specs.

---

## Step 7: Plan Tasks and Create Local Progress Tracker

### Create `.progress.md`

Create a local progress file in the repository root. This file is the agent's working state — it avoids repeated GitHub API calls and carries context across session restarts.

```markdown
<!-- .progress.md -->
# Progress: #<NUMBER> - <Issue Title>

## Branch
`<NUMBER>-<short-description>`

## Comment ID
<COMMENT_ID>

## Tasks
- [ ] Task 1 description
- [ ] Task 2 description
- [ ] Task 3 description
- [ ] Task 4 description
- [ ] Task 5 description
- [ ] Task 6 description

## Batch Queue
<!-- Tasks completed since last GitHub sync -->

## Decisions
- <key technical decision and rationale>
```

Add `.progress.md` to `.gitignore` — it is local working state, not project code:

```bash
echo ".progress.md" >> .gitignore
```

### Sync tasks to the Implementation Notes comment

Push the task list to GitHub so the owner has visibility:

```bash
gh api repos/SpecLeft/specleft/issues/comments/$COMMENT_ID \
  --method PATCH \
  --field body="## Implementation Notes

**Branch:** \`<NUMBER>-<short-description>\`
**Approach:** <brief summary>

### Decisions
- <decision 1>

### Tasks
- [ ] Task 1 description
- [ ] Task 2 description
- [ ] Task 3 description
- [ ] Task 4 description
- [ ] Task 5 description
- [ ] Task 6 description"
```

### If the issue body contains Acceptance Criteria

Do not duplicate them. Reference the issue's own `- [ ]` items and break them into implementation subtasks in your task list. You will mark the issue body's criteria as complete during GitHub sync (Step 11).

---

## Step 8: Implement

Work on one task or a small group of related subtasks at a time.

Follow the conventions in [CONTRIBUTING.md](CONTRIBUTING.md):
- Type hints on all function parameters and return values
- `pathlib.Path` for file operations
- PEP 8 naming: `snake_case` functions, `PascalCase` classes
- Functions under 50 lines

---

## Step 9: Lint and Test

Chain the commands to save tool calls:

```bash
make lint-fix && make lint && make test
```

**Do not proceed to Step 10 if any step fails.** Fix issues first and re-run.

If `make lint` fails after `lint-fix`, the remaining issues are typically:
- **mypy type errors** -- fix type annotations manually
- **Unfixable ruff violations** -- refactor the code

---

## Step 10: Commit, Push, and Update Local Progress

### Commit and push

Stage specific files (not `git add .`):

```bash
git add <specific-files>
git commit -m "Description of change (#<NUMBER>)"
git push origin <NUMBER>-<short-description>
```

Commit message rules:
- Present tense, imperative mood ("Add feature" not "Added feature")
- Under 72 characters
- Always include the issue reference `(#<NUMBER>)` at the end

Examples:
```
Add template loading utility (#92)
Fix edge case in YAML parsing (#92)
Update CLI reference for plan --template (#92)
```

### Update `.progress.md` locally

Mark the task complete and add it to the batch queue:

```markdown
## Tasks
- [x] Add template loading utility   ← mark done
- [ ] Write tests for template loading
- [ ] Extend plan command with --template flag
...

## Batch Queue
- [x] Add template loading utility    ← track for next GitHub sync
```

This is a local file read/write — no API calls, no tokens spent on `gh`.

---

## Step 11: Sync Progress to GitHub (Batched)

### When to sync

Sync the Implementation Notes comment to GitHub when **any** of these conditions is met:

1. **3 tasks completed** since the last sync
2. **Switching to a different area of the codebase** (e.g., moving from core logic to tests)
3. **All tasks are complete** (final sync before PR)
4. **Session is ending** (push current state so a new session can resume)

### How to sync

Read the current state from `.progress.md` and push it to the GitHub comment:

```bash
gh api repos/SpecLeft/specleft/issues/comments/$COMMENT_ID \
  --method PATCH \
  --field body="## Implementation Notes

**Branch:** \`92-add-plan-template-support\`
**Approach:** Add Jinja2 template support to the plan command

### Decisions
- Use Jinja2 for template rendering (consistent with existing skeleton templates)

### Tasks
- [x] Add template loading utility
- [x] Write tests for template loading
- [x] Extend plan command with --template flag
- [ ] Write integration tests"
```

After syncing, clear the batch queue in `.progress.md`.

### Update Acceptance Criteria in the issue body

If the issue body contains `- [ ]` acceptance criteria, update them during the sync:

```bash
# Fetch the current body
BODY=$(gh issue view <NUMBER> --repo SpecLeft/specleft --json body --jq '.body')

# Modify BODY: change "- [ ] <criterion>" to "- [x] <criterion>" for completed items

# Write it back
gh issue edit <NUMBER> --repo SpecLeft/specleft --body "$BODY"
```

Always fetch the latest body before editing to avoid overwriting changes made by others.

---

## Step 12: Repeat

Return to **Step 8**. Follow this cycle:

```
Implement → Lint/Test → Commit/Push → Update .progress.md
  ↓ (repeat up to 3 tasks)
Sync to GitHub (Step 11)
  ↓ (repeat)
Until all tasks in .progress.md are [x]
```

The inner loop (Steps 8–10) is fast and local. The outer sync (Step 11) is the only step that makes GitHub API calls.

---

## Step 13: Create the Pull Request

Once all tasks are complete:

```bash
gh pr create \
  --repo SpecLeft/specleft \
  --base main \
  --head <NUMBER>-<short-description> \
  --title "<Short description> (#<NUMBER>)" \
  --body "## Description
<Summary of what was implemented and why>

## Type of Change
- [x] <applicable type from PR template>

## Checklist
- [x] My code follows the style guidelines of this project
- [x] I have performed a self-review of my code
- [x] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes

## Testing
- \`make test\` -- all tests passing
- \`make lint\` -- all checks passing

## Related Issues
Closes #<NUMBER>"
```

Using `Closes #<NUMBER>` automatically closes the issue and moves it to "Done" on the Kanban board when the PR merges.

---

## Traceability Tips

### Use `gh issue develop` for branch creation
Creates a GitHub-tracked link between the issue and the branch, visible in the issue sidebar under "Development." Prefer this over manual `git checkout -b`.

### Reference issue number in every commit
Including `(#<NUMBER>)` in commit messages creates automatic backlinks from the issue timeline to each commit. Reviewers can trace any line of code back to the issue that motivated it.

### Maintain a single Implementation Notes comment
Update one comment in-place (via `gh api PATCH`) rather than posting new comments. This gives reviewers a single location for: branch name, approach, decisions, and task progress.

### Use `.progress.md` as the local source of truth
The agent reads and writes `.progress.md` instead of querying GitHub for current state. This eliminates repeated API calls and keeps the full task context available without carrying it in the conversation. On session restart, read `.progress.md` first — it tells you exactly where you left off.

### Batch GitHub comment updates (up to 3 tasks)
Sync to the GitHub comment after every 3 completed tasks, when switching code areas, or at session end. This cuts API calls by ~60% while keeping the owner informed at meaningful intervals.

### Use task checkboxes for progress tracking
GitHub renders `- [ ]` / `- [x]` as a progress bar in the issue list view. Completion status is visible at a glance from the Kanban board.

### Commit atomically per task
Commit after each task completes, not at the end. This creates a 1:1 mapping between tasks in the Implementation Notes and commits in the branch history.

### Push after each commit
Push immediately after each commit. This ensures:
- Progress is visible to the owner in real time
- Work is not lost if the agent session terminates
- Code is recoverable even if `.progress.md` and the GitHub comment are temporarily out of sync

### Close issues via PR body
Use `Closes #<NUMBER>` in the PR body. When the PR merges, GitHub automatically closes the issue and moves it on the Kanban board.

### Keep decisions in the Implementation Notes
Record non-obvious technical decisions and their rationale in the "Decisions" section of both `.progress.md` (local) and the Implementation Notes comment (GitHub). This creates a searchable record that persists beyond the PR.

### Token cost awareness
The inner loop (implement → lint → commit → update `.progress.md`) is cheap — local file operations only. The outer sync (push to GitHub comment) is the expensive step. Structure work to maximise progress between syncs.

---

## Edge Cases and Failure Handling

### No issues on the board
If `gh project item-list` returns empty, stop and notify the owner. Do not create issues autonomously.

### Lint failure after lint-fix
`make lint-fix` auto-fixes formatting and some linting. If `make lint` still fails:
- **mypy type errors**: fix type annotations manually
- **Unfixable ruff violations**: refactor the code

Do not bypass lint failures.

### Test failure
1. Read the failure output carefully
2. Fix the failing test or the implementation
3. Re-run `make test` to confirm
4. Only then proceed to commit

Never commit code that fails tests.

### Branch already exists
If `gh issue develop` fails because the branch exists:

```bash
git fetch origin
git checkout <existing-branch-name>
git pull origin <existing-branch-name>
```

Resume from Step 6.

### Merge conflicts
If pushing fails due to remote changes:

```bash
git fetch origin main
git rebase origin/main
# Resolve conflicts if any
make lint && make test
git push origin <branch-name> --force-with-lease
```

Use `--force-with-lease` (never `--force`) to protect against overwriting others' work.

### Resuming a session
If the agent session terminates and restarts:

1. Read `.progress.md` — it contains the issue number, branch name, comment ID, and current task state
2. Checkout the branch: `git checkout <branch-from-progress-file>`
3. Check which tasks are `[x]` in `.progress.md` vs the GitHub comment
4. If the batch queue is non-empty, sync to GitHub first (Step 11)
5. Resume from the next `[ ]` task at Step 8

This avoids re-fetching the issue, re-reading instructions, or re-planning tasks.

### Comment ID lost between sessions
If `.progress.md` is also missing, recover the Implementation Notes comment ID:

```bash
gh api repos/SpecLeft/specleft/issues/<NUMBER>/comments \
  --jq '.[] | select(.body | startswith("## Implementation Notes")) | .id'
```

### Pre-commit hook failures
If a git hook fails on commit:
1. Read the failure output
2. Fix the issues (usually formatting)
3. Re-stage the files
4. Create a **new** commit (do not amend)

---

## Quick Reference

| Step | Command |
|------|---------|
| View board | `gh project item-list 1 --owner SpecLeft --limit 1` |
| View issue | `gh issue view <N> --repo SpecLeft/specleft` |
| View issue (JSON) | `gh issue view <N> --repo SpecLeft/specleft --json title,body,labels` |
| Comment on issue | `gh issue comment <N> --repo SpecLeft/specleft --body "..."` |
| Get comment ID | `gh api repos/SpecLeft/specleft/issues/<N>/comments --jq '.[-1].id'` |
| Update comment | `gh api repos/SpecLeft/specleft/issues/comments/$COMMENT_ID --method PATCH --field body="..."` |
| Create linked branch | `gh issue develop <N> --repo SpecLeft/specleft --name <N>-<desc> --base main` |
| Checkout branch | `git fetch origin && git checkout <N>-<desc>` |
| Auto-fix lint | `make lint-fix` |
| Check lint | `make lint` |
| Run tests | `make test` |
| Pre-commit | `make pre-commit` |
| Commit | `git commit -m "Description (#<N>)"` |
| Push | `git push origin <N>-<desc>` |
| Edit issue body | `gh issue edit <N> --repo SpecLeft/specleft --body "..."` |
| Create PR | `gh pr create --repo SpecLeft/specleft --base main --head <N>-<desc> --title "..." --body "..."` |
| Find notes comment | `gh api repos/SpecLeft/specleft/issues/<N>/comments --jq '.[] \| select(.body \| startswith("## Implementation Notes")) \| .id'` |
