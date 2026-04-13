---
name: commit-staged
description: Inspect the staged git diff, write an appropriate commit message in Traditional Chinese that follows the current repository's AGENTS.md rules, and create the commit. Use when Codex is asked to commit the currently staged changes and the message must be derived from the staged content rather than the full worktree.
---

# Commit Staged

Create a commit from the staged changes only, following the repository's AGENTS.md commit rules.

## Workflow

1. Inspect the staged diff and staged file list, not the full unstaged worktree.
2. Detect whether the staged content is:
   - normal files in the current repo
   - a submodule pointer update in the current repo
   - staged changes inside a submodule repo
   - a vendored subtree-style directory update
3. Derive the commit intent from what is actually staged.
4. Write the commit message in Traditional Chinese.
5. Prefer Conventional Commit style such as `feat(scope): ...`, `fix: ...`, `refactor: ...`, `test: ...`, `docs: ...`, or `chore: ...`.
6. Create the commit using the staged content.

## Working Rules

- Do not describe unstaged or unrelated changes.
- Keep the subject imperative and specific.
- Default to the repository's preferred Conventional Commit format when it fits the staged change.
- Add a body when the staged change is non-trivial, explaining why the change was made and any important context or impact.
- Derive scope from the staged files only when it is clear and useful.
- If nothing is staged, stop and report that no commit can be created.
- When staged changes mix unrelated intent, stop and report that the staging should be split before committing.

## Repo Boundary Rules

- Treat a git submodule as a separate repository.
- If the user points at a submodule path, inspect both the parent repo's staged status and the submodule repo's staged status before deciding what to commit.
- If the staged changes are inside a submodule repo, commit inside the submodule first.
- If the parent repo only stages the submodule gitlink pointer, describe only the pointer update in the parent commit message.
- If a submodule has staged internal changes but the parent repo has nothing staged yet, report that the correct flow is:
  1. create the commit inside the submodule
  2. stage the updated submodule pointer in the parent repo
  3. create the parent repo commit if requested
- If the parent repo has the only staged change and it is a submodule gitlink pointer update, do not block that commit just because the submodule worktree also has unstaged edits.
- Never describe submodule internal file edits in the parent repo commit message unless those same files are actually staged in the parent repo, which normally they are not.
- For subtree-style directories, treat them as normal tracked files in the current repo unless repository instructions explicitly define a different workflow.
- If the staged subtree update is a vendor sync or bulk import, prefer a message that names the upstream package/project and the kind of sync when that can be inferred from the staged files.

## Message Standard

- Write the subject in Traditional Chinese.
- Keep the subject focused on the user-visible or code-level change that is actually staged.
- Avoid vague subjects such as "修改一些東西" or "更新".
- For submodule pointer commits, use wording that reflects updating the submodule version or pointer, for example `chore(path): 更新子模組版本` when a clear path-based scope is useful.
- For commits created inside a submodule, derive the message from the submodule's staged diff only.
- For subtree sync commits, mention the synced module or directory when it is clear and useful.

## Output

State the final commit message and whether the commit was created successfully.
If submodules are involved, state clearly whether the commit was created:
- inside the submodule
- in the parent repository
- or both
