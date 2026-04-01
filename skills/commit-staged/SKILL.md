---
name: commit-staged
description: Inspect the staged git diff, write an appropriate commit message in Traditional Chinese that follows the current repository's AGENTS.md rules, and create the commit. Use when Codex is asked to commit the currently staged changes and the message must be derived from the staged content rather than the full worktree.
---

# Commit Staged

Create a commit from the staged changes only, following the repository's AGENTS.md commit rules.

## Workflow

1. Inspect the staged diff and staged file list, not the full unstaged worktree.
2. Derive the commit intent from what is actually staged.
3. Write the commit message in Traditional Chinese.
4. Prefer Conventional Commit style such as `feat(scope): ...`, `fix: ...`, `refactor: ...`, `test: ...`, or `chore: ...`.
5. Create the commit using the staged content.

## Working Rules

- Do not describe unstaged or unrelated changes.
- Keep the subject imperative and specific.
- Default to the repository's preferred Conventional Commit format when it fits the staged change.
- Add a body when the staged change is non-trivial, explaining why the change was made and any important context or impact.
- Derive scope from the staged files only when it is clear and useful.
- If nothing is staged, stop and report that no commit can be created.

## Message Standard

- Write the subject in Traditional Chinese.
- Keep the subject focused on the user-visible or code-level change that is actually staged.
- Avoid vague subjects such as "修改一些東西" or "更新".
- If the staged diff mixes unrelated intent, stop and report that the staging should be split before committing.

## Output

State the final commit message and whether the commit was created successfully.
