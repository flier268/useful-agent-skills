---
name: commit-staged
description: Commit only staged changes with a Traditional Chinese message from the staged diff.
---

# Commit Staged

Commit staged changes only.

## Workflow

1. Inspect `git diff --cached` and the staged file list.
2. If nothing is staged, stop.
3. If staged changes mix unrelated intent, ask for split staging.
4. Derive the commit intent from staged content only.
5. Write a Traditional Chinese message, preferably Conventional Commit style when it fits.
6. Create the commit.

## Working Rules

- Do not describe unstaged or unrelated changes.
- Keep the subject imperative and specific.
- Use a scope only when staged paths make it clear.
- Add a body only when the staged change needs context.

## Repo Boundary Rules

- Treat a git submodule as a separate repository.
- If the staged changes are inside a submodule repo, commit inside the submodule first.
- If the parent stages only a submodule gitlink pointer, describe only the pointer update.
- If a submodule has staged internal changes but the parent has no staged pointer, commit the submodule first, then stage and commit the parent pointer if requested.
- If the parent repo has the only staged change and it is a submodule gitlink pointer update, do not block that commit just because the submodule worktree also has unstaged edits.
- For subtree-style directories, treat staged files as normal repo files unless repo instructions say otherwise.

## Message Standard

- Write the subject in Traditional Chinese.
- Avoid vague subjects such as `更新` or `修改一些東西`.
- For submodule pointer commits, say the submodule version or pointer was updated.
- For subtree sync commits, name the synced package or directory when clear.

## Output

State the final commit message and whether the commit was created. If submodules are involved, say where the commit was made.
